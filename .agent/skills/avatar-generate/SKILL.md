---
name: avatar-generate
description: Generate talking-avatar video from text using HeyGen Avatar V API with the STUDENT's OWN trained avatar (BYOA, canon _shared/bring-your-own-account.md). Used by replicate-viral to produce speaker_video_src track. Triggered by `/avatar <text>` or programmatic call from replicate-viral skill. Reads the student's HeyGen key/avatar from accounts.json (helper account.py); if not connected, runs onboarding and stops - never ships the author's key. Debug-only placeholder under IVANOS_ALLOW_PLACEHOLDER=1.
allowed-tools: Bash, Read, Write
version: "1.0"
created: 2026-05-23
last_reviewed: 2026-05-23
review_deps_every: 5 months
---

# avatar-generate - text -> MP4 (student's OWN HeyGen Avatar V, BYOA)

⚠️ **HeyGen v2 sunsets 2026-10-31**. Migration to v3 required by Oct 2026. Alternative: Gemini Omni Flash via Google AI Studio (generative, no training needed) - see `~/.business/growth/format-library-vertical-2026.md` for decision matrix.

HeyGen Avatar V обёртка для visual talking-head дорожки автора. Sub-skill для `replicate-viral`.

🌍 **Multi-location:** `replicate-viral` вызывает этот скилл ПО РАЗУ НА СМЫСЛОВОЙ СЕГМЕНТ ролика (2-4 на 30с) — каждый вызов: свой текст сегмента (`$1`) + свой кадр-лук локации (avatar_id/look из Ф4.6) + своё нарезанное аудио сегмента (`$3`). Каждый рендер — самостоятельный непрерывный клип со своим аудио (инвариант: не накладывать общий звук на склейку — рассинхрон губ). Кеш по хешу текста сегмента работает как обычно. Цена по HeyGen-секундам та же, что один длинный рендер.

## Когда триггерить

- Явный вызов `/avatar <text>`
- Программный вызов из `replicate-viral` для speaker_video_src
- Запросы «сгенери аватар», «сделай видео с моим аватаром», «HeyGen render»

## Когда НЕ триггерить

- Если есть живая запись автора (face-cam) - использовать её
- Если нужен B-roll без говорящей головы (Higgsfield Soul ID или Kling 3.0 - другие инструменты)

## Зависимости

- `curl`, `ffmpeg`, `python3`, `bc`, `md5sum` или `md5`
- Env в `~/.business/processes/.env`:
  - `HEYGEN_API_KEY` (https://app.heygen.com/settings → API)
  - `HEYGEN_AVATAR_ID` (https://app.heygen.com/avatars → твой trained avatar)
  - `HEYGEN_VOICE_ID` (опционально - используется в text-mode если нет ElevenLabs MP3)

## Как вызвать

```bash
~/.claude/skills/avatar-generate/scripts/heygen-render.sh "<text>" [avatar_id] [voice_audio_url]
```

- `$1` text - что говорит аватар
- `$2` avatar_id - override env (опционально)
- `$3` voice_audio_url - публичный URL на MP3 от ElevenLabs (опционально); если задан, HeyGen lip-syncs к этому аудио вместо своего TTS

Stdout: единственная строка с абсолютным путём (`/tmp/avatar-{hash12}.mp4`).
Stderr: логи прогресса polling, warnings.

## Workflow

1. Hash текст → cache check `/tmp/avatar-{hash}.mp4`
2. POST `https://api.heygen.com/v2/video/generate` с avatar+voice payload
3. Получить `video_id` из ответа
4. Polling: GET `https://api.heygen.com/v1/video_status.get?video_id=...` каждые 10 секунд
5. Status `completed` → скачать `video_url` через curl
6. Verify MP4 >100KB
7. Print path

Max wait: 6 минут (стандартные HeyGen рендеры 1-3 мин для 30с видео).

## Fallback

Если нет ключей или API упал:
- ffmpeg генерит чёрное видео 1080x1920 с текстом «AVATAR PLACEHOLDER»
- Длительность ~ word_count / 2.5 сек (как в voice-generate)
- В stderr: `WARNING: Using avatar placeholder (reason)`
- Валидный MP4 → Remotion загрузит и сможет собрать композицию

## Cost (для понимания автору)

- HeyGen Creator: $24/мес = 15 мин/мес видео
- Team: $69/мес = 30 мин/мес
- API доступен только на Team+ или Enterprise
- Кеш по хешу - не рендерить одну и ту же реплику дважды

## Anti-patterns

- ❌ Не пытаться рендерить >5 минут одним job (HeyGen рекомендует чанковать)
- ❌ Не использовать `avatar_style="closeup"` для портрета 1080x1920 - будет crop
- ❌ Не парсить stderr как путь - путь только в stdout
- ❌ Не вызывать без audio_url если хочешь lip-sync к голосу автора (тогда HeyGen TTS, не PVC)