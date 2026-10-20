#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strip_notes.py - вычищает служебные комментарии из СОБРАННОЙ страницы:
HTML-комментарии в разметке, секционные комментарии вёрстки в инлайн-CSS
И рабочие пометки разработчика в инлайн-JS.

Зачем: page-template.html и рабочие черновики намеренно нашпигованы пометками
для сборщика («🔴 ШАПКА - КАНОН…», «only-wide (Обо мне запрещено)», «Один блок
на 88% документа читатель просто не доживал увидеть»). Это внутренняя кухня.
В исходнике страницы на проде её быть не должно: любой читатель открывает
Ctrl+U и видит рабочие заметки, разъезды кластера и даты инцидентов.

То же самое приезжало вторым путём - из tokens.css. Комментарий разработчика
«note = тихая врезка TL;DR внутри раздела, она не должна спорить с флагоманом»
(tokens.css:494-496) уехал в прод-HTML на 16 страницах, потому что CSS
встраивается инлайн целиком, а чистились только HTML-комментарии
(ревизия по решению автора, revision-tldr-2026-08-03.md, раздел 2). Поэтому
`/* … */` внутри `<style>` снимается тем же проходом. Трогается ТОЛЬКО
содержимое `<style>`: комментарии в примерах кода внутри `<pre>` остаются.

ТРЕТИЙ путь - инлайн-`<script>` шаблона (закрыт по решению автора). Чистилка внутрь
скриптов не смотрела вовсе, а в шаблонном скрипте живут восемь русских
пометок разработчика (прогресс-бар, код-блок, якоря, лайтбокс, scrollspy…).
Они уехали в исходник 118 собранных страниц корпуса, и вместе с ними -
дословная реплика владельца, попавшая в 19 файлов и на живые страницы.
РЕШЕНИЕ: пометки в шаблоне ОСТАВЛЯЕМ (они полезны разработчику), снимает их
СБОРЩИК при рендере - build_page.build() зовёт strip_script_comments() в
конце сборки, и этот же файл повторяет проход по готовым байтам.

Закон: рабочие пометки живут в ШАБЛОНЕ, в tokens.css и в инлайн-JS шаблона,
в собранный HTML не попадают. Единственное исключение - маркеры внешних
счётчиков, которые вендор просит оставлять как есть (Яндекс.Метрика
открывает и закрывает блок комментарием), и комментарии вида `/*! … */`
(лицензии вендоров) - и в CSS, и в JS.

🔴 JS - не CSS: там `//` живёт внутри строк («https://mc.yandex.ru/…») и внутри
регулярок, а `/*` - внутри строковых литералов. Регуляркой по телу скрипта
здесь ходить нельзя: снятый «комментарий» из середины URL ломает счётчик или
лайтбокс молча. Поэтому тело скрипта разбирает посимвольный сканер scan_js()
(строки, шаблонные литералы с ${…}, регулярки, оба вида комментариев), и
снимается ТОЛЬКО то, что сканер уверенно опознал комментарием. Сканер
наткнулся на невозможное в валидном JS (незакрытая строка, перевод строки
внутри '…' или регулярки, незакрытый /* …) - скрипт НЕ трогается вовсе, а
оставшиеся в нём пометки с кириллицей уходят в барьер (см. ниже). Снять
меньше лучше, чем сломать скрипт.

Барьер: script_notes_left() ловит комментарии С КИРИЛЛИЦЕЙ, которые внутри
`<script>` всё-таки остались (разбор отказал, либо байты собраны не этим
сборщиком). Русский текст в комментарии инлайн-скрипта = рабочая пометка,
другого источника у него нет. Такая находка красит и --check, и обычный
прогон: сборка обязана падать громко, а не тихо увозить пометку в прод.

Использование:
    python3 strip_notes.py <файл.html> [ещё файлы...]        # правит на месте
    python3 strip_notes.py --check <файл.html> [...]          # только отчёт, exit 1 если грязно
    python3 strip_notes.py --selftest                         # тесты чистилки, файлы не нужны
"""
import re
import sys

# Комментарии, которые ОСТАЮТСЯ в проде: маркеры вендорских счётчиков
KEEP = (
    'Yandex.Metrika counter',
    '/Yandex.Metrika counter',
    'Google Tag Manager',
    'End Google Tag Manager',
)

COMMENT = re.compile(r'[ \t]*<!--(?!\[if)(?!<!\[endif)(.*?)-->[ \t]*\n?', re.S)
STYLE = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.S | re.I)
CSS_COMMENT = re.compile(r'[ \t]*/\*(?!!)(.*?)\*/[ \t]*\n?', re.S)

# ── JS ───────────────────────────────────────────────────────────────────────
SCRIPT = re.compile(r'(<script([^>]*)>)(.*?)(</script>)', re.S | re.I)
_TYPE_ATTR = re.compile(r'\btype\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
# type, при котором содержимое тега - именно JavaScript. Всё остальное
# (application/ld+json, application/json, text/template, importmap) - ДАННЫЕ:
# там `//` и `/*` - обычные символы, разбирать их как код запрещено.
JS_TYPES = ('', 'text/javascript', 'application/javascript', 'text/ecmascript',
            'application/ecmascript', 'module', 'text/jsx', 'module/javascript')
CYRILLIC = re.compile(r'[А-Яа-яЁё]')
# наивный поиск комментариев - ТОЛЬКО для барьера в случае отказа разбора
NAIVE_COMMENT = re.compile(r'/\*.*?\*/|//[^\n]*', re.S)

# После этих слов `/` начинает РЕГУЛЯРКУ, хотя предыдущий символ буквенный
# (`return /x/.test(s)`); после любого другого идентификатора `/` - деление.
_REGEX_AFTER_WORD = {
    'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
    'throw', 'case', 'do', 'else', 'yield', 'await',
}
_WORD_CHARS = re.compile(r'[A-Za-z0-9_$À-￿]')


def keep(body: str) -> bool:
    b = body.strip()
    return any(b == k or b.startswith(k) for k in KEEP)


def filler(m) -> str:
    """Чем заменить снятый комментарий.

    Регулярка съедает и отступ слева, и перевод строки справа. Если комментарий
    стоял на своей строке - вокруг всё равно остаётся пробельное, строка уходит
    целиком, замена пустой строкой корректна. Если комментарий стоял МЕЖДУ
    непробельными символами (хвост разметки + следующая строка текста), пустая
    замена склеивает слова: «гайд</a><!-- x -->и ещё» -> «гайд</a>и ещё».
    Поэтому в этом и только в этом случае ставим пробел.
    """
    s, a, b = m.string, m.start(), m.end()
    before = s[a - 1] if a > 0 else ''
    after = s[b] if b < len(s) else ''
    if before and after and not before.isspace() and not after.isspace():
        return ' '
    return ''


def strip_css_comments(html: str):
    """Секционные комментарии из инлайн-CSS. Только внутри <style>."""
    removed = []

    def one_style(sm):
        def sub(m):
            removed.append(' '.join(m.group(1).split())[:80])
            return filler(m)
        body = CSS_COMMENT.sub(sub, sm.group(2))
        body = re.sub(r'\n{3,}', '\n\n', body)
        return sm.group(1) + body + sm.group(3)

    return STYLE.sub(one_style, html), removed


# ── разбор JS ────────────────────────────────────────────────────────────────

def _script_type(attrs: str) -> str:
    m = _TYPE_ATTR.search(attrs or '')
    if not m:
        return ''
    return (m.group(1) or m.group(2) or m.group(3) or '').strip().lower()


def is_js(attrs: str) -> bool:
    return _script_type(attrs) in JS_TYPES


def _eat_template(js: str, i: int):
    """Тело шаблонного литерала с позиции i (сразу после ` или после }).

    Возвращает (следующая позиция, ok, открылась ли подстановка ${ ).
    """
    n = len(js)
    while i < n:
        c = js[i]
        if c == '\\':
            i += 2
            continue
        if c == '`':
            return i + 1, True, False
        if c == '$' and i + 1 < n and js[i + 1] == '{':
            return i + 2, True, True
        i += 1
    return n, False, False


def _regex_allowed(prev: str, prev_word: str) -> bool:
    """Может ли `/` в этой позиции начинать регулярку, а не быть делением."""
    if not prev:
        return True
    if prev_word:
        return prev_word in _REGEX_AFTER_WORD
    if prev in ')]':
        return False
    if prev == '.':
        return False
    return True


def scan_js(js: str):
    """Посимвольный разбор тела скрипта.

    Возвращает (comments, ok):
      comments - список (start, end, kind) для комментариев, найденных именно
                 в КОДЕ; kind - 'line' или 'block';
      ok       - разбор дошёл до конца, ничего невозможного для валидного JS
                 не встретил. ok=False -> вызывающий НЕ трогает этот скрипт.
    """
    comments = []
    i, n = 0, len(js)
    prev = ''        # последний значимый символ кода
    prev_word = ''   # последнее слово-идентификатор (для `return /x/`)
    braces = []      # стек: сколько «{» открыто внутри текущей ${ … }
    while i < n:
        c = js[i]
        if c in ' \t\r\n':
            i += 1
            continue
        # комментарии
        if c == '/' and i + 1 < n and js[i + 1] == '/':
            j = js.find('\n', i)
            j = n if j < 0 else j
            comments.append((i, j, 'line'))
            i = j
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '*':
            j = js.find('*/', i + 2)
            if j < 0:
                return comments, False
            comments.append((i, j + 2, 'block'))
            i = j + 2
            continue
        # строковые литералы
        if c in '"\'':
            j, closed = i + 1, False
            while j < n:
                d = js[j]
                if d == '\\':
                    # перенос строки экранированием - валидный JS
                    j += 2
                    continue
                if d == c:
                    closed = True
                    break
                if d == '\n':
                    return comments, False   # строка не закрылась на своей строке
                j += 1
            if not closed:
                return comments, False
            i, prev, prev_word = j + 1, c, ''
            continue
        # шаблонный литерал
        if c == '`':
            i, ok, opened = _eat_template(js, i + 1)
            if not ok:
                return comments, False
            if opened:
                braces.append(0)
            prev, prev_word = '`', ''
            continue
        if c == '{' and braces:
            braces[-1] += 1
            i, prev, prev_word = i + 1, '{', ''
            continue
        if c == '}' and braces:
            if braces[-1] == 0:
                braces.pop()
                i, ok, opened = _eat_template(js, i + 1)
                if not ok:
                    return comments, False
                if opened:
                    braces.append(0)
                prev, prev_word = '`', ''
                continue
            braces[-1] -= 1
            i, prev, prev_word = i + 1, '}', ''
            continue
        # регулярка или деление
        if c == '/':
            if not _regex_allowed(prev, prev_word):
                i, prev, prev_word = i + 1, '/', ''
                continue
            j, in_class, closed = i + 1, False, False
            while j < n:
                d = js[j]
                if d == '\\':
                    j += 2
                    continue
                if d == '\n':
                    return comments, False   # регулярка не бывает многострочной
                if d == '[':
                    in_class = True
                elif d == ']':
                    in_class = False
                elif d == '/' and not in_class:
                    closed = True
                    break
                j += 1
            if not closed:
                return comments, False
            j += 1
            while j < n and js[j].isalpha():
                j += 1
            # регулярка - значение: следующий `/` уже деление
            i, prev, prev_word = j, ')', ''
            continue
        # идентификатор / число
        if _WORD_CHARS.match(c):
            j = i
            while j < n and _WORD_CHARS.match(js[j]):
                j += 1
            prev_word = js[i:j]
            prev = js[j - 1]
            i = j
            continue
        i, prev, prev_word = i + 1, c, ''
    if braces:
        return comments, False
    return comments, True


def _cuts_for(js: str, comments):
    """Какие из найденных комментариев снимаем и каким куском.

    Правила (узкие намеренно):
      · `/*! … */` - лицензия вендора, не трогаем;
      · комментарий стоит В НАЧАЛЕ СТРОКИ (слева только отступ) - снимаем
        всегда: именно так выглядит пометка разработчика;
      · комментарий стоит ПОСЛЕ КОДА на строке - снимаем, только если внутри
        есть кириллица (рабочая пометка), иначе оставляем как есть.
    Возвращает список (start, end, replacement, текст комментария).
    """
    n = len(js)
    out = []
    for a, b, _kind in comments:
        text = js[a:b]
        if text.startswith('/*!'):
            continue
        ls = js.rfind('\n', 0, a) + 1
        le = js.find('\n', b)
        le = n if le < 0 else le
        before, after = js[ls:a], js[b:le]
        leading = before.strip() == ''
        trailing_only = after.strip() == ''
        if not leading and not CYRILLIC.search(text):
            continue
        if leading and trailing_only:
            # комментарий занимал строки целиком - строки уходят целиком
            out.append((ls, min(le + 1, n), '', text))
        elif leading:
            # слева отступ, справа код: снимаем комментарий и пробелы за ним
            k = b
            while k < n and js[k] in ' \t':
                k += 1
            out.append((a, k, '', text))
        elif trailing_only:
            # хвостовая пометка: снимаем её вместе с пробелами перед ней
            k = a
            while k > ls and js[k - 1] in ' \t':
                k -= 1
            out.append((k, le, '', text))
        else:
            # код с обеих сторон - на месте комментария остаётся один пробел
            out.append((a, b, ' ', text))
    return out


def strip_js_comments(js: str):
    """Снять пометки разработчика из тела ОДНОГО инлайн-скрипта.

    Возвращает (новое тело, [снятые тексты], ok). ok=False - разбор отказал,
    тело возвращается байт-в-байт как было.
    """
    comments, ok = scan_js(js)
    if not ok:
        return js, [], False
    cuts = _cuts_for(js, comments)
    if not cuts:
        return js, [], True
    out, last, removed = [], 0, []
    for start, end, repl, text in cuts:
        out.append(js[last:start])
        out.append(repl)
        removed.append(' '.join(text.split())[:80])
        last = end
    out.append(js[last:])
    body = ''.join(out)
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body, removed, True


def strip_script_comments(html: str):
    """Пометки разработчика из ВСЕХ инлайн-JS страницы. Данные (ld+json) не трогаем."""
    removed = []
    failed = []

    def one(m):
        if not is_js(m.group(2)):
            return m.group(0)
        body, gone, ok = strip_js_comments(m.group(3))
        if not ok:
            failed.append(m.start())
            return m.group(0)
        removed.extend(gone)
        return m.group(1) + body + m.group(4)

    return SCRIPT.sub(one, html), removed, failed


def script_notes_left(html: str):
    """БАРЬЕР: пометки с кириллицей, оставшиеся внутри инлайн-JS.

    Русский текст в комментарии инлайн-скрипта - всегда рабочая пометка:
    ни шаблон, ни вендорский счётчик легального русского комментария не несут.
    Если разбор скрипта отказал, ищем наивной регуляркой и помечаем находку -
    лучше ложная краснота гейта, чем тихая пометка в прод.
    """
    left = []
    for m in SCRIPT.finditer(html):
        if not is_js(m.group(2)):
            continue
        body = m.group(3)
        comments, ok = scan_js(body)
        if ok:
            for a, b, _k in comments:
                text = body[a:b]
                if CYRILLIC.search(text):
                    left.append(' '.join(text.split())[:80])
        else:
            for mm in NAIVE_COMMENT.finditer(body):
                if CYRILLIC.search(mm.group(0)):
                    left.append('[разбор JS отказал] '
                                + ' '.join(mm.group(0).split())[:80])
    return left


def strip(html: str):
    removed = []

    def sub(m):
        body = m.group(1)
        if keep(body):
            return m.group(0)
        removed.append(' '.join(body.split())[:80])
        # комментарий стоял на своей строке - убираем строку целиком,
        # стоял между непробельными символами - оставляем пробел (см. filler)
        return filler(m)

    out = COMMENT.sub(sub, html)
    out, css_removed = strip_css_comments(out)
    out, js_removed, js_failed = strip_script_comments(out)
    notes = removed + ['CSS: ' + x for x in css_removed] + ['JS: ' + x for x in js_removed]
    if js_failed:
        notes.append('JS: разбор отказал у %d скриптов - они не тронуты' % len(js_failed))
    return out, notes


def main(argv):
    check = '--check' in argv
    files = [a for a in argv if not a.startswith('--')]
    # пустой список файлов - это ошибка вызова, а не «чисто»: раньше
    # `strip_notes.py --check` молча возвращал 0 и любой гейт над ним зеленел
    if not files:
        print('ОШИБКА strip_notes: не передан ни один файл.\n'
              '    python3 strip_notes.py <файл.html> [ещё файлы...]\n'
              '    python3 strip_notes.py --check <файл.html> [...]\n'
              '    python3 strip_notes.py --selftest', file=sys.stderr)
        return 2
    dirty = 0
    leaked = 0
    for f in files:
        src = open(f, encoding='utf-8').read()
        out, removed = strip(src)
        if removed:
            dirty += 1
        print(f'{f}: служебных комментариев {len(removed)}')
        for r in removed:
            print(f'    - {r}')
        if not check and removed:
            open(f, 'w', encoding='utf-8').write(out)
            print(f'    -> вычищено, осталось {len(re.findall(COMMENT, out))} (вендорские маркеры)')
        # барьер: смотрим на те байты, которые реально уедут в прод
        left = script_notes_left(out)
        if left:
            leaked += 1
            print(f'    🔴 БАРЬЕР: в <script> остались рабочие пометки ({len(left)}):')
            for r in left:
                print(f'        - {r}')
    if leaked:
        print('ОШИБКА strip_notes: пометки разработчика внутри <script> снять не удалось '
              '(см. 🔴 выше). Пометка уедет в исходник страницы - сборка остановлена.',
              file=sys.stderr)
        return 1
    return 1 if (check and dirty) else 0


# ── селфтест ─────────────────────────────────────────────────────────────────
# Класс дефекта по решению автора: чистилка внутрь <script> не смотрела, восемь русских
# пометок шаблона уехали в 118 собранных страниц. Тесты держат ДВА края сразу:
# пометка обязана сниматься, а код скрипта обязан остаться байт-в-байт.

def selftest():
    results = []

    def check_(name, cond, detail=''):
        results.append((name, bool(cond), detail))

    def page(js, attrs=''):
        return '<html><body><script%s>\n%s\n</script></body></html>' % (attrs, js)

    # 1. пометка с кириллицей в начале строки снимается (оба вида)
    js = '  /* прогресс-бар чтения: полосу ведёт CSS */\n  var a = 1;'
    out, gone, ok = strip_js_comments(js)
    check_('блочная пометка с кириллицей снимается',
           ok and 'прогресс-бар' not in out and 'var a = 1;' in out, repr(out))
    js = '  // якорь-ссылка у каждого h2\n  var a = 1;'
    out, gone, ok = strip_js_comments(js)
    check_('строчная пометка с кириллицей снимается',
           ok and '//' not in out and 'var a = 1;' in out, repr(out))

    # 2. `//` внутри строки-URL не трогается (счётчик Метрики)
    js = 'var r = "https://mc.yandex.ru/metrika/tag.js";\nvar q = \'http://x/y//z\';'
    out, gone, ok = strip_js_comments(js)
    check_('`//` внутри строки-URL цел', ok and out == js and not gone, repr(out))

    # 3. `/*` внутри строкового литерала не трогается
    js = 'var s = "/* не комментарий */";\nvar t = \'a /* b\';'
    out, gone, ok = strip_js_comments(js)
    check_('`/*` внутри строки цел', ok and out == js and not gone, repr(out))

    # 4. `//` внутри регулярки не трогается
    js = 'var u = s.replace(/\\/\\//g, "/");\nif (/^\\/\\//.test(s)) { u = 1; }'
    out, gone, ok = strip_js_comments(js)
    check_('`//` внутри регулярки цело', ok and out == js and not gone, repr(out))

    # 5. деление после идентификатора и скобки не принимается за регулярку
    js = 'var k = (a + b) / 2 / c;\nvar m = arr[0] / n;\nvar p = fn() / 2;'
    out, gone, ok = strip_js_comments(js)
    check_('деление не путается с регуляркой', ok and out == js and not gone, repr(out))

    # 6. хвостовая пометка с кириллицей снимается, код остаётся
    js = 'var a = 1; // так надо, иначе едет вёрстка\nvar b = 2;'
    out, gone, ok = strip_js_comments(js)
    check_('хвостовая пометка снимается, код цел',
           ok and out.startswith('var a = 1;\n') and 'var b = 2;' in out
           and 'вёрстка' not in out, repr(out))

    # 7. хвостовой ASCII-комментарий не трогаем (узкое правило: снять меньше)
    js = 'var a = 1; // fallback for old Safari\nvar b = 2;'
    out, gone, ok = strip_js_comments(js)
    check_('хвостовой ASCII-комментарий оставлен', ok and out == js, repr(out))

    # 8. лицензия вендора остаётся
    js = '/*! jslib v1.2 | MIT */\nvar a = 1;'
    out, gone, ok = strip_js_comments(js)
    check_('`/*!` лицензия не снимается', ok and out == js, repr(out))

    # 9. шаблонный литерал с ${} и «комментарием» внутри текста
    js = 'var h = `<b>${x}</b> // не комментарий`;\nvar y = 2;'
    out, gone, ok = strip_js_comments(js)
    check_('шаблонный литерал цел', ok and out == js and not gone, repr(out))

    # 10. отказ разбора: незакрытая строка - не трогаем НИЧЕГО
    js = 'var s = "не закрыта;\n/* пометка разработчика */\nvar a = 1;'
    out, gone, ok = strip_js_comments(js)
    check_('незакрытая строка = отказ разбора, байты не тронуты',
           (not ok) and out == js and not gone, repr(out)[:90])

    # 11. барьер видит пометку, которую снять не удалось
    left = script_notes_left(page(js))
    check_('барьер ловит пометку при отказе разбора',
           len(left) == 1 and 'разбор JS отказал' in left[0], str(left))
    check_('барьер молчит на чистом скрипте',
           script_notes_left(page('var r = "https://x/y";')) == [], '')

    # 12. ld+json - данные, а не код: не трогаем и в барьер не тащим
    ld = ('{"@type":"Article","url":"https://<твой-домен>/x/",'
          '"name":"Нейросети // и как их считать"}')
    src = page(ld, ' type="application/ld+json"')
    out, _, failed = strip_script_comments(src)
    check_('JSON-LD не тронут', out == src and not failed, out[:80])
    check_('JSON-LD не идёт в барьер', script_notes_left(src) == [], '')

    # 13. сквозной strip(): HTML + CSS + JS одним проходом, вендор-маркер жив
    src = ('<!-- рабочая пометка -->\n'
           '<!-- Yandex.Metrika counter -->\n'
           '<style>/* секция шапки */\n.a{color:red}</style>\n'
           '<script>\n  /* пометка в скрипте */\n  var u = "https://mc.yandex.ru/x.js";\n</script>')
    out, removed = strip(src)
    check_('strip: HTML-пометка снята', 'рабочая пометка' not in out, out[:60])
    check_('strip: вендор-маркер Метрики оставлен', 'Yandex.Metrika counter' in out)
    check_('strip: CSS-пометка снята', 'секция шапки' not in out)
    check_('strip: JS-пометка снята', 'пометка в скрипте' not in out)
    check_('strip: URL счётчика цел', 'https://mc.yandex.ru/x.js' in out, out[-90:])
    check_('strip: JS-находка помечена в отчёте',
           any(r.startswith('JS: ') for r in removed), str(removed))

    # 14. идемпотентность: второй проход ничего не меняет
    out2, removed2 = strip(out)
    check_('strip идемпотентен', out2 == out and not [r for r in removed2 if r.startswith('JS: ')],
           str(removed2))

    ok_n = 0
    for name, good, detail in results:
        print(('  OK   ' if good else '  FAIL ') + name
              + (('  [%s]' % detail) if detail and not good else ''))
        ok_n += 1 if good else 0
    print('selftest strip_notes: %d/%d прошло' % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
