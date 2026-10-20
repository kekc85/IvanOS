# Технический конвейер сторис-деки

Рабочий эталон живёт в `~/highlight-work/render/` (дека «мой путь», принята по решению автора). Новый проект = копия этого каркаса в `~/highlight-work/<slug>/render/` (папка ВНЕ iCloud).

## Каркас

```
render/
├── slides-benchmark.json   ← вся копия деки (один источник истины текстов)
├── build-premium.mjs       ← статика: photo / barriers / funnel / day / cta → out/slide-NN.png
├── record-anim.mjs         ← анимированные кадры (hook 01 / barriers 07 / funnel 09 / CTA 16): Playwright recordVideo → _vid/anim-NN.webm
├── record-days.mjs         ← кадры с живым медиа (скролл лендинга, телефоны с роликами)
├── render-overlays.mjs     ← overlay-PNG поверх пруф-видео (прозрачный PNG / фон+кроп)
├── img/ incoming/ _vid/    ← ассеты: фото, скрины, исходные видео
├── out/                    ← готовые slide-NN.png, video-NN.mp4, anim-NN.mp4
├── review/                 ← стоп-кадры самопроверки
└── show*/                  ← паблиш-папки с дека-html (уникальные имена файлов на ревизию)
```

## Ключевые механики (не переизобретать)

**Типограф против висячих слов** - в каждом генераторе:
```js
const ty=t=>String(t).replace(/(^|[\s(«])(и|а|но|с|в|у|к|о|на|по|за|не|из|от|до|же|для|под|при)\s/g,(m,p,w)=>p+w+' ');
const nb=t=>ty(ty(String(t))).replace(/ (?=[^<> ]+(?:<\/span>)?\s*$)/,' ');
```
Большие заголовки (≥80px): NBSP-цепочки могут дать overflow - при нужде жёсткий `<br>` (`s.title.replace(" на ","<br>на ")`).

**Playwright recordVideo** (в chromium h264 внутри страницы не играет - для вставляемых видео VP9 webm):
- отдельная tmp-папка на кадр `_vid/tmp-N` (иначе rename хватает чужой webm)
- viewport 1080×1920, `waitForTimeout(DUR[n])`, потом rename webm

**ffmpeg-рецепты:**
```bash
# webm → mp4 сторис
ffmpeg -y -i _vid/anim-NN.webm -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -movflags +faststart out/anim-NN.mp4
# прозрачный overlay-PNG поверх видео-пруфа (масштаб+центр-кроп до 1080×1920)
ffmpeg -y -i incoming/proof.mov -i overlay.png -filter_complex "[0:v]scale=1080:-2,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2[bg];[bg][1:v]overlay=0:0,format=yuv420p" -t 13.5 -an -c:v libx264 -preset veryfast -crf 21 out/video-01.mp4
# фон-PNG + кроп видео-таблицы в окно + fade-маска краёв
ffmpeg -y -loop 1 -i bg.png -i incoming/pay.mov -i fade.png -filter_complex "[1:v]crop=W:H:X:Y,scale=1080:-2[v];[0:v][v]overlay=0:700[t];[t][2:v]overlay=0:0,format=yuv420p" -t 11.4 -an -c:v libx264 -preset veryfast -crf 21 out/video-02.mp4
# стоп-кадр на проверку (видео - в содержательной фазе, не в начале)
ffmpeg -y -ss 6 -i out/anim-NN.mp4 -frames:v 1 review/kNN.png
```

**Дизайн-токены деки «мой путь»:** фон #171008/#241712, cream #F7EFE2, gold #E8B25F, terra #E0552A (цвет денег/действия); Unbounded (заголовки) / Manrope (текст) / JetBrains Mono (кикеры). Кикер = моно-uppercase на тёмной пилюле. Новая дека под другой бренд - токены из brandkit, но роли цветов сохранить (один акцент = деньги/действие).

**Сейф-зоны:** первый текст y≥170, низ контента y≤1720. Скрим фото-кадров: `linear-gradient(0deg, rgba(8,5,3,.985) 0%, .93 26%, .58 46%, 0 66%)` + text-shadow заголовка.

**Анимации:** мягкий пульс `@keyframes ping{0%{box-shadow:0 0 0 0 rgba(224,85,42,.4)}70%{box-shadow:0 0 0 15px rgba(224,85,42,0)}...}` 3.2-3.4s ease-in-out; вход карточек - чередование inL/inR с лёгким rotate; НИКАКИХ shine-sweep.

## Паблиш и кэш-барьер

```bash
# сервер (детерминированный порт)
cd render/showN && nohup python3 -m http.server 8730 --bind 127.0.0.1 >/dev/null 2>&1 &
# каждая ревизия = НОВЫЙ префикс имён (b28-*, b29-*) + новая дека deck-b28.html
# заголовок деки: «ВЕРСИЯ B28 - если видишь этот заголовок, кэш сброшен»
# проверка КАЖДОЙ ссылки:
for f in <все файлы>; do curl -s -o /dev/null -w '%{http_code}' "http://localhost:8730/$f"; done  # все 200
```

Финальное сообщение автору: ссылка на деку + инлайн стоп-кадры изменённых кадров в чат + что изменилось по пунктам. НЕ в Telegram-бот.
