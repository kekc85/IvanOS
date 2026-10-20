---
name: voice-generate
description: Generate audio voiceover from text using ElevenLabs TTS API with the STUDENT's OWN cloned voice (BYOA, canon _shared/bring-your-own-account.md). Used by replicate-reel to produce speaker_audio_src track. Triggered by `/voice <text>` or programmatic call from replicate-reel skill. Reads the student's ElevenLabs key/voice from accounts.json (helper account.py); if not connected, runs onboarding and stops - never ships the author's key. Debug-only silent placeholder under IVANOS_ALLOW_PLACEHOLDER=1.
allowed-tools: Bash, Read, Write
version: "1.0"
created: 2026-05-23
last_reviewed: 2026-05-23
review_deps_every: 3 months
---

# voice-generate - text -> MP3 (student's OWN ElevenLabs PVC, BYOA)

ElevenLabs TTS обёртка для голосовой дорожки автора. Sub-skill для `replicate-reel`.

## Когда триггерить

- Явный вызов `/voice <text>`
- Программный вызов из `replicate-reel` при сборке Remotion композиции (speaker_audio_src)
- Любой запрос «озвучь голосом автора» / «сгенери TTS» / «сделай MP3 из этого текста»

## Когда НЕ триггерить

- Если уже есть готовый MP3 от автора (живая запись) - использовать его
- Если задача - выбрать voice ID или клонировать новый голос (это ручная работа в UI ElevenLabs)

## Зависимости

- `curl`, `ffmpeg`, `bc`, `md5sum` или `md5` (macOS)
- Env: `~/.business/processes/.env` с `ELEVENLABS_API_KEY` и `ELEVENLABS_VOICE_ID`
- Получить ключ: https://elevenlabs.io/app/settings/api-keys
- Voice ID: https://elevenlabs.io/app/voice-lab → клик на voice → копировать ID из URL или Share

## Как вызвать

```bash
~/.claude/skills/voice-generate/scripts/eleven-tts.sh "Текст для озвучки" [optional_voice_id]
```

Stdout: единственная строка с абсолютным путём к MP3 (`/tmp/voice-{hash12}.mp3`).
Stderr: логи, warnings.
Exit code: 0 success (включая fallback), не-ноль только при системной ошибке (нет ffmpeg/curl).

## Output

- Кешируется по md5 хешу текста → один и тот же текст не жжёт кредиты повторно
- Модель: `eleven_multilingual_v2` (лучшее качество для русского)
- Voice settings: `stability=0.5`, `similarity_boost=0.75` (baseline для cloned voices)

## Fallback

Если `ELEVENLABS_API_KEY` пуст или API вернул ошибку:
- Скрипт генерит молчаливый MP3 длительностью `max(word_count / 2.3, char_count / 12.0)` секунд (≈2.3 wps + 12 chars/sec - калибровано под RU; до этой редакции было 2.0/14 - плейсхолдер кончался раньше реального голоса)
- Используется `ffmpeg -f lavfi -i anullsrc` → валидный MP3 файл
- **stderr ОЧЕНЬ заметный**: `ERROR: ELEVENLABS_API_KEY не задан - возвращён MOLCHALIVYY placeholder. Финальный MP4 будет БЕЗ ГОЛОСА. Установи API key или передай --no-voice явно.`
- Stdout всё равно отдаёт путь - Remotion загрузит файл, просто не услышит голос

Это позволяет `replicate-reel` собрать MP4 даже без credentials (для smoke-test пайплайна).

## Cost (для понимания автору)

- ElevenLabs Creator: $22/мес = 100K знаков. Один Reel ~300 знаков = ~333 ролика/мес
- Pro: $99/мес = 500K знаков
- Per-character billing, кеш по хешу экономит ре-генерации

## Anti-patterns

- ❌ Не передавать кириллицу через bash без правильного quoting (использовать двойные кавычки)
- ❌ Не вызывать без cache check (idempotent script делает это сам)
- ❌ Не парсить stderr как path - путь только в stdout
- ❌ Не использовать `eleven_monolingual_v1` - он не поддерживает русский