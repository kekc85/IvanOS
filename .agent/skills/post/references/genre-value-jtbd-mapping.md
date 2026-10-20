# Genre × Value-vector × JTBD Mapping v1.0

> **Назначение:** matrix-table для Pass 0.5 в `workflow/03-write.md`. Жанр выбирается не ради формы, а как часть tuple `(genre, value_vector, JTBD)`. Без mapping пост получается формальным - Pass 0.5 v1 (only genre) ловит структуру, но не доставку value целевому читателю.
>
> **Источники:**
> - 5 автор-жанров - `references/_voice-TEMPLATE.md` v2.0 §4.2
> - 7 JTBD читателя - `.business/audience/avatar.md` + Карта смыслов 2.1 (root causes 1-3) + 8 канонических формулировок из 5.2-Карта-смыслов.md
> - Verbatim примеры - `examples/_TEMPLATE.md` (10 постов по типам)
> - Banned pivot - `memory/feedback_no_sales_pivot_in_value_post.md`
> - JTBD payer-language - `memory/feedback_jtbd_language_of_payer.md`

---

## Оси матрицы

### Axis 1: 5 автор-жанров (rows)

| ID | Genre | Корневой template (gold-standard) |
|---|---|---|
| G1 | **narrative-кейс** | Пост 8 (<имя ученика> / $100K case) |
| G2 | **vulnerability+reveal** | Пост 9 (День Победы) / пост о факап <сумма>|
| G3 | **alarm+reaction** | Пост 1 (🆘 Telegram блок) |
| G4 | **lifestyle+brag** | Пост 6 (25k подписчиков + море) |
| G5 | **build-in-public+paradox** | Пост 4 («Меня уволили со СВОЕГО») |

### Axis 2: 6 value-types (columns)

| ID | Value vector | Что доставляет читателю |
|---|---|---|
| V1 | **Insight** | Новая нейронная связь, «увидел рынок по-другому» |
| V2 | **Actionable** | Конкретный шаг, который можно сделать сегодня вечером |
| V3 | **Counter-intuitive** | Опровержение mainstream совета («не копи 10К, продавай со 100») |
| V4 | **Case study** | Чужой/свой пример с цифрами и механикой |
| V5 | **Strategic** | Что произойдёт на рынке за 6-12 месяцев - названными событиями, датами и цифрами, не «картиной» |
| V6 | **Original (proprietary frame)** | Авторский фреймворк / категория автора (вайбкодинг, контент-завод) |

### Axis 3: 7 JTBD читателя (3rd dimension)

Дословно из аватара + Карты смыслов 2.1 (8 канонических формулировок Belief Map 5.1):

| ID | JTBD payer-language (тест «готов платить <твоя цена>₽?») | Source |
|---|---|---|
| J1 | **«Получать первые автооплаты с цифрового продукта»** | avatar.md «главная цель» / Карта 2.3 «5 уведомлений за выходные» |
| J2 | **«Заработать первые 100-500К ₽ без аудитории 10К»** | Карта 5.2 канон #5 «JTBD-2 малая база 100-3000» |
| J3 | **«Пробить потолок 100-300К/мес на консультациях через цифровой продукт»** | Карта 5.2 канон #4 «JTBD-3 эксперт» |
| J4 | **«Защититься от блокировок аккаунта (cross-platform, диверсификация)»** | Карта 2.9 «массовые блокировки 2026» + Карта 2.1 root cause 2 |
| J5 | **«Перестать каждый месяц искать продажи заново (MRR / recurring)»** | Карта 5.2 канон #7 «JTBD-6 14.5% базы» |
| J6 | **«Перестать делать рилсы руками - снять зависимость от съёмок/монтажа»** | Карта 5.2 канон #6 «JTBD-4 интроверт без камеры» |
| J7 | **«Понять что вообще происходит на рынке ИИ - не отстать»** | Карта 2.1 «корневая 2026» + пост 7 «5 сдвигов» |

---

## Матрица 5×6 (по cell - best-fit / mandatory beat / verbatim / anti-pattern)

Каждая cell кодируется:
- **FIT** - natural / forced / invalid
- **JTBD primary** - какой JTBD из 7 чаще всего адресуется этой комбинацией
- **Mandatory beat** - что должно быть в посте, чтобы доставить value
- **Verbatim example** - пост из gold-standard, где такая комбинация уже сработала
- **Anti-pattern** - какой value-vector НЕ подходит для этого жанра

### G1 narrative-кейс × V1-V6

| | V1 Insight | V2 Actionable | V3 Counter-intuitive | V4 Case study | V5 Strategic | V6 Original |
|---|---|---|---|---|---|---|
| **FIT** | natural | forced | natural | NATURAL (best-fit) | invalid | natural |
| **JTBD** | J3 / J1 | J1 / J2 | J2 / J3 | **J1 / J3 / J5** | - | J3 / J6 |
| **Beat** | named hero + момент-инсайта + reveal | named hero + 1 повторяемый шаг | mainstream-совет vs реальный путь героя | имя+возраст+ниша → 3 шага → цифра → cliffhanger | - | имя + авторский термин («цифровой двойник бабушки») + цифра |
| **Verbatim** | Пост 8 ($100K case + бинарная фаза) | - | Пост 8 «не нужно быть программистом» | **Пост 8 (3 372 chars, 65🔥)** | - | Пост 8 «нейро-бабушки», «денежный треугольник» |
| **Anti** | - | Tutorial drift (Шаг 1/Шаг 2/Шаг 3 = AI-template) | - | - | strategic = вырождается в analyst-отчёт без живого героя | - |

### G2 vulnerability+reveal × V1-V6

| | V1 Insight | V2 Actionable | V3 Counter-intuitive | V4 Case study | V5 Strategic | V6 Original |
|---|---|---|---|---|---|---|
| **FIT** | NATURAL (best-fit) | invalid | natural | natural (если кейс = свой факап) | invalid | natural |
| **JTBD** | **J3 / J1 / J7** | - | J2 / J3 | J1 / J3 | - | J6 / J3 |
| **Beat** | «Раньше я думал X. Оказалось Y» + нерешённое | - | «Все говорят X. Я просрал на этом <сумма>» | свой факап + цифра + урок (без resolve) | - | свой кейс + авторский термин ослабляет ценность урока |
| **Verbatim** | Пост 9 (День Победы → soft-pivot) / пост о <сумма>-факап | - | «Я просрал <сумма> на платный трафик.2) | «<сумма>-факап» | - | - |
| **Anti** | - | actionable убивает vulnerability (если есть «сделай 3 шага» - это не vulnerability) | - | - | strategic = эссеист с прогнозом, теряется «Я просрал» | - |

### G3 alarm+reaction × V1-V6

| | V1 Insight | V2 Actionable | V3 Counter-intuitive | V4 Case study | V5 Strategic | V6 Original |
|---|---|---|---|---|---|---|
| **FIT** | natural | NATURAL (best-fit) | natural | forced | natural | forced |
| **JTBD** | J4 / J7 | **J4 / J1** | J4 | - | J4 / J7 | - |
| **Beat** | «Telegram блок» → «вот что я понял» | crisis + 3-step plan + автор-действие («я УДВАИВАЮ») | «99% замедляют, я УДВАИВАЮ» | - | «вот что будет в течение месяца» + рекомендация | - |
| **Verbatim** | Пост 1 (🆘, 2 570 просмотров, топ-1) | **Пост 1 (3-step plan + reversal)** | Пост 1 «99% замедляют, я УДВАИВАЮ» | - | Пост 1 (соединено с план-реакцией) | - |
| **Anti** | - | - | - | crisis + кейс ученика = не работает (кризис требует ЛИЧНОГО автора-действия, не чужого) | - | original фреймворк в crisis выглядит cynical (использует панику для product placement) |

### G4 lifestyle+brag × V1-V6

| | V1 Insight | V2 Actionable | V3 Counter-intuitive | V4 Case study | V5 Strategic | V6 Original |
|---|---|---|---|---|---|---|
| **FIT** | forced | invalid | natural | natural (свой кейс = brag) | invalid | natural |
| **JTBD** | J1 | - | J6 / J2 | **J1 / J6 / J5** | - | J6 |
| **Beat** | момент-сцена + одна цифра + soft-insight | - | «отдыхал, гулял, стрелял, кайфовал» vs метрика - paradox | один момент сцены + одна цифра ($100K в мес / 25 тыс подписчиков) | - | «контент-ферма приросла на 25 тыс» - авторский термин в контексте отдыха |
| **Verbatim** | - | - | **Пост 6 («Поездка к морю ИЛИ 25.000 подписчиков»)** | **Пост 6 (1 250 chars, простой формат)** | - | Пост 6 «контент-ферма», «20+ аккаунтов по РФ» |
| **Anti** | insight в lifestyle = педантично, теряется brag | - | - | - | strategic = лекция в отпуске, читатель не верит | - |

### G5 build-in-public+paradox × V1-V6

| | V1 Insight | V2 Actionable | V3 Counter-intuitive | V4 Case study | V5 Strategic | V6 Original |
|---|---|---|---|---|---|---|
| **FIT** | natural | natural | NATURAL (best-fit) | natural (свой проект как кейс) | natural | NATURAL |
| **JTBD** | J7 / J1 | J1 / J6 | **J6 / J7** | J1 | J4 / J7 | **J6 / J1** |
| **Beat** | «Допилил X - оказалось Y» с неожиданным reveal | «Допилил Х - забирай» (tool-drop variant) | «Меня уволили со СВОЕГО контент-завода» (paradox) | свой проект + цифры + cliffhanger | «вот что я строю → почему рынок туда идёт» | свой проект + авторский фреймворк как доказательство категории |
| **Verbatim** | Пост 4 («Меня уволили…» 1 591 chars, 8🔥) | Пост 3 («Уникализатор + выход из бана» 1 448 chars) | **Пост 4 (paradox-hook + 3-актная хронология)** | Пост 4 (свой контент-завод как кейс) | Пост 4 (Claude → СиДэнс/Клинг/ВЕО) | **Пост 4 «контент-завод», «вайбкодинг от А до Я»** |
| **Anti** | - | - | - | - | - | - |

---

## Сводка: 5 best-fit (1 на жанр)

| Жанр | Best-fit tuple | Verbatim |
|---|---|---|
| G1 narrative-кейс | **G1 × V4 (case study) × J1/J3/J5** | Пост 8 ($100K в мес, 3 372 chars, 65🔥) |
| G2 vulnerability+reveal | **G2 × V1 (insight) × J3/J1/J7** | Пост 9 / «<сумма>-факап» |
| G3 alarm+reaction | **G3 × V2 (actionable) × J4/J1** | Пост 1 (🆘 Telegram, 3-step plan, топ-1 по охвату) |
| G4 lifestyle+brag | **G4 × V4 (case study) × J1/J6/J5** | Пост 6 (25 тыс подписчиков + отдых) |
| G5 build-in-public+paradox | **G5 × V3 (counter-intuitive) × J6/J7** | Пост 4 («Меня уволили со СВОЕГО») |

## Сводка: 5 invalid combinations (что НЕ работает)

| Tuple | Почему не работает |
|---|---|
| **G1 × V2 (actionable)** | Narrative-кейс с actionable-выводом скатывается в Tutorial («Шаг 1/Шаг 2/Шаг 3») - это AI-default жанр, hard-abort в Pass 0.5 |
| **G2 × V2 (actionable)** | Vulnerability + actionable («Я просрал <сумму>. Сделай 3 шага чтобы не повторить») убивает vulnerability - превращает в нравоучение |
| **G2 × V5 (strategic)** | Vulnerability + strategic = эссеист с прогнозом. Теряется «Я просрал». Vulnerability требует личного beat, не анализа рынка |
| **G3 × V4 (case study)** | Crisis + кейс ученика не работает - кризис требует ЛИЧНОГО автора-действия («я УДВАИВАЮ»), не чужого примера |
| **G4 × V2/V5** | Lifestyle + actionable / strategic = лекция в отпуске. Читатель не верит - если ты на море, не учи меня сейчас |

## Сводка: JTBD coverage gaps в автор-corpus

| JTBD | Покрытие в 10 gold-standard | Gap analysis |
|---|---|---|
| J1 первые автооплаты | 5/10 (пост 4, 6, 8, 2, 5) | **OK** |
| J2 100-500К без аудитории 10К | 1/10 (пост 8 косвенно) | **GAP** - нет прямого поста под этот JTBD |
| J3 потолок 100-300К/мес → цифровой продукт | 2/10 (пост 8, пост 5) | **partial** |
| J4 защита от блокировок | 2/10 (пост 1, пост 3) | OK |
| J5 MRR / recurring | 0/10 | **GAP CRITICAL** - JTBD-6 14.5% базы не имеет post в gold-standard |
| J6 снять зависимость от съёмок/монтажа | 3/10 (пост 2, 3, 4) | OK |
| J7 что происходит на рынке | 2/10 (пост 7, пост 1) | **partial** |

**Strategic implication:** при `mode=plan` из Карты смыслов 2.1 - приоритизировать темы под J5 (MRR/recurring) и J2 (малая база). Эти JTBD payer-language, но не имеют sufficient template-coverage в gold-standard.

---

## Cross-check rules для Pass 0.5

### Rule 1: tuple должен быть в матрице
Выбранная `(genre, value_vector, JTBD)` сверяется с матрицей:
- Если FIT = **natural** или **NATURAL (best-fit)** → PROCEED
- Если FIT = **forced** → WARNING + suggest closest natural tuple
- Если FIT = **invalid** → HARD ABORT + return к Pass 0.5 для re-selection

### Rule 2: JTBD payer-language
Выбранный JTBD должен пройти тест «готов клиент платить <твоя цена> ₽?» (см. `feedback_jtbd_language_of_payer.md`).

Banned «JTBD»:
- «упаковать экспертизу» / «закрепить identity» / «запустить движок» - НЕ JTBD
- любой JTBD на языке методологии (артефакты, контуры, фасилитация)

### Rule 3: invalid сразу
- G1 × V2 → tutorial drift, HARD ABORT
- G2 × V2 → vulnerability убита, HARD ABORT
- G2 × V5 → essay-mode, HARD ABORT
- G3 × V4 → crisis требует автора, HARD ABORT
- G4 × V2/V5 → lecture-in-vacation, HARD ABORT

---

## История версий
- **v1.0 (2026-05-28):** первая версия. 5×6 матрица. 7 JTBD. 5 best-fit + 5 invalid + 7 JTBD coverage gaps. Source: corpus 65 (автора) + Карта смыслов 5.2 v4 + avatar.md.
