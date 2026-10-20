---
name: website-config
version: "1.0"
last_reviewed: 2026-05-29
description: Конфиг скила website. Точка адаптации процесса создания сайта под конкретного автора - пути к .business/, хостинг, домен, ESP. Сам процесс (workflow) общий.
---

# website config

> Точка адаптации под автора. Скилл `website` одинаков у автора и у учеников. Различие - только этот файл и данные проекта.

## Subject
```yaml
subject:
  name: "<Твоё имя>"
  market: ru            # ru | en | both (EN основной с июня 2026)
  main_site: null       # домен основного сайта (правило «один сайт для всего контента»)
```

## Paths (source of truth для Фазы 0-1)
```yaml
paths:
  funnel: ".business/marketing/funnel.md"
  avatar: ".business/audience/avatar.md"
  segments: ".business/audience/segments.md"
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"
  products_dir: ".business/products/"
  project_tasks: "tasks/projects/"           # tasks/projects/<site>.md при старте сайта
```

## Tools per phase (общие, не трогать)
```yaml
tools:
  phase_04_visual: ["stitch (MCP+stitch-loop)", "frontend-design"]
  phase_05_tokens: "ui-ux-pro-max search.py"
  phase_06_build: ["21st.dev MCP", "frontend-design"]
  phase_07_motion: "motion"
  copy_humaniser: "Skill('humaniser') на публичной копи (Фаза 3) — mandatory"
```

## Deploy
```yaml
deploy:
  default: vercel
  ru_hosting_check: "check-host.net IP routing для РФ"
  rule_no_vps_mixing: true        # каждый прод на свой VPS
```

**Для ученика:** заменить `subject`, `main_site`, при необходимости `deploy`. Пути `.business/` — под свой проект. Workflow и правила фаз НЕ трогать.