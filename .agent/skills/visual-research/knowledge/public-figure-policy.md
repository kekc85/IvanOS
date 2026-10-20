# Public Figure Policy

Gate-логика для определения «можно ли искать фото этой персоны».

## Allow list (yes — searchable)

### Tech / business public figures
- CEO / фаундеры (Dario Amodei, Sam Altman, Elon Musk, Mark Zuckerberg etc)
- C-level executives с publicly-listed role
- Известные инвесторы (Marc Andreessen, Naval Ravikant)
- Public-facing entrepreneurs (Riley Brown, Pieter Levels)

### Content creators / influencers
- YouTubers / TikTokers / Reels-авторы с >10k subscribers
- Bloggers с personal brand (LinkedIn / Twitter authors)
- Podcasters (Lex Fridman, Tim Ferriss)

### Authors / scientists / journalists
- Published authors (книги, papers)
- Researchers с public affiliation
- Journalists с public bylines (TechCrunch, Verge, NYT etc)

### Public events participants
- Conference speakers (TED, TechCrunch Disrupt, Web Summit)
- Public panelists
- Press conference participants

### Political / civic public figures
- Elected officials
- Government appointees
- Public spokespersons

## Soft cases (proceed with caution)

### Mid-tier creators (<10k followers)
- Допустимо если они сами активно публикуют self-portraits
- Если контент-цель — нейтральный референс (не критика)
- Не доставать private/personal photos

### Family members of public figures
- Только если они сами public-facing (не "wife of CEO")
- Никогда дети, даже если родители public

### Former public figures (retired, scandal-affected)
- Допустимо для исторического контекста
- Не использовать в attacking-tone контенте

## Deny list (NO — refuse to search)

### Children
- Несовершеннолетние, даже children of public figures
- Включая students, child actors, kid creators

### Private individuals
- Люди не имеющие public-facing role
- "Сосед", "коллега", "random user"
- Profile в соцсетях ≠ public figure

### Sensitive contexts
- Жертвы преступлений
- Медицинские пациенты (даже если знаменитые)
- Случайные люди в новостях (witnesses, bystanders)
- Anonymous sources

### Imagery types
- Non-consensual photos (paparazzi-стиль leaks)
- Hacked / stolen private photos
- Deepfakes presented as real
- Mugshots вне prosecutorial context

### Restricted use cases
- Harassment / doxxing material
- Stalking aid
- Identity fraud / impersonation prep
- Targeting individuals for attacks

## Decision algorithm

```
1. Public role explicitly listed (CEO / author / journalist / speaker)?
   YES → Allow → proceed to source hierarchy
   NO  → continue
2. Self-publishes content publicly (>10k followers, active on platforms)?
   YES → Allow (soft) → use only public-facing photos
   NO  → continue
3. Mentioned in news/wiki/public records as public-facing?
   YES → Allow (with context check)
   NO  → STOP. Refuse.
4. Soft case (mid-tier / family / former)?
   → Caution. Limit to public posts. No personal photos.
5. Deny-list match (child / sensitive / victim / restricted)?
   → STOP. Refuse with brief reason.
```

## Refusal language

Если запрос не проходит:

> Не могу найти фото — этот человек не подпадает под политику публичных фигур (см. public-figure-policy.md). Если речь идёт о публичной персоне с известной ролью — уточни контекст (компания / роль / public bylines).

Не выдавать длинные moral lectures. Краткий refusal + offer to clarify scope.

## Edge cases в контексте автора

- **Ученики курса** — приватные, NO. Только если ученик сам опубликовал case study с self-portrait и дал апрув.
- **Конкуренты-эксперты** (<конкурент>, автор Замесин etc) — public, OK. Использовать для разборов и upper-funnel.
- **Random TG-channel авторы** — soft case. Если канал >5k subs и автор face-cam regularly — OK.
- **Семья автора** — приватная, NO (даже если знаменитый муж/жена). Никогда детей.