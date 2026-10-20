"""Слой публичного адреса медиа.

Зачем он вообще нужен. Telegram принимает файл прямо в запросе, а Instagram
и VK устроены иначе: Instagram КАЧАЕТ файл со своей стороны по ссылке, которую
ты ему дал. Значит картинка обязана лежать в вебе и открываться без пароля.
Файл на твоём диске площадка не увидит физически, сколько ни повторяй запрос

Три пути, и два из них бесплатны:

  ready  ссылка уже публичная (твой сайт, твоё облако с прямой раздачей).
         Движок только проверяет, что адрес отвечает и отдаёт именно медиа
  git    публичный репозиторий на любом git-хостинге. Файл коммитится и уезжает,
         адрес raw-раздачи собирается из MEDIA_PUBLIC_BASE. Денег не стоит,
         живёт годами, переживает перезагрузку компьютера.
         Папку внутри репозитория задаёт MEDIA_GIT_SUBDIR (по умолчанию media).
         Пустое значение = класть в корень: часть бесплатных раздач (gist и
         прочие «плоские» хранилища) каталоги внутри репозитория отвергает
  ssh    свой сервер или хостинг: файл кладётся по scp в каталог веб-сервера,
         адрес собирается из MEDIA_PUBLIC_BASE. Нужен сервер, зато всё своё

Общее правило слоя: адрес считается рабочим только после живой проверки.
Не отвечает - движок говорит об этом прямо, а не отправляет площадку в никуда
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import config


class MediaError(Exception):
    pass


def mode() -> str:
    return config.env("MEDIA_MODE", "ready").lower()


def public_base() -> str:
    return config.env("MEDIA_PUBLIC_BASE").rstrip("/")


def put(path_or_url: str) -> str:
    """Кладёт файл в веб и возвращает публичный адрес.

    Уже публичный адрес возвращается как есть: слой не мешает тем, у кого
    картинки и так лежат в вебе
    """
    if path_or_url.lower().startswith(("http://", "https://")):
        return path_or_url

    source = Path(path_or_url).expanduser()
    if not source.exists():
        raise MediaError("файла нет на диске: %s" % path_or_url)

    current = mode()
    if current == "git":
        return _put_git(source)
    if current == "ssh":
        return _put_ssh(source)
    raise MediaError(
        "MEDIA_MODE=ready означает «ссылки уже публичные», а пришёл локальный файл %s."
        " Выбери MEDIA_MODE=git или MEDIA_MODE=ssh, либо дай сразу публичную ссылку" % source.name
    )


def verify(url: str, http=None) -> tuple[bool, int, str]:
    from . import net as net_module

    http = http or net_module.build()
    return http.head_ok(url)


# ── путь git ─────────────────────────────────────────────────────────────
def _put_git(source: Path) -> str:
    repo = config.env("MEDIA_GIT_DIR")
    if not repo:
        raise MediaError("для MEDIA_MODE=git нужен MEDIA_GIT_DIR: локальная папка публичного репозитория")
    base = public_base()
    if not base:
        raise MediaError("для MEDIA_MODE=git нужен MEDIA_PUBLIC_BASE: адрес raw-раздачи репозитория")
    if not shutil.which("git"):
        raise MediaError("git не установлен, а путь git без него не работает")

    repo_dir = Path(repo).expanduser()
    # пустой MEDIA_GIT_SUBDIR = корень репозитория. Нужен «плоским» раздачам,
    # которые каталоги внутри репозитория не принимают вовсе
    subdir = config.env("MEDIA_GIT_SUBDIR", "media").strip("/")
    if subdir:
        target_dir = repo_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        rel = "%s/%s" % (subdir, source.name)
    else:
        target_dir = repo_dir
        rel = source.name
    target = target_dir / source.name
    shutil.copy2(source, target)

    branch = config.env("MEDIA_GIT_BRANCH", "main")
    _git(repo_dir, ["add", rel])
    status = _git(repo_dir, ["status", "--porcelain", rel]).strip()
    if status:
        _git(repo_dir, ["commit", "-m", "media: %s" % source.name])
    _git(repo_dir, ["push", "origin", branch])
    return "%s/%s" % (base, rel)


def _git(repo_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), *args], capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        raise MediaError("git %s: %s" % (" ".join(args), (result.stderr or result.stdout).strip()[:300]))
    return result.stdout


# ── путь ssh ─────────────────────────────────────────────────────────────
def _put_ssh(source: Path) -> str:
    target = config.env("MEDIA_SSH_TARGET")
    base = public_base()
    if not target:
        raise MediaError("для MEDIA_MODE=ssh нужен MEDIA_SSH_TARGET вида пользователь@сервер:/путь/в/вебе")
    if not base:
        raise MediaError("для MEDIA_MODE=ssh нужен MEDIA_PUBLIC_BASE: адрес, по которому этот каталог виден")
    if not shutil.which("scp"):
        raise MediaError("scp не установлен, а путь ssh без него не работает")
    destination = target.rstrip("/") + "/" + source.name
    result = subprocess.run(
        ["scp", "-q", str(source), destination], capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise MediaError("scp не смог положить файл: %s" % (result.stderr or result.stdout).strip()[:300])
    return "%s/%s" % (base, source.name)


def describe() -> str:
    current = mode()
    if current == "git":
        return "git: %s -> %s" % (config.env("MEDIA_GIT_DIR") or "не задан", public_base() or "не задан")
    if current == "ssh":
        return "ssh: %s -> %s" % (config.env("MEDIA_SSH_TARGET") or "не задан", public_base() or "не задан")
    return "ready: ссылки берутся готовыми, движок только проверяет их живость"
