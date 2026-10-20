# Арсенал визуальных эффектов + движок реализма (Фазы 6-7)

> Источник: ресёрч топ-зарубежки по решению автора (Awwwards/SOTD + код Stripe/Linear/Dub.co + вскрытый код Миллера example-etalon.ru/Замесина). Цель: лендинг должен выглядеть как премиум-продукт, а НЕ как плоский AI-вайрфрейм. Подключать на Фазе 6 (сборка с реальными ассетами) и Фазе 7 (движение).

## Главный инсайт (вскрытый код конкурентов)
Премиум-лендинг = **1 живой герой-объект (canvas/слоёная композиция) + CSS-reveal со stagger + бесконечные ленты + pulse + щедрые hover-transitions + smooth-scroll**. БЕЗ тяжёлых библиотек. У Миллера «второй мозг» — слоёная композиция (статичный line-art + дышащий glow + дрейфующие частицы + canvas-линии + узлы со staggered-появлением), а не один flat-элемент. Цифры **выезжают из размытия** (blur→0). Никто из конкурентов НЕ делает тёмную неонку.

## CDN (проверено)
```html
<link rel="stylesheet" href="https://unpkg.com/lenis@1.3.23/dist/lenis.css">
<script src="https://unpkg.com/lenis@1.3.23/dist/lenis.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.1/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.1/dist/ScrollTrigger.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.1/vanilla-tilt.min.js"></script>
```

## ТОП-эффекты, которые берём
1. **Aurora-градиент + grain** (CSS-only) — фон hero, сине-золотые blob под blur + SVG-noise overlay.
2. **Smooth scroll (Lenis) + reveal со stagger** (GSAP `ScrollTrigger.batch`, `once:true`).
3. **Счётчики из размытия** (`opacity+translateY+scale+blur(8px)→0`, count-up на scroll). Приём Миллера.
4. **Magnetic CTA** — кнопка тянется к курсору (`pointermove`+transform; текст тянется сильнее = глубина).
5. **3D-tilt карточки** (vanilla-tilt, `max:6-8`, glare ≤.2). На тач не init.
6. **Spotlight cursor glow** (CSS-var `--mx/--my` + radial-gradient mask) — на ТЁМНЫХ секциях.
7. **Infinite marquee** (CSS, дубль контента, `translateX -50%`, mask-fade).
8. **Kinetic gradient text** (`background-clip:text` + animated `background-position`) — акцент-слово.
9. **Живой герой-объект** (слой line-art + glow + дрейф-частицы + connection-линии + staggered узлы + сигналы offset-path).

## Что НЕ берём
Sticky horizontal scroll (бьёт mobile-конверсию) · text-scramble · полный WebGL-Igloo · тёмная неонка.

## Движок РЕАЛИЗМА (Фаза 6) — против «нарисованных» плоских блоков
- **Device-мокапы на CSS/SVG:** браузер (реальный URL-бар, favicon, светофор macOS, тень `0 40px 80px -28px`, лёгкая перспектива `rotateY/X`), телефон (notch, пузыри TG с хвостами). Внутри — реальный контент, не flat-плейсхолдер.
- **Реалистичная оплата:** банковский/CloudPayments пуш (`Зачисление · +N ₽`), привязанный к устройству, не парящий toast. Можно `stripe-screenshot-post`.
- **Генерация скиллами на максимум:** UI/текст — высокоточный CSS (диффузия врёт текст); иллюстрации (мозг/сцена) — image-gen через **БЕСПЛАТНЫЙ ChatGPT** (image_generation; **Higgsfield ЗАПРЕЩЁН — платный**); автор может дропнуть готовую картинку. Не оставлять сток-клише («AI brain» силуэт = мгновенный AI-маркер).
- **Подписи владения:** это система УЧАСТНИКА (его сайт/воронка), не автора, но БЕЗ дублей-ярлыков на каждом объекте.

## Анти-AI-slop (Фаза 4/6)
- **Шрифты характерные, не дефолт.** Sora/Manrope/Inter = «AI default». Брать distinctive (Unbounded, Geologica, Golos Text) + line-height display ≤1.06.
- **Ломать «секции стопкой»:** крупные editorial-номера (01/02/03, 120-200px, opacity .06-.12), асимметрия + наложение за край контейнера, один доминант на секцию вместо равных плиток.
- Чекбоксы ☐ → сплошные галочки/иконки/номера. Текстовые `→` и пунктир → сплошные градиентные SVG-коннекторы.
- Не дублировать hero/финал (два таймера), фразы (chip + подзаголовок одно и то же).
- VIP-тариф обязан доминировать (золотая рамка/подложка/scale).

## Мобилка + перформанс (Фаза 8, MANDATORY)
- **Mobile-first обязателен**, проверять 360/390/768/1280. Absolute-композиции (hero) — чистый mobile-fallback (стек, не наложение).
- **Перф:** урезать веса шрифтов, `font-display:swap`, `loading="lazy"` на фото, скрипты в конце `<body>`, один GSAP-тикер на Lenis, `ScrollTrigger.refresh()` после `load`.
- `@media(prefers-reduced-motion:reduce)` — глушить движение, контент видимым (счётчики = финал, reveal = показан).