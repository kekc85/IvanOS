# Звукодизайн motion-графики для коротких вертикальных видео — прескриптивная база знаний

> Назначение: лечь в `knowledge/` скилла, который автоматически кладёт СЛОЁНЫЙ, динамичный звук под анимацию. Закрывает критику автора («примитивные одиночные бипы»). Всё ниже опирается на разборы sound-дизайнеров; источники с URL в конце. Тайминги в миллисекундах и кадрах (24/30 fps: 1 кадр ≈ 33-42 мс).

---

## 0. Ядро философии (одна фраза на всё)

**Один «звук события» = НЕ один файл, а 3-5 слоёв в трёх частотных полосах (низ/серед/верх), выровненных по пику.** Профессиональный звук собирается так же, как звук удара = «smack + beefy impact + rustle of clothing», звук закрытия двери = «heavy thud + metallic latch click + swoosh of sleeve» — каждый слой несёт свою функцию (источник: Pro Sound Effects, SFX Engine). Правило-потолок: **больше 3-5 файлов на одно событие — стоп, мьютим по очереди, лишний слой выкидываем** (Pro Sound Effects). Низ нельзя штабелировать: «три разных баса не сделают звук больше» — получится муть.

Три функции внутри слоя (модель удара из Pro Sound Effects):
- **transient / attack** — «ожидание», точка синхрона с визуалом (smack, click, crack);
- **body / weight** — масса и сила (beefy impact, boom, thump);
- **texture / tail** — связь со средой, реализм (rustle, air, debris, reverb).

---

## 1. Принцип слоистости: 12 РЕЦЕПТОВ compound-событий

Формат каждого рецепта: слои → **тайминг слоя относительно визуального хита** (0 мс = кадр, где элемент «приземлился») → **относительная громкость** (transient = опорный 0 dB, остальное в минус) → частотная полоса.

База таймингов (универсально по всем источникам):
- **Звук ведёт визуал: transient стартует на 10-20 мс РАНЬШЕ кадра-хита** — мозг обрабатывает аудио быстрее картинки (Pixflow, Pro Sound Effects). Для движений (whoosh) лид-ин ещё больше — весь sweep ДО приземления.
- Доводка по 1 кадру до идеального синка (Pixflow).
- Длительность whoosh = длительности перехода: ~400-500 мс на полусекундный рез (Pixflow). UI-звуки 80-300 мс (SoundCy/Envato). Ризер 4-16 баров / в коротком видео 0.3-2 с (Unison, Epidemic).

Частотная гигиена (по всем источникам): hi-pass всё ниже 80-100 Hz; mid-boost 1-3 kHz чтобы «прорезать»; air-shelf 10 kHz+ для «дорогого» верха; вырезать notch 1.5-3 kHz под голосом (Pixflow, SFX Engine).

### 1.1 Whoosh / Transition (переход, свайп между сценами)
| Слой | Offset от хита | Gain | Полоса |
|---|---|---|---|
| air-whoosh (sweep, основа движения) | −400…−20 мс (весь подлёт) | −3 dB | high/broadband |
| low sub-boom / rumble (вес) | −150…0 мс | −6 dB | 40-120 Hz |
| transient crack / impact «приземление» | 0 мс (точно на хит) | 0 dB | 2-5 kHz |
| reverb tail | 0…+300 мс (хвост после) | −12 dB | wide, затухает |

База + комплементарные слои (sub-rumble на вес, hi-air на текстуру, reverse-cymbal на драму) + **короткий impact в конце как «точка приземления»** — «даже маленький транзиент делает рез locked and confident» (Pixflow, SFX Engine). Doppler: автоматизация pitch/pan/volume по дуге (Pixflow, dl-sounds).

### 1.2 Pop (появление мелкого элемента, иконка, бейдж)
| Слой | Offset | Gain | Полоса |
|---|---|---|---|
| soft pop (округлый аттак) | 0 мс | 0 dB | mid |
| UI-click (чёткость) | 0 мс | −6 dB | high-mid |
| sparkle / shimmer (опционально, «магия») | +20…+80 мс | −10 dB | 8-14 kHz |

«Layering timbres — crisp click + subtle swoosh — добавляет сложность без перегруза» (SoundCy). Длительность 80-150 мс, мгновенный аттак-быстрый спад = «precise» (SoundCy).

### 1.3 Counter / Ticker (счётчик, бегущие цифры)
| Слой | Offset | Gain | Полоса |
|---|---|---|---|
| rhythmic ticks с нарастающим pitch | по кадрам цифр | −6 dB | mid |
| (опц.) coin-clink на каждый «круглый» шаг | на круглых числах | −8 dB | high-mid |
| final impact / ding | на финальной цифре | 0 dB | broadband + low |

Тики поднимаются по высоте к финалу (нарастание напряжения = pitch-rise, релиз = pitch-drop — общий принцип Pixflow). Финал обязателен — «landing point», иначе счётчик «не закрывается».

### 1.4 Reveal / Climax (кульминация, заголовок, главный кадр)
Каноническая 4-фазная структура trailer-hit (Epidemic, Soundstripe, UVI Meteor: 3 слоя rise + 4 слоя impact):
| Фаза | Слои | Тайминг | Gain |
|---|---|---|---|
| **riser** (8-16 кадров / 0.3-1 с) | noise-sweep + pitch-rise + reverse-cymbal | −длина…0 | от −20 dB к 0 |
| **impact** | boom (body) + crack (transient) | 0 мс | 0 dB |
| **sub-drop** | суб-волна вниз | 0…+200 мс | −4 dB |
| **tail** | reverb / атмосфера | +200…+1500 мс | −12 dB, затух |
Пик ризера = ТОЧНО кадр reveal; перед хитом — резкий vol-cut −3…−6 dB для контраста «дыхание перед ударом» (Unison). Low = вес, mid = тело, high = sparkle/excitement (Soundstripe, Epidemic).

### 1.5 Riser / Build (только подводка, без удара — нагнетание)
noise-sweep (фильтр 150 Hz → 10 kHz, резонанс 15-20%) + pitch-automation (−12 → 0 полутонов) + volume −20 → 0 dB, **пики слоёв смещены (staggered)**, не одновременно (Unison). В коротком видео сжать до 0.3-2 с.

### 1.6 Sub-drop (бас уходит вниз — «приземление веса»)
Один суб-осциллятор с pitch-down автоматизацией, 40-120 Hz, старт 0 мс на хите, −4 dB, хвост 200-400 мс. Только на КРУПНЫХ событиях (мелкий pop суб не получает — см. §3).

### 1.7 Glitch (цифровой сбой, дёрганый переход)
| Слой | Роль |
|---|---|
| digital noise burst (белый шум вместо хита) | «dropout» эффект (Sample Focus) |
| bit-crush на основном звуке | «сонная деградация железа» (Sample Focus, NI) |
| stutter / micro-repeat (ultra-короткий буфер, pitch/filter на сегменте) | «broken machine» (Sample Focus, MusicRadar) |
| (опц.) granular поверх + bit-crush | lo-fi текстура (Sample Focus) |
Слои носят на низкой громкости поверх оригинала «для текстуры без потери грува» (Sample Focus). Длительность 40-150 мс, рваный тайминг намеренно.

### 1.8 Click / UI (нажатие, тап, toggle)
single crisp click (mid-high), 30-80 мс, мгновенный аттак. Опц. + micro-swoosh для «жидкости». «Tap/click должны ощущаться мгновенно» (SoundCy). Это атом — почти не слоится, но варьируется (см. §2).

### 1.9 Ding / Notification (уведомление, успех, галочка)
ping (sharp attack + quick decay, 1-2 тона) + опц. shimmer-tail. 150-300 мс. «Notification can be slightly longer» чем click (SoundCy). Для «success» — восходящая пара тонов; для «error» — нисходящая.

### 1.10 Swipe / Wipe (горизонтальный сдвиг, листание)
короткий air-whoosh (быстрее и тише чем сценический, §1.1) + лёгкий transient на стопе. 150-300 мс, pan по направлению свайпа.

### 1.11 Typewriter / Text-in (печать текста, по-символьно)
серия коротких ключевых кликов (mechanical key), по символу/слову, −6 dB, рандом pitch/timing на каждый (иначе «строчит» механически — §2). На финале строки — лёгкий «caret»-ding.

### 1.12 Coin / Cash (деньги, цена, монетизация)
coin-clink (high-mid, металл) ×N + опц. «cash register» body на финале + sparkle-shimmer. Для тикера цены — комбинировать с §1.3.

> **Reverse / Sparkle / Stinger / Texture-atmos** — это слои-модификаторы, входят в рецепты выше: reverse-swell как pre-roll к reveal; sparkle/shimmer как hi-декор к pop/coin; stinger = короткий музыкальный аккорд-акцент на reveal; texture/atmos = подложка-«воздух» под всю сцену (низкая громкость, заполняет тишину).

---

## 2. Динамика и вариативность («human feel»)

**Почему нельзя один файл на повтор.** Идентичный сэмпл на каждый тик/клик звучит механически и вызывает усталость слуха. Решение прямо из UI-практики: **«создай 3-5 чуть разных версий основного звука, проигрывай их случайно — интерфейс начинает звучать живым и естественным»** (SoundCy). Профи-инструменты строят это в ядро: «every parameter — velocity, pitch, rotation — может быть рандомизирован», «вводи тонкие смещения внутри каждого слоя чтобы избежать механики» (Sound Particles 3). Библиотеки whoosh строятся вокруг «randomisation + speed and level variation» на сотнях ассетов (Krotos Weaponiser: 574 whoosh-ассета).

**Микро-джиттер (применять к КАЖДОМУ повторному срабатыванию):**
- **pitch**: ± несколько центов/полутон (SoundCy: «adjust the pitch a tiny bit»);
- **timing**: ± несколько мс смещения старта (не на сетке идеально — иначе строчит);
- **length**: «обрежь длину на пару миллисекунд» (SoundCy);
- **gain**: ± 1-3 dB;
- **sample**: иногда подменяй один слой альтернативой (SoundCy: «swap out one of the layers»).

**Сколько вариаций на категорию:** минимум **3-5 на повторяющийся звук** (click/tick/key) — это нижний порог «non-mechanical» (SoundCy, Sound Particles). Для «событийных» (whoosh/impact/reveal) — больше (5-10), чтобы серия переходов в одном видео не звучала копипастой. Ротация: round-robin (по кругу, без немедленного повтора того же сэмпла) + рандомный джиттер поверх.

---

## 3. Энергия под движение (sound matches motion)

**Звук масштабируется под силу/размер движения.** Прямой принцип: **«bigger means lower and slower, and vice versa»** — крупное событие = ниже и медленнее, мелкое = выше и короче (Krotos). «Scale your sound layers to the size and weight of what you are designing to.»

| Движение | Звук |
|---|---|
| мелкое появление (иконка, бейдж) | тонкий pop/click, БЕЗ суба, 80-150 мс |
| средний переход | air-whoosh + лёгкий transient, без big-boom |
| крупный reveal / влёт большого блока | riser → impact (boom+crack) → **sub-drop** → tail |
| резкий стоп / drop-кадр | «drop = мёртвая остановка, намеренная пауза» — тишина или один суб + reverb-tail (Pro Sound Effects) |

**Тихие моменты («breathe»).** Не озвучивать каждый кадр. «Самые виральные Reels — ритм slow-fast-slow / прогрессивный build, нарратив-арка даже за 30 с» (techfly, virlo). Перед reveal — vol-cut/пауза «дыхание перед ударом» (Unison). Тишина — инструмент контраста, не дыра.

**Музыкальная энергия-кривая к пику.** Ризер «начинается тихо и медленно, плавно набирает громкость и интенсивность до громкого эпичного финала» (Soundstripe). Раскладка энергии под нарратив: 2/4/8 «единиц» build перед drop (Unison). Пики слоёв смещать (staggered), не валить одновременно (Unison).

**Сайдчейн-дакинг (sfx/whoosh давят музыку, голос давит музыку/sfx).** Сжимать музыку под событийный звук и под голос, чтобы транзиент «прорезал». Параметры из практики video/audio: **gain-reduction −15 dB (лёгкий) … −20 dB (типично) … −35 dB (тяжёлый)**, ratio **3:1-5:1** (LANDR, Larry Jordan). Атака быстрая (поймать транзиент), релиз — чтобы музыка вернулась за длину события. Голос — главный приоритет дакинга в говорящем контенте.

---

## 4. Sound-on vs sound-off и типичные AI-tells

**Sound-on vs sound-off.** Лента листается без звука по умолчанию — «в silent-scroll motion = твой мегафон» (techfly). Поэтому: (1) звук — БОНУС поверх и без того читаемого визуала, не костыль; (2) при sound-on звук должен «reinforce message без отвлечения», поддерживать ритм (pops/swipes/chimes на быстрых резах) (finchley, levitatemedia). Голос/дилог — поверх всего, музыка и sfx «complement, not overpower» (DropForce).

**Ошибки / AI-tells (чего избегать в авто-раскладке):**
- **over-whooshing** — whoosh на каждый рез = слух глохнет, теряется акцент. «Too many effects distract or feel unnatural» (Editors Keys). Whoosh только на значимых переходах.
- **один-звук-на-всё** — главный механический tell; лечится §2 (3-5 вариаций + джиттер).
- **мисматч энергии** — big-boom под мелкий pop или тонкий клик под огромный reveal (нарушение §3 «bigger = lower/slower»).
- **generic corporate** — стоковый «успех-динь» без слоёв/характера; всегда минимум 2-3 слоя (§0).
- **клиппинг / штабель низа** — «три баса не сделают больше», только муть и перегруз (Pro Sound Effects); hi-pass ниже 80-100 Hz, держать хедрум.
- **перегруз (>3-5 слоёв)** — «стоп, мьют по очереди, выкинь лишнее» (Pro Sound Effects).
- **звук НЕ ведёт визуал** — транзиент должен стартовать на 10-20 мс РАНЬШЕ кадра (Pixflow); «на кадр позже» читается как рассинхрон.
- **нет landing-point** — переход/счётчик без финального transient «висит» (SFX Engine).

---

## 5. ТАКСОНОМИЯ библиотеки (целевое ~300-500 сэмплов)

17 категорий × вариации. Распределение взвешено по частоте использования в motion-графике (whoosh/impact/pop/click — рабочие лошади, больше вариаций; редкие — меньше). Вариации = pitch/length/sample под §2 round-robin.

| # | Категория | Вариаций | Зачем столько |
|---|---|---|---|
| 1 | whoosh / transition | 40 | главная лошадь, у каждого перехода своя (short/long/swipe/scene) |
| 2 | impact / boom | 35 | reveal/landing; small→large по весу |
| 3 | pop | 30 | появления элементов — частотный повтор → нужна ротация |
| 4 | click / UI | 30 | тапы/тогглы — самый механичный риск, max вариаций |
| 5 | riser / swell | 25 | подводка под reveal, разной длины |
| 6 | tick | 25 | счётчики/таймеры — повтор в серии |
| 7 | ding / notification | 25 | success/error/neutral + варианты |
| 8 | sub-drop | 20 | вес крупных событий |
| 9 | glitch | 20 | стилевые рваные переходы |
| 10 | sparkle / shimmer | 20 | hi-декор pop/coin/magic |
| 11 | coin / cash | 20 | монетизация/цены (тема автора) |
| 12 | typewriter | 18 | текст-ин по символам |
| 13 | swipe | 18 | листание/сдвиг |
| 14 | reverse / pre-roll | 15 | swell перед reveal |
| 15 | stinger | 15 | музыкальный акцент-аккорд |
| 16 | texture / atmos | 12 | подложки-«воздух» под сцену |
| 17 | transient crack / snap | 15 | чистые транзиенты для слоения в compound |
| | **Итого** | **~423** | в коридоре «несколько сотен» (300-500) |

Минимальный жизнеспособный набор (если урезать): по 3-5 на категорию = ~70 для старта, но повторяемость пострадает; целевое — таблица выше.

---

## 6. Compound-event схема для конфига

Данные описывают слоёное событие: `event → [{layer_sound, offset_ms, gain_db, pitch_semitones}]` + правила вариации. `offset_ms`: 0 = кадр визуального хита, отрицательное = звук раньше.

```json
{
  "version": 1,
  "global": {
    "lead_in_ms": -15,
    "humanize": { "pitch_semitones": 0.4, "timing_ms": 8, "gain_db": 2.0 },
    "rotation": "round_robin_no_immediate_repeat",
    "sidechain_duck": { "target": "music", "reduction_db": -18, "ratio": "4:1" }
  },
  "events": {
    "transition_whoosh": {
      "energy": "medium",
      "layers": [
        { "layer_sound": "whoosh/air_sweep",       "offset_ms": -400, "gain_db": -3,  "pitch": 0 },
        { "layer_sound": "sub/boom_rumble",         "offset_ms": -150, "gain_db": -6,  "pitch": 0 },
        { "layer_sound": "transient/crack",         "offset_ms": 0,    "gain_db": 0,   "pitch": 0 },
        { "layer_sound": "texture/reverb_tail",     "offset_ms": 0,    "gain_db": -12, "pitch": 0 }
      ],
      "variations": 6
    },

    "element_pop": {
      "energy": "small",
      "layers": [
        { "layer_sound": "pop/soft_pop",            "offset_ms": 0,   "gain_db": 0,   "pitch": 0 },
        { "layer_sound": "click/ui_click",          "offset_ms": 0,   "gain_db": -6,  "pitch": 0 },
        { "layer_sound": "sparkle/shimmer",         "offset_ms": 40,  "gain_db": -10, "pitch": 2 }
      ],
      "variations": 5,
      "rules": { "no_sub": true }
    },

    "counter_tick": {
      "energy": "small",
      "per_step": [
        { "layer_sound": "tick/rhythmic_tick",      "offset_ms": 0,   "gain_db": -6,  "pitch_ramp": "+0.5_per_step" }
      ],
      "final_step": [
        { "layer_sound": "ding/impact_ding",        "offset_ms": 0,   "gain_db": 0,   "pitch": 0 },
        { "layer_sound": "sub/boom_rumble",         "offset_ms": 0,   "gain_db": -6,  "pitch": 0 }
      ],
      "variations": 4
    },

    "climax_reveal": {
      "energy": "large",
      "layers": [
        { "layer_sound": "riser/noise_sweep",       "offset_ms": -700, "gain_db": -20, "gain_to_db": 0, "pitch_ramp": "-12_to_0" },
        { "layer_sound": "reverse/cymbal_swell",    "offset_ms": -500, "gain_db": -10, "pitch": 0 },
        { "layer_sound": "impact/boom_body",        "offset_ms": 0,    "gain_db": 0,   "pitch": 0 },
        { "layer_sound": "transient/crack",         "offset_ms": 0,    "gain_db": -2,  "pitch": 0 },
        { "layer_sound": "sub/sub_drop",            "offset_ms": 0,    "gain_db": -4,  "pitch": -5 },
        { "layer_sound": "texture/reverb_tail",     "offset_ms": 200,  "gain_db": -12, "pitch": 0 }
      ],
      "pre_hit_vol_cut_db": -4,
      "variations": 8
    }
  }
}
```

Правила движка (из §1-3): transient любого события садится на `offset_ms: 0` (кадр-хит) и опорный `gain_db: 0`; `lead_in_ms` сдвигает всю связку чуть раньше визуала; `humanize` применяется per-trigger; `no_sub`/`energy` блокируют big-boom под мелкие события; `sidechain_duck` давит музыку под событие и под голос.

---

## Источники

- Pro Sound Effects — Layering Sound Effects (модель слоёв удара, 3-5 потолок, штабель низа): https://blog.prosoundeffects.com/sound-layering
- Pro Sound Effects — Sound Effects Terms (riser/swell/drop определения): https://blog.prosoundeffects.com/sound-effects-terms-explained-part-1
- SFX Engine — How to layer sound effects in video (door-close слои, landing-point): https://sfxengine.com/blog/how-to-layer-sound-effects-in-video
- Pixflow — Cinematic Whoosh Sound Effects (лид-ин 10-20 мс, EQ, длительность, impact-end): https://pixflow.net/blog/cinematic-whoosh-sound-effects/
- Pixflow — Explosion Sound Effects Complete Guide (4-слойная structure impact, notch под голос): https://pixflow.net/blog/explosion-sound-effects-a-complete-guide/
- Krotos — How to Design Whoosh (weight-scaling «bigger = lower/slower», 574 ассета, randomisation): https://www.krotosaudio.com/how-to-design-whoosh-sound-effects/
- SoundCy — How to make UI sounds (3-5 вариаций, 80-300 мс, pitch/length джиттер, timbre-layering): https://soundcy.com/article/how-to-make-ui-sounds
- Sound Particles 3 — Advanced Randomization (рандом каждого параметра, micro-offset): https://blog.soundparticles.com/advanced-randomization-tools
- Unison — How to Create Risers (4-16 баров, pitch −12→0, filter 150 Hz→10 kHz, vol −20→0, staggered, pre-drop cut): https://unison.audio/how-to-create-risers/
- Soundstripe — Cinematic Riser SFX (структура тихо→эпично, low/mid/high роли): https://www.soundstripe.com/blogs/what-are-cinematic-riser-sound-effects
- Epidemic Sound — Risers (designed): https://www.epidemicsound.com/sound-effects/categories/designed/riser/
- UVI Meteor — Swell & Impact (3 rise + 4 impact слоя): https://www.uvi.net/meteor
- Sample Focus — 5 Techniques for Glitch SFX (bitcrush, stutter, noise-burst dropout, granular): https://blog.samplefocus.com/blog/5-essential-techniques-for-creating-glitch-sound-effects/
- Native Instruments — Glitch effects (bitcrush основа): https://blog.native-instruments.com/glitch-effects/
- MusicRadar — 8 ways to glitch up your sounds (stutter/beat-repeat): https://www.musicradar.com/tuition/tech/8-ways-to-glitch-up-your-sounds-618302
- LANDR — What is Ducking / Sidechains (reduction −15/−20/−35 dB, ratio 3:1-5:1): https://blog.landr.com/what-is-ducking/
- Larry Jordan — Auto-duck music under dialog (DaVinci/Audition практика): https://larryjordan.com/articles/automatically-duck-background-music-under-dialog-in-davinci-resolve/
- Editors Keys — Ultimate Guide to Sound Design (layer for realism, overuse-ошибка): https://www.editorskeys.com/blogs/news/the-ultimate-guide-to-sound-design-in-video-editing
- Finchley — Short Video Mastery / SFX for editing (pops/swipes/chimes на резах, sound-off контекст): https://www.finchley.co.uk/finchley-learning/short-video-mastery-tiktok-and-instagram-reels-using-sound-effects-for-video-editing
- techfly — Short-Form Editing (silent-scroll, slow-fast-slow ритм): https://www.techfly.in/short-form-content-editing-the-secret-to-viral-reels/
- Virlo — Short-form editing tips (нарратив-арка за 30 с): https://virlo.ai/blog/short-form-video-editing-tips
- LinkedIn Learning — Layering sound for heightened impact (Sound Design for Motion Graphics): https://www.linkedin.com/learning/sound-design-for-motion-graphics/layering-sound-for-heightened-impact
