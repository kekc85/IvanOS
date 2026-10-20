"""Async-обёртка над Apify HTTP API (без зависимости от apify-client).

Apify-client 1.8.1 + apify-shared 2.x падают на ImportError в средах
с разными версиями pydantic — идём напрямую через REST. API простой:
POST run + polling + GET items.

API docs: https://docs.apify.com/api/v2
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

APIFY_API_BASE = "https://api.apify.com/v2"

# Не ждём вечно — рилзы и карусели обычно укладываются в 1-3 минуты.
DEFAULT_RUN_TIMEOUT_SEC = 5 * 60
RUN_POLL_INTERVAL_SEC = 3.0


class ApifyError(RuntimeError):
    """Любая ошибка Apify (failed run, timeout, HTTP fail)."""


@dataclass
class ApifyRunResult:
    items: list[dict[str, Any]]
    cost_usd: float
    run_id: str
    status: str  # SUCCEEDED | FAILED | TIMED-OUT


async def run_actor_and_wait(
    token: str,
    actor_id: str,
    run_input: dict[str, Any],
    *,
    timeout_sec: float = DEFAULT_RUN_TIMEOUT_SEC,
    poll_interval: float = RUN_POLL_INTERVAL_SEC,
) -> ApifyRunResult:
    """Запустить actor, дождаться завершения, вернуть dataset items + cost.

    actor_id формат: `username~actor-name` (с `~` вместо `/`) — этого требует REST.
    Принимаем `username/actor-name` и сами заменяем.
    """
    actor_id_url = actor_id.replace("/", "~")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        headers={"Content-Type": "application/json"},
    ) as c:
        r = await c.post(
            f"{APIFY_API_BASE}/acts/{actor_id_url}/runs",
            params={"token": token},
            json=run_input,
        )
        if r.status_code >= 400:
            raise ApifyError(
                f"actor run start failed: {r.status_code} {r.text[:200]}"
            )
        run = r.json().get("data", {})
        run_id = run.get("id")
        if not run_id:
            raise ApifyError(f"no run id in response: {r.text[:200]}")

        deadline = asyncio.get_event_loop().time() + timeout_sec
        status = run.get("status") or ""
        while status in ("READY", "RUNNING"):
            if asyncio.get_event_loop().time() > deadline:
                await _abort_run(c, token, run_id)
                raise ApifyError(
                    f"run {run_id} timed out after {timeout_sec}s (still {status})"
                )
            await asyncio.sleep(poll_interval)
            rr = await c.get(
                f"{APIFY_API_BASE}/actor-runs/{run_id}",
                params={"token": token},
            )
            if rr.status_code >= 400:
                raise ApifyError(
                    f"run status failed: {rr.status_code} {rr.text[:200]}"
                )
            run = rr.json().get("data", {})
            status = run.get("status") or ""

        if status != "SUCCEEDED":
            raise ApifyError(
                f"run {run_id} finished with status={status}: "
                f"{run.get('statusMessage') or '(no message)'}"
            )

        dataset_id = run.get("defaultDatasetId")
        items: list[dict[str, Any]] = []
        if dataset_id:
            ri = await c.get(
                f"{APIFY_API_BASE}/datasets/{dataset_id}/items",
                params={"token": token, "clean": "true", "format": "json"},
            )
            if ri.status_code >= 400:
                raise ApifyError(
                    f"dataset items failed: {ri.status_code} {ri.text[:200]}"
                )
            data = ri.json()
            items = data if isinstance(data, list) else []

        cost_usd = float(run.get("usageTotalUsd") or 0.0)

        return ApifyRunResult(
            items=items,
            cost_usd=cost_usd,
            run_id=run_id,
            status=status,
        )


async def _abort_run(client: httpx.AsyncClient, token: str, run_id: str) -> None:
    try:
        await client.post(
            f"{APIFY_API_BASE}/actor-runs/{run_id}/abort",
            params={"token": token},
            timeout=15.0,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("abort run %s failed: %r", run_id, e)
