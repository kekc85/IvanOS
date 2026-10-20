#!/usr/bin/env python3
"""SEO-хвост публикации: каждая новая статья автоматически уходит в индекс везде.

Портируемый инструмент: ВСЕ личные значения (домен, FTP, счётчик Метрики, IndexNow-ключ)
живут в конфиге `~/.config/seo-publish.json` (или путь через --config / env SEO_PUBLISH_CONFIG).
В коде и в скилле персональных данных нет - инструмент реплицируется ученику как есть.

Что делает за один прогон:
  1. FTPS-листинг корня сайта -> актуальный список публичных страниц
     (папки и файлы с префиксом page_prefix, корневые страницы, публичные лендинги).
  2. sitemap.xml НЕ собирает сам, а делегирует владельцу - sitemap_rebuild.py
     (см. «ОДИН ВЛАДЕЛЕЦ КАРТЫ» ниже). Путь к владельцу - поле sitemap_rebuild в конфиге.
  3. Гейт каждой НОВОЙ страницы: 200 + canonical + Метрика + JSON-LD.
     Чего не хватает - вшивает сам и перезаливает (self-healing, не зависит от памяти модели).
  4. IndexNow-пинг (yandex.com + api.indexnow.org) ТОЛЬКО новых URL (или переданных через --url).
     Google отдельного пинга не имеет (sitemap-ping закрыт в 2023): Google читает обновлённый
     sitemap.xml, поданный в Search Console.

🔴 ОДИН ВЛАДЕЛЕЦ КАРТЫ (зафиксировано, разбор «два владельца sitemap.xml»).
Карту сайта собирает и заливает РОВНО ОДИН скрипт - sitemap_rebuild.py. Здесь прямой
сборки и заливки sitemap.xml БОЛЬШЕ НЕТ.
Почему: живая карта несёт слой image (image:image / image:title, namespace sitemap-image)
и даты из реестра содержимого (content-sha-registry.json). Здешняя build_sitemap() ни
того, ни другого не умеет - она пишет голый urlset. Пока этот файл заливал карту сам,
первый же штатный прогон SEO-хвоста молча затирал живую карту с картинками плоской
и обнулял слой дат: два владельца одного файла = гонка, в которой выигрывает тот, кто
отработал последним.
Теперь: прогон делегирует пересборку владельцу (путь - поле sitemap_rebuild в конфиге).
Пути нет или он не найден - ГРОМКИЙ ОТКАЗ с ненулевым кодом, а не тихая сборка мимо
владельца. Функция build_sitemap() ниже оставлена как библиотечная: её вызывает сам
sitemap_rebuild.py в аварийном режиме --без-картинок, но НЕ этот прогон.

Запуск после публикации статьи:  seo_publish.py --url <живой URL статьи>
Самолечение всего сайта (синк):  seo_publish.py --self-heal
Прогон вхолостую (ничего не льём): seo_publish.py --dry-run

Пароль FTP: Keychain (сервис = ftp_host, аккаунт = ftp_user) -> env FTPPASS -> файл ~/.ftppass.
IndexNow-ключ: если в конфиге пусто - генерится сам, файл <ключ>.txt заливается в корень сайта
(ключ по стандарту IndexNow публичен, секретом не является).

Первичная настройка ученика (один раз):
  1. Скопировать шаблон конфига из lead-magnit/config.md -> ~/.config/seo-publish.json, вписать своё.
  2. Положить FTP-пароль в Keychain:  security add-internet-password -a <ftp_user> -s <ftp_host> -w <пароль>
"""
import argparse, html as htmlmod, json, os, re, secrets, subprocess, sys, tempfile
from datetime import datetime

MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
CONFIG_DEFAULT = os.path.expanduser("~/.config/seo-publish.json")


def load_config(path):
    p = path or os.environ.get("SEO_PUBLISH_CONFIG") or CONFIG_DEFAULT
    if not os.path.exists(p):
        sys.exit(f"Конфиг не найден: {p}. Шаблон - в lead-magnit/config.md (раздел SEO-хвост)")
    cfg = json.load(open(p))
    for req in ("domain", "ftp_host", "ftp_user", "ftp_root", "metrika_id"):
        if not cfg.get(req):
            sys.exit(f"В конфиге {p} нет обязательного поля: {req}")
    cfg["_path"] = p
    cfg.setdefault("redirected", [])
    cfg.setdefault("skip_flat", [])
    cfg.setdefault("landing_dirs", [])
    # SITEMAP-ПРЕДУСЛОВИЕ (по решению автора, доразбор И6.9/И6.1): FTP-листинг корня
    # НЕрекурсивный (см. parse_listing) - директории-хабы (tema/) и будущие
    # глоссарные несут СВОИ под-директории со страницами (tema/<slug>/index.html),
    # листинг корня их не видит вовсе. hub_dirs - явный список таких директорий
    # уже существующих сегодня; glossary_dirs - тот же механизм ЗАРАНЕЕ для
    # глоссария, которого ещё нет (пустой список - шаг НЕ делает лишних сетевых
    # вызовов, см. parse_listing).
    cfg.setdefault("hub_dirs", [])
    cfg.setdefault("glossary_dirs", [])
    # sitemap-гигиена (по решению автора): пути, которые формально проходят фильтры выше
    # (landing_dirs / root_pages), но не место им в публичном индексе - noindex-страницы,
    # мёртвые формы. Список - в конфиге, не хардкодом в parse_listing(), чтобы ученик мог
    # завести свои исключения без правки движка. Применяется в parse_listing() ниже и
    # наследуется ОБОИМИ потребителями индекса - sitemap_rebuild.py и llms_rebuild.py -
    # так гейт паритета между ними не рвётся.
    cfg.setdefault("sitemap_exclude", [])
    cfg.setdefault("page_prefix", "guide-")
    # ОДИН ВЛАДЕЛЕЦ КАРТЫ (см. шапку): путь к sitemap_rebuild.py - единственному, кто
    # имеет право собирать и заливать sitemap.xml. Дефолт пустой СОЗНАТЕЛЬНО: путь у
    # каждого свой, а угаданный путь хуже отсутствующего - тихо соберёт карту не тем
    # движком. Пусто -> прогон откажется трогать карту громко (sitemap_owner ниже).
    cfg.setdefault("sitemap_rebuild", "")
    cfg.setdefault("root_pages", {"index.html": ["/", "1.0"]})
    cfg.setdefault("author_name", "")
    cfg.setdefault("author_url", cfg["domain"])
    return cfg


def ftp_pass(cfg):
    # Keychain есть только на macOS; на Linux-релее бинаря security нет вовсе -
    # без try ловим FileNotFoundError и никогда не доходим до FTPPASS/~/.ftppass
    try:
        r = subprocess.run(["security", "find-internet-password", "-a", cfg["ftp_user"],
                            "-s", cfg["ftp_host"], "-w"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    if os.environ.get("FTPPASS"):
        return os.environ["FTPPASS"]
    p = os.path.expanduser("~/.ftppass")
    if os.path.exists(p):
        return open(p).read().strip()
    sys.exit("FTP-пароль не найден (Keychain / env FTPPASS / ~/.ftppass)")


def mask_cmd(cmd):
    """Строка команды, безопасная для лога и исключения: креды заменены заглушкой.

    🔴 УТЕЧКА КЛАССА, НЕ ЭКЗЕМПЛЯРА (по решению автора). Пароль стоял прямо в argv, и
    любое падение печатало его целиком: `subprocess.TimeoutExpired` кладёт cmd в
    текст исключения, traceback уезжает в лог волны и оседает на диске. За сутки
    осел дважды. Лечится в ДВА рубежа, оба ниже: креды больше не едут в argv
    (рубеж 1, curl читает их из конфига на stdin), а всё, что всё-таки печатает
    команду, проходит через эту функцию (рубеж 2, страховка на будущее)."""
    out = []
    skip = False
    for a in (cmd if isinstance(cmd, (list, tuple)) else [str(cmd)]):
        a = str(a)
        if skip:
            out.append("<скрыто>")
            skip = False
            continue
        if a in ("--user", "-u"):
            out.append(a)
            skip = True
            continue
        # форма, склеенная в одном аргументе, и голый логин:пароль в URL
        a = re.sub(r"(--user[=\s]+)\S+", r"\1<скрыто>", a)
        a = re.sub(r"(ftps?://)[^/@\s]+:[^/@\s]+@", r"\1<скрыто>@", a)
        out.append(a)
    return " ".join(out)


def curl(args, **kw):
    """curl без кредов в argv.

    РУБЕЖ 1. `--user <логин:пароль>` изымается из аргументов и передаётся через
    конфиг на stdin (`-K -`, формат `user = "..."`). Пароля не остаётся ни в
    argv, ни в `ps aux`, ни в тексте исключения. Механизм проверен живым
    прогоном на этой машине до правки: `printf 'user = "..."' | curl -K - …`
    вернул http=200.
    РУБЕЖ 2. Любое исключение подмены не переживает: перехватываем и
    перевыбрасываем с ЗАМАСКИРОВАННОЙ командой, чтобы traceback был чист даже
    если креды когда-нибудь придут иным путём."""
    args = list(args)
    cred = None
    if "--user" in args:
        i = args.index("--user")
        if i + 1 < len(args):
            cred = args[i + 1]
            del args[i:i + 2]
    cmd = ["curl", "--ftp-ssl", "--insecure", "-sS"]
    if cred is not None:
        cmd += ["-K", "-"]
        kw.setdefault("input", ('user = "%s"\n' % cred).encode("utf-8"))
    cmd += args
    try:
        return subprocess.run(cmd, capture_output=True, text=False, timeout=kw.pop("timeout", 180), **kw)
    except subprocess.TimeoutExpired as e:
        raise subprocess.TimeoutExpired(mask_cmd(cmd), e.timeout,
                                        output=e.output, stderr=e.stderr) from None
    except subprocess.SubprocessError as e:
        raise RuntimeError(f"curl отказал: {mask_cmd(cmd)} :: {type(e).__name__}") from None


def ssh_listing(cfg):
    """Список корня сайта ОДНИМ ssh-соединением. Формат тот же `ls -l`, что у
    FTP, поэтому parse_listing() читает его без единой правки.

    ЗАЧЕМ (по решению автора). FTP-листинг корня встал: отдаёт ровно 9824 байта и на
    100 с, и на 300 с - это не «медленно», это обрыв, и увеличение таймаута его
    не лечит. Канон движка (`scripts/seo/README.md`, раздел анти-бан контура)
    уже объявил рабочим второй канал: «SSH на хостинг ВКЛЮЧЁН (по решению автора)…
    сверка всего сайта = ОДНО соединение вместо ~160 FTP-команд». Инструмент про
    него не знал и продолжал ходить зависшим FTP.

    Логин НЕ выводится из ftp_user и НЕ зашивается в код: этот файл раздаётся
    ученикам, и автор-специфичный адрес в нём был бы утечкой. Берётся ключ
    `ssh_login` конфига; ключа нет - возвращаем None, и вызывающий честно идёт
    прежним путём."""
    login = (cfg or {}).get("ssh_login")
    if not login:
        return None
    root = str(cfg.get("ftp_root", "")).strip("/")
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
           "-o", "ConnectTimeout=20", login, f"ls -l {root}/"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=False, timeout=120)
    except subprocess.SubprocessError as e:
        print(f"ssh-листинг не вышел ({type(e).__name__}), иду прежним путём", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"ssh-листинг вернул {r.returncode}: "
              f"{r.stderr.decode('utf-8', 'ignore')[:200]}", file=sys.stderr)
        return None
    return r.stdout.decode("utf-8", "ignore")


def ftp_listing(cfg, pw):
    r = curl(["--user", f'{cfg["ftp_user"]}:{pw}', f'ftp://{cfg["ftp_host"]}{cfg["ftp_root"]}/'], timeout=600)
    if r.returncode != 0:
        sys.exit(f"FTP-листинг не получен: {r.stderr.decode()[:200]}")
    return r.stdout.decode("utf-8", "ignore")


def listing(cfg, pw):
    """Единая точка получения списка корня: сперва ssh, при неудаче - ftp.

    ПОЧЕМУ SSH ПЕРВЫМ, А НЕ ФЛАГОМ. Флаг требует, чтобы кто-то ЗНАЛ про аварию и
    вспомнил его добавить - а сегодняшний отказ выглядел как молчаливое зависание
    посреди ночного прогона. Порядок «ssh, иначе ftp» чинит случай сам и ничего
    не отнимает: нет ключа `ssh_login`, нет доступа, пустой ответ - тихо едем
    прежним FTP-путём, поведение старых вызывающих не меняется ни на шаг.
    Возвращает (текст листинга, каким каналом получен)."""
    text = ssh_listing(cfg)
    if text and len(text.splitlines()) > 1:
        return text, "ssh"
    return ftp_listing(cfg, pw), "ftp"


def ftp_dir_listing(cfg, pw, subdir):
    """Листинг ОДНОЙ поддиректории корня (не рекурсивно дальше неё). Нужен для
    hub_dirs/glossary_dirs: обычный ftp_listing() читает только корень и внутрь
    tema/ (и будущего глоссария) не заходит - см. SITEMAP-ПРЕДУСЛОВИЕ в
    load_config(). Директория ещё не создана / временная ошибка FTP - пустая
    строка (мягкий пропуск): для glossary_dirs=[] это штатный случай на будущее,
    громкий отказ здесь не нужен - список директорий пуст сегодня."""
    r = curl(["--user", f'{cfg["ftp_user"]}:{pw}',
              f'ftp://{cfg["ftp_host"]}{cfg["ftp_root"]}/{subdir}/'])
    if r.returncode != 0:
        return ""
    return r.stdout.decode("utf-8", "ignore")


def parse_hub_subdirs(subdir, listing):
    """Строки листинга поддиректории-хаба -> страницы /{subdir}/{slug}/.

    В отличие от корня (parse_listing), здесь НЕТ фильтра по page_prefix: каждая
    вложенная директория хаба/глоссария САМА ПО СЕБЕ целевая страница
    (index.html внутри), а не гайд с префиксом guide-.

    🔴 ФИКС (приёмка по решению автора, BLOKER): у /slovar/ (глоссарий) есть СВОЙ index.html
    прямо в корне поддиректории - он живёт как страница /{subdir}/ наравне со
    своими вложенными терминами /{subdir}/{slug}/. Раньше цикл ловил только
    строки-директории (perm.startswith("d")) и молча пропускал файл index.html
    внутри листинга /slovar/ - сам корень хаба/глоссария никогда не попадал ни
    в sitemap.xml, ни в llms.txt. Для /tema/ такого файла в листинге нет
    (проверено живьём) - поведение хабов не меняется, просто has_root_index
    остаётся False."""
    now = datetime.now()
    pages = []
    has_root_index, root_mtime = False, None
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        perm, name = parts[0], parts[-1]
        if name in (".", ".."):
            continue
        mon, day, tail = parts[5], int(parts[6]), parts[7]
        if ":" in tail:
            year = now.year if MONTHS.get(mon, 1) <= now.month else now.year - 1
        else:
            year = int(tail)
        mtime = f"{year}-{MONTHS.get(mon, 1):02d}-{day:02d}"
        if perm.startswith("d"):
            pages.append((f"/{subdir}/{name}/", mtime, "0.7"))
        elif perm.startswith("-") and name == "index.html":
            has_root_index, root_mtime = True, mtime
    if has_root_index:
        pages.append((f"/{subdir}/", root_mtime, "0.7"))
    return pages


def parse_listing(cfg, listing):
    now = datetime.now()
    pages, prefix = [], cfg["page_prefix"]
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        perm, name = parts[0], parts[-1]
        mon, day, tail = parts[5], int(parts[6]), parts[7]
        if ":" in tail:
            year = now.year if MONTHS.get(mon, 1) <= now.month else now.year - 1
        else:
            year = int(tail)
        mtime = f"{year}-{MONTHS.get(mon, 1):02d}-{day:02d}"
        if perm.startswith("d"):
            if name in cfg["redirected"]:
                continue
            # 🔴 РОДОВАЯ СТРАНИЦА В ДИРЕКТОРИИ (по решению автора, разбор «карта с 301»).
            # root_pages ключуется ИМЕНЕМ ИЗ ЛИСТИНГА, а листинг корня отдаёт
            # директорию как голое имя (blog), а не как blog/index.html. Пока
            # ключ вида "<dir>/index.html" не читался здесь, запись в конфиге
            # просто не срабатывала ни разу: сайт переехал на /blog/, конфиг это
            # честно объявил, а карта родовую страницу теряла целиком (её больше
            # не давала ни эта ветка, ни файловая - blog.html ушёл в redirected).
            # Явный ключ сильнее эвристик ниже: он несёт и адрес, и priority.
            root_key = f"{name}/index.html"
            if root_key in cfg["root_pages"]:
                path, prio = cfg["root_pages"][root_key]
                pages.append((path, mtime, prio))
                continue
            if name.startswith(prefix):
                pages.append((f"/{name}/", mtime, "0.8"))
            elif name in cfg["landing_dirs"]:
                pages.append((f"/{name}/", mtime, "0.7"))
        elif perm.startswith("-") and name.endswith(".html"):
            # 🔴 redirected РАБОТАЕТ И ДЛЯ ФАЙЛОВ (по решению автора, тот же разбор).
            # Список redirected читался ТОЛЬКО в ветке директорий, поэтому плоский
            # файл-заглушка (guide-x.html, отдающий 301 на /guide-x/) продолжал
            # попадать в карту, сколько его туда ни вписывай: 51 адрес карты вёл
            # на переадресацию. Для панели вебмастера это «страница с
            # переадресацией», то есть адрес вне индекса. Заглушка остаётся на
            # диске ради старых ссылок, но в карте ей места нет - карта описывает
            # то, что отвечает 200.
            if name in cfg["redirected"]:
                continue
            if name in cfg["root_pages"]:
                path, prio = cfg["root_pages"][name]
                pages.append((path, mtime, prio))
            elif name.startswith(prefix) and name not in cfg["skip_flat"]:
                pages.append((f"/{name}", mtime, "0.8"))
    # SITEMAP-ПРЕДУСЛОВИЕ: hub_dirs (tema/ и т.п.) и glossary_dirs (заранее,
    # пустой список сегодня) листятся ОТДЕЛЬНЫМ запросом каждая - корневой
    # листинг выше их подстраницы никогда не видел. Пустой список обоих ключей
    # (дефолт в load_config) -> ни одного лишнего сетевого вызова, поведение
    # для конфигов без hub_dirs не меняется.
    hub_like = list(cfg.get("hub_dirs", [])) + list(cfg.get("glossary_dirs", []))
    if hub_like:
        pw = ftp_pass(cfg)
        for subdir in hub_like:
            sub_listing = ftp_dir_listing(cfg, pw, subdir)
            if sub_listing:
                pages.extend(parse_hub_subdirs(subdir, sub_listing))
    excluded = set(cfg.get("sitemap_exclude", []))
    if excluded:
        pages = [p for p in pages if p[0] not in excluded]
    return sorted(set(pages))


def build_sitemap(cfg, pages):
    """ПЛОСКАЯ карта без image-слоя. 🔴 БИБЛИОТЕЧНАЯ функция, не точка входа.

    Единственный законный вызывающий - sitemap_rebuild.py в аварийном режиме
    --без-картинок, который знает, что сносит image-теги, и сам это печатает.
    Результат этой функции НЕЛЬЗЯ заливать на прод из этого файла: она не умеет ни
    image:image/image:title, ни дат из реестра содержимого - заливка затрёт оба слоя
    (см. «ОДИН ВЛАДЕЛЕЦ КАРТЫ» в шапке). Заливка карты живёт только в sitemap_rebuild.py.
    """
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, mtime, prio in pages:
        out.append(f'  <url><loc>{cfg["domain"]}{path}</loc><lastmod>{mtime}</lastmod><priority>{prio}</priority></url>')
    out.append("</urlset>")
    return "\n".join(out) + "\n"


SITEMAP_REFUSAL = (
    "СТОП: sitemap собирает sitemap_rebuild.py, прямая сборка отключена "
    "(сотрёт image-слой и реестр дат).\n"
    "   Причина: живая карта несёт image:image/image:title и даты из реестра "
    "содержимого; здешняя build_sitemap() пишет голый urlset и оба слоя обнуляет.\n"
    "   Как включить: в конфиге {cfg_path} задать поле \"sitemap_rebuild\" - "
    "полный путь к sitemap_rebuild.py.\n"
    "   Пересобрать карту руками прямо сейчас: python3 <путь>/sitemap_rebuild.py "
    "(проверка без заливки: --проверка)"
)


def sitemap_owner(cfg, pages, pw, dry=False):
    """Делегировать пересборку карты владельцу (sitemap_rebuild.py), а если
    владельца нет (ученик без своего сборщика) - честный фолбэк: собрать
    ПЛОСКУЮ карту (без image-слоя и без дат реестра) и сказать об этом вслух.

    У АВТОРА поведение прежнее: его конфиг всегда несёт рабочий sitemap_rebuild,
    ветка фолбэка у него не срабатывает никогда - это правило класса «работает у
    автора, ломается у ученика» (R191), а не смена контракта функции.

    Молчаливый пропуск карты хуже честного предупреждения, поэтому фолбэк
    ГРОМКИЙ (печатает причину в stderr), а не тихий. Настоящий отказ (владелец
    ЕСТЬ, но вернул ненулевой код) остаётся sys.exit - там карта реально сломана.

    Возвращает dict для отчёта.
    """
    path = os.path.expanduser(cfg.get("sitemap_rebuild", "") or "")
    if not path or not os.path.exists(path):
        sys.stderr.write(
            "ВНИМАНИЕ: sitemap_rebuild.py не задан (поле \"sitemap_rebuild\" в "
            f"{cfg.get('_path', CONFIG_DEFAULT)} пустое или путь битый) - "
            "собираю ПЛОСКУЮ карту без image-слоя и без дат из реестра содержимого. "
            "Когда соберёшь свой сборщик карты, впиши его путь в конфиг - лишний "
            "слой вернётся.\n")
        xml = build_sitemap(cfg, pages)
        if dry:
            return {"owner": None, "fallback": True, "dry": True, "pages": len(pages)}
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as tf:
            tf.write(xml)
            tmp = tf.name
        upload(cfg, pw, tmp, "sitemap.xml")
        os.unlink(tmp)
        return {"owner": None, "fallback": True, "dry": False, "pages": len(pages)}
    cmd = [sys.executable, path] + (["--проверка"] if dry else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    tail = (r.stdout or "").strip().splitlines()[-12:]
    if r.returncode != 0:
        sys.exit("СТОП: владелец карты sitemap_rebuild.py вернул код "
                 f"{r.returncode} - карта НЕ пересобрана.\n"
                 + "\n".join(tail) + "\n" + (r.stderr or "").strip()[-600:])
    return {"owner": path, "dry": dry, "returncode": r.returncode, "tail": tail}


def upload(cfg, pw, local, remote):
    r = curl(["--user", f'{cfg["ftp_user"]}:{pw}', "-T", local,
              f'ftp://{cfg["ftp_host"]}{cfg["ftp_root"]}/{remote}'])
    if r.returncode != 0:
        sys.exit(f"Заливка {remote} упала: {r.stderr.decode()[:200]}")


def fetch(url):
    r = subprocess.run(["curl", "-s", "--max-time", "30", url], capture_output=True, timeout=60)
    return r.stdout


def http_code(url):
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "30", url],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def metrika_snippet(mid):
    return ("\n<!-- Yandex.Metrika counter -->\n"
            '<script type="text/javascript">\n'
            "   (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n"
            "   m[i].l=1*new Date();\n"
            "   for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}\n"
            "   k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})\n"
            f'   (window, document, "script", "https://mc.yandex.ru/metrika/tag.js?id={mid}", "ym");\n\n'
            f"   ym({mid}, 'init', {{ssr:true, webvisor:true, clickmap:true, ecommerce:\"dataLayer\", accurateTrackBounce:true, trackLinks:true}});\n"
            "</script>\n"
            f'<noscript><div><img src="https://mc.yandex.ru/watch/{mid}" style="position:absolute; left:-9999px;" alt="" /></div></noscript>\n'
            "<!-- /Yandex.Metrika counter -->\n").encode()


def heal_page(cfg, pw, url):
    """200 + canonical + metrika + JSON-LD; чего нет - вшить и перезалить."""
    code = http_code(url)
    if code != "200":
        return {"url": url, "status": code, "healed": False, "error": f"HTTP {code}"}
    raw = fetch(url)
    is_article = f'/{cfg["page_prefix"]}' in url
    # Страницы без JSON-LD бывают такими ОСОЗНАННО: у части корпуса нет реального
    # datePublished, часть - кодословные двери воронки. Навязанная Article-схема с
    # выдуманной датой = фейковый сигнал свежести, прямой запрет стратегии.
    # skip_schema в конфиге: слаги, которым схему не вшивать. "*" = не вшивать никому
    # сравнение по ТОЧНОМУ слагу, не по подстроке: guide-promt не должен
    # блокировать guide-promty-drevney-grecii
    skip_schema = cfg.get("skip_schema", [])
    url_slug = url.replace(cfg["domain"], "").strip("/").removesuffix(".html")
    schema_blocked = "*" in skip_schema or any(
        s.strip("/").removesuffix(".html") == url_slug
        for s in skip_schema if s != "*")
    need_canon = b'rel="canonical"' not in raw
    need_metrika = b"mc.yandex.ru/metrika" not in raw
    need_ld = b"application/ld+json" not in raw and is_article and not schema_blocked
    if not (need_canon or need_metrika or need_ld):
        return {"url": url, "status": "200", "healed": False, "ok": True}
    m = re.search(rb"</head>", raw, re.I) or re.search(rb"</body>", raw, re.I)
    if not m:
        return {"url": url, "status": "200", "healed": False, "error": "нет </head> и </body>"}
    block = b""
    if need_canon:
        block += f'  <link rel="canonical" href="{url}" />\n'.encode()
    if need_ld:
        t = re.search(rb"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
        d = re.search(rb'<meta\s+name="description"\s+content="(.*?)"', raw, re.S | re.I)
        title = htmlmod.unescape(t.group(1).decode("utf-8", "ignore").strip()) if t else ""
        desc = htmlmod.unescape(d.group(1).decode("utf-8", "ignore").strip()) if d else ""
        if title:
            ld = {"@context": "https://schema.org", "@type": "Article", "headline": title,
                  "description": desc, "url": url, "inLanguage": "ru",
                  "author": {"@type": "Person", "name": cfg["author_name"], "url": cfg["author_url"]},
                  "publisher": {"@type": "Person", "name": cfg["author_name"], "url": cfg["domain"]},
                  "mainEntityOfPage": {"@type": "WebPage", "@id": url}}
            block += b'  <script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).encode() + b"</script>\n"
    if need_metrika:
        block += metrika_snippet(cfg["metrika_id"])
    raw = raw[:m.start()] + block + raw[m.start():]
    rel = url.replace(cfg["domain"], "").lstrip("/")
    remote = (rel.rstrip("/") + "/index.html") if url.endswith("/") and rel else (rel or "index.html")
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
        tf.write(raw)
        tmp = tf.name
    upload(cfg, pw, tmp, remote)
    os.unlink(tmp)
    ok = http_code(url) == "200"
    return {"url": url, "status": "200", "healed": True,
            "added": [x for x, need in (("canonical", need_canon), ("metrika", need_metrika),
                                        ("json-ld", need_ld)) if need], "ok": ok}


def ensure_indexnow_key(cfg, pw):
    """Ключ из конфига; нет - сгенерить, залить <key>.txt в корень, дописать в конфиг."""
    key = cfg.get("indexnow_key", "")
    host = cfg["domain"].split("//")[1]
    if not key:
        key = secrets.token_hex(16)
        cfg["indexnow_key"] = key
        stored = {k: v for k, v in cfg.items() if not k.startswith("_")}
        json.dump(stored, open(cfg["_path"], "w"), ensure_ascii=False, indent=2)
    if http_code(f'{cfg["domain"]}/{key}.txt') != "200":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
            tf.write(key)
            tmp = tf.name
        upload(cfg, pw, tmp, f"{key}.txt")
        os.unlink(tmp)
    return key, host


def indexnow_ping(cfg, pw, urls):
    key, host = ensure_indexnow_key(cfg, pw)
    body = json.dumps({"host": host, "key": key,
                       "keyLocation": f'{cfg["domain"]}/{key}.txt', "urlList": urls})
    results = {}
    for ep in ("https://yandex.com/indexnow", "https://api.indexnow.org/indexnow"):
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "30",
                            "-X", "POST", "-H", "Content-Type: application/json; charset=utf-8",
                            "--data-binary", body, ep],
                           capture_output=True, text=True, timeout=60)
        results[ep] = r.stdout.strip()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", default=[], help="URL новой статьи (можно несколько)")
    ap.add_argument("--self-heal", action="store_true", help="синк без новых статей")
    ap.add_argument("--config", default=None, help="путь к конфигу (default ~/.config/seo-publish.json)")
    ap.add_argument("--dry-run", dest="dry", action="store_true",
                    help="вхолостую: карта делегируется владельцу в режиме --проверка, "
                         "страницы не лечатся, IndexNow не пингуется, на прод ничего не льётся")
    args = ap.parse_args()

    cfg = load_config(args.config)
    pw = ftp_pass(cfg)
    pages = parse_listing(cfg, ftp_listing(cfg, pw))
    live = fetch(f'{cfg["domain"]}/sitemap.xml').decode("utf-8", "ignore")
    live_urls = set(re.findall(r"<loc>(.*?)</loc>", live))
    added = sorted({f'{cfg["domain"]}{p}' for p, _, _ in pages} - live_urls)

    report = {"pages_total": len(pages), "sitemap_added": added,
              "healed": [], "indexnow": None, "dry_run": args.dry}

    # 🔴 ОДИН ВЛАДЕЛЕЦ КАРТЫ. Раньше здесь стояла прямая сборка build_sitemap() и
    # БЕЗУСЛОВНАЯ заливка при new != live - именно она затирала живой image-слой.
    # Теперь пересборка целиком у владельца, а отказ громкий (см. sitemap_owner).
    report["sitemap"] = sitemap_owner(cfg, pages, pw, dry=args.dry)

    to_ping = sorted(set(args.url) | set(added))

    # --self-heal: пройти ВЕСЬ корпус, а не только новые страницы из диффа sitemap.
    # Лечим молча (canonical/метрика; schema - с оглядкой на skip_schema), а в IndexNow
    # шлём только то, что реально изменилось: пинговать 200 нетронутых страниц незачем
    if args.dry:
        # холостой прогон: карту уже посмотрел владелец в режиме --проверка, дальше
        # идут только пишущие шаги (heal перезаливает страницы, IndexNow дёргает
        # поисковики) - в холостом прогоне им делать нечего
        report["would_heal"] = to_ping
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return

    if args.self_heal:
        all_urls = sorted({f'{cfg["domain"]}{p}' for p, _, _ in pages})
        healed_now = []
        for u in all_urls:
            if u in to_ping:
                continue
            res = heal_page(cfg, pw, u)
            report["healed"].append(res)
            if res.get("healed"):
                healed_now.append(u)
        report["self_heal_scanned"] = len(all_urls)
        to_ping = sorted(set(to_ping) | set(healed_now))

    for u in sorted(set(args.url) | set(added)):
        report["healed"].append(heal_page(cfg, pw, u))
    if to_ping:
        report["indexnow"] = indexnow_ping(cfg, pw, to_ping)
        report["pinged"] = to_ping

    print(json.dumps(report, ensure_ascii=False, indent=1))
    bad = [h for h in report["healed"] if h.get("error")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()