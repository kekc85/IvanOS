# Аудит сайта: workflow

Используется когда пользователь говорит "проверь сайт" / "audit мой лендинг" / "что у меня не так".

## Шаг 0. Подтверждение что сайт принадлежит пользователю

⚠️ Скилл не для атаки на чужие сайты. Уточняем:

> "Прежде чем начну - подтверди что [URL] принадлежит тебе или ты имеешь право проводить аудит. Этот скилл для самопроверки, не для атаки на конкурентов."

Если пользователь не подтверждает - отказываемся. Если нужен blueprint атаки - это другой инструмент (`~/.business/processes/legal-attack-blueprint.md`), и он не запускается из этого скилла.

## Шаг 1. Подключение Playwright

Загружаем нужные tools через ToolSearch:

```
select:mcp__playwright__browser_navigate,mcp__playwright__browser_resize,mcp__playwright__browser_take_screenshot,mcp__playwright__browser_evaluate,mcp__playwright__browser_network_requests,mcp__playwright__browser_snapshot,mcp__playwright__browser_close
```

## Шаг 2. Заход на сайт + размер viewport

```
browser_navigate(url)
browser_resize(1440, 900)
```

## Шаг 3. Прескролл + загрузка lazy-content

```
browser_evaluate(function='() => {
  return (async () => {
    let h = 0;
    for (let i = 0; i < 40; i++) {
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise(r => setTimeout(r, 800));
      if (document.body.scrollHeight === h) break;
      h = document.body.scrollHeight;
    }
    document.querySelectorAll("img[data-src], img[loading=lazy]").forEach(img => {
      if (img.dataset.src) img.src = img.dataset.src;
      img.loading = "eager";
    });
    window.scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 3000));
    return "done";
  })();
}')
```

## Шаг 4. Снимки ключевых зон (4-6 скринов)

Целевые зоны:
- Hero (главный экран)
- Ключевые рекламные блоки (с обещаниями результата, цифрами доходов)
- Форма с офером и чек-боксами
- Подвал с реквизитами
- Политика-старт (если есть ссылка - проверить)
- Оферта-старт (если есть ссылка - проверить)

```
browser_take_screenshot(type='viewport', fullPage=false)
```

После каждого скрина - scrollTo к следующей зоне.

## Шаг 5. Проверка трекеров через network_requests

```
browser_network_requests()
```

Ищем запросы к:
- `mc.yandex.ru` (Яндекс.Метрика)
- `google-analytics.com`, `googletagmanager.com` (GA)
- `top-fwz1.mail.ru`, `top.mail.ru` (Top.Mail.Ru)
- `facebook.com/tr` (Facebook Pixel)
- `vk.com/rtrg` (VK Pixel)

Если трекеры грузятся **ДО** показа cookie-баннера и нажатия "Принять" - это нарушение.

## Шаг 6. JS-проверки

```
browser_evaluate(function='() => {
  const result = {
    cookies: document.cookie,
    has_cookie_banner: !!document.querySelector("[id*=cookie], [class*=cookie], [id*=consent], [class*=consent]"),
    has_oferta_link: !!Array.from(document.querySelectorAll("a")).find(a => /оферт|oferta/i.test(a.textContent)),
    has_privacy_link: !!Array.from(document.querySelectorAll("a")).find(a => /политик|privacy|конфиденциальн/i.test(a.textContent)),
    has_footer_with_inn: /инн[^а-я]{0,10}\\d{10,12}|огрн/i.test(document.body.innerText),
    forms_with_checkbox: Array.from(document.querySelectorAll("form")).map(f => ({
      action: f.action || "?",
      has_required_checkbox: !!f.querySelector("input[type=checkbox][required]"),
      has_consent_text: /согласен|согласие|policy/i.test(f.innerText)
    })),
    h1_text: document.querySelector("h1")?.textContent?.slice(0, 200),
    title: document.title,
    metrika_loaded: typeof ym !== "undefined",
    ga_loaded: typeof ga !== "undefined" || typeof gtag !== "undefined"
  };
  return result;
}')
```

## Шаг 7. Проверка текста политики ПДн и оферты

Если есть ссылки на оферту и политику - открываем эти страницы, выкачиваем текст:

```
browser_navigate(privacy_url)
browser_evaluate(function='() => document.body.innerText')
```

Затем прогоняем по regex:

```python
import re

# Политика ПДн должна содержать
patterns_pdn_required = [
    r'cookie|куки',
    r'(яндекс|метрик|google|analytics)',  # если на сайте есть метрика
    r'(трансгранич|иностранн|США|ОАЭ|Евросоюз)',  # если используется Telegram/Google
    r'реестр.*оператор',  # упоминание реестра РКН
    r'30.*день|30.*дней',  # срок уничтожения
    r'(перечень|список|обработчик).*(третьи лица|третьим)',  # перечень обработчиков
    r'cмз|самозанят|нпд|ип|ооо'  # реквизиты оператора
]

for p in patterns_pdn_required:
    if not re.search(p, privacy_text, re.IGNORECASE):
        violations.append(f"Политика ПДн не содержит: {p}")
```

## Шаг 8. Проверка реестра операторов ПДн

Через WebFetch обращаемся к `https://pd.rkn.gov.ru/operators-registry/operators-list/` с фильтром по ИНН пользователя.

Если ИНН не найден в реестре - нарушение ст.22 152-ФЗ, штраф до 300К₽.

## Шаг 9. Закрытие сессии

```
browser_close()
```

## Шаг 10. Формирование отчёта

См. `knowledge/audit-checklist-4-layers.md` раздел "Формат итогового отчёта".

Структура:
1. Сводка (сайт, дата, число нарушений, потенциальные штрафы)
2. Критические нарушения (с приоритетом починки)
3. Важные
4. Минорные
5. Action plan (что сделать сегодня)
6. Оценка времени и сложности
7. Ссылки на готовые документы из `materials/legal-pack/` под исправления

## Шаг 11. Сохранение отчёта

Кладём отчёт на рабочий стол: `~/Desktop/Аудит сайта - <домен> - по решению автора.md`

И конвертируем в DOCX:

```bash
pandoc отчёт.md -o отчёт.docx --from markdown --to docx --standalone
```

## Что НЕ делаем

- Не выдаём пользователю blueprint **атаки** на чужие сайты (это `~/.business/processes/legal-attack-blueprint.md`, не для распространения)
- Не делаем выводы про обороты или скрытое благосостояние владельца сайта
- Не сохраняем чужие персональные данные с сайта (если случайно увидели)
- Если в процессе обнаружили серьёзные нарушения (например, явный фишинг или мошенничество) - сообщаем пользователю что это может быть незаконный сайт и предлагаем прекратить аудит