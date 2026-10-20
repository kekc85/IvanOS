"""Слой публичного адреса медиа на подменённом транспорте: ни git, ни scp
по-настоящему не вызываются.

Про адрес `user@web-1.example` в примерах: имя сервера намеренно взято с дефисом.
Скан на личное ищет в тексте телеграм-хэндлы по образцу «собака плюс буквы», и
короткое имя сервера без дефиса он честно принимает за хэндл. Это ложная тревога, но чинить
её ослаблением скана нельзя, поэтому чинится сам пример.

Зачем набор нужен. Instagram не умеет принимать файл с твоего диска: он КАЧАЕТ
картинку сам по ссылке. Значит слой, который эту ссылку делает, стоит на пути
каждой публикации с картинкой, и молчаливая ошибка здесь стоит поста. Живьём
путь `git` прожит отдельно (файл уехал в публичную раздачу и площадка скачала
его сама), а тут проверяется то, что живой прогон показать не может: порядок
команд, сборка адреса, поведение на отказе и понятность каждой ошибки

Подмена: `subprocess.run` и `shutil.which` внутри модуля. Записываем каждый
вызов и отвечаем тем, что задал тест. Настоящих процессов ноль
"""

from __future__ import annotations

import subprocess

import pytest

from autopost import media


class FakeRun:
    """Записывает команды вместо запуска. Ответ задаёт сам тест"""

    def __init__(self, answers=None):
        self.calls: list[list[str]] = []
        self.answers = answers or {}

    def __call__(self, args, **kwargs):
        args = [str(part) for part in args]
        self.calls.append(args)
        for needle, reply in self.answers.items():
            if needle in _key(args):
                code, out, err = reply
                return subprocess.CompletedProcess(args, code, out, err)
        return subprocess.CompletedProcess(args, 0, "", "")

    def sub(self, needle: str) -> list[list[str]]:
        return [call for call in self.calls if needle in _key(call)]


def _key(args: list[str]) -> str:
    """Что именно запущено, без путей.

    Путь временной папки в прогоне содержит имя теста, а в именах тестов
    встречаются слова `commit` и `push`: сверять команду по всей строке -
    значит ловить собственное имя теста вместо команды
    """
    if args[:1] == ["git"]:
        return " ".join(args[3:])
    return args[0] if args else ""


@pytest.fixture
def kartinka(tmp_path):
    picture = tmp_path / "kartinka.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n proba")
    return picture


@pytest.fixture
def repo(tmp_path):
    place = tmp_path / "publichnyy-repo"
    place.mkdir()
    return place


@pytest.fixture
def podmena(monkeypatch):
    def install(answers=None, tools=("git", "scp")):
        runner = FakeRun(answers)
        monkeypatch.setattr(media.subprocess, "run", runner)
        monkeypatch.setattr(media.shutil, "which", lambda name: ("/usr/bin/%s" % name) if name in tools else None)
        return runner

    return install


# ── путь git ─────────────────────────────────────────────────────────────
def test_git_put_commits_and_returns_public_address(monkeypatch, podmena, repo, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/main/")
    runner = podmena({"status --porcelain": (0, " M media/kartinka.png\n", "")})

    address = media.put(str(kartinka))

    assert address == "https://raw.example/user/repo/main/media/kartinka.png"
    assert (repo / "media" / "kartinka.png").read_bytes() == kartinka.read_bytes(), "файл обязан лечь в репозиторий"
    poryadok = [call[3] for call in runner.calls]
    assert poryadok == ["add", "status", "commit", "push"], "сначала add, потом коммит, и только потом отправка"
    assert runner.sub("push")[0][-2:] == ["origin", "main"], "ветка по умолчанию main"


def test_git_put_can_live_in_repo_root(monkeypatch, podmena, repo, kartinka):
    """Пустой MEDIA_GIT_SUBDIR = корень репозитория.

    Это не украшение: часть бесплатных раздач каталоги внутри репозитория
    отвергает совсем, и без корня путь git там не работает физически
    """
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_GIT_SUBDIR", "")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/gist/raw")
    runner = podmena({"status --porcelain": (0, " M kartinka.png\n", "")})

    address = media.put(str(kartinka))

    assert address == "https://raw.example/user/gist/raw/kartinka.png"
    assert (repo / "kartinka.png").exists(), "файл лежит в корне, подкаталога нет"
    assert not (repo / "media").exists()
    assert runner.sub("add")[0][-1] == "kartinka.png", "в git уходит путь без подкаталога"


def test_git_put_skips_commit_when_file_did_not_change(monkeypatch, podmena, repo, kartinka):
    """Повторная выкладка того же файла не плодит пустые коммиты"""
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/main")
    runner = podmena({"status --porcelain": (0, "", "")})

    address = media.put(str(kartinka))

    assert address.endswith("/media/kartinka.png")
    assert runner.sub("commit") == [], "коммитить нечего, а адрес всё равно возвращается"


def test_git_put_uses_branch_from_settings(monkeypatch, podmena, repo, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_GIT_BRANCH", "master")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/master")
    runner = podmena({"status --porcelain": (0, " M media/kartinka.png\n", "")})

    media.put(str(kartinka))

    assert runner.sub("push")[0][-2:] == ["origin", "master"]


def test_git_put_names_missing_settings(monkeypatch, podmena, kartinka, repo):
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.delenv("MEDIA_GIT_DIR", raising=False)
    monkeypatch.delenv("MEDIA_PUBLIC_BASE", raising=False)
    podmena()

    with pytest.raises(media.MediaError) as bez_papki:
        media.put(str(kartinka))
    assert "MEDIA_GIT_DIR" in str(bez_papki.value)

    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    with pytest.raises(media.MediaError) as bez_adresa:
        media.put(str(kartinka))
    assert "MEDIA_PUBLIC_BASE" in str(bez_adresa.value)


def test_git_put_repeats_push_failure_verbatim(monkeypatch, podmena, repo, kartinka):
    """Отказ отправки виден дословно: ученик читает ответ хостинга, а не «что-то пошло не так»"""
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/main")
    podmena(
        {
            "status --porcelain": (0, " M media/kartinka.png\n", ""),
            "push": (128, "", "remote: Permission to user/repo.git denied"),
        }
    )

    with pytest.raises(media.MediaError) as caught:
        media.put(str(kartinka))
    assert "Permission to user/repo.git denied" in str(caught.value)


def test_git_put_needs_git_installed(monkeypatch, podmena, repo, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/main")
    runner = podmena(tools=())

    with pytest.raises(media.MediaError) as caught:
        media.put(str(kartinka))
    assert "git не установлен" in str(caught.value)
    assert runner.calls == [], "без git не делаем ни одного вызова"


# ── путь ssh ─────────────────────────────────────────────────────────────
def test_ssh_put_copies_by_scp_and_returns_address(monkeypatch, podmena, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "ssh")
    monkeypatch.setenv("MEDIA_SSH_TARGET", "user@web-1.example:/var/www/media/")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://sait.example/media")
    runner = podmena()

    address = media.put(str(kartinka))

    assert address == "https://sait.example/media/kartinka.png"
    call = runner.sub("scp")[0]
    assert call[0] == "scp"
    assert call[-2] == str(kartinka)
    assert call[-1] == "user@web-1.example:/var/www/media/kartinka.png", "лишнего слэша в адресе назначения нет"


def test_ssh_put_names_missing_settings(monkeypatch, podmena, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "ssh")
    monkeypatch.delenv("MEDIA_SSH_TARGET", raising=False)
    monkeypatch.delenv("MEDIA_PUBLIC_BASE", raising=False)
    podmena()

    with pytest.raises(media.MediaError) as bez_celi:
        media.put(str(kartinka))
    assert "MEDIA_SSH_TARGET" in str(bez_celi.value)

    monkeypatch.setenv("MEDIA_SSH_TARGET", "user@web-1.example:/var/www/media")
    with pytest.raises(media.MediaError) as bez_adresa:
        media.put(str(kartinka))
    assert "MEDIA_PUBLIC_BASE" in str(bez_adresa.value)


def test_ssh_put_repeats_scp_failure_verbatim(monkeypatch, podmena, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "ssh")
    monkeypatch.setenv("MEDIA_SSH_TARGET", "user@web-1.example:/var/www/media")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://sait.example/media")
    podmena({"scp": (1, "", "Permission denied (publickey)")})

    with pytest.raises(media.MediaError) as caught:
        media.put(str(kartinka))
    assert "Permission denied (publickey)" in str(caught.value)


def test_ssh_put_needs_scp_installed(monkeypatch, podmena, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "ssh")
    monkeypatch.setenv("MEDIA_SSH_TARGET", "user@web-1.example:/var/www/media")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://sait.example/media")
    runner = podmena(tools=("git",))

    with pytest.raises(media.MediaError) as caught:
        media.put(str(kartinka))
    assert "scp не установлен" in str(caught.value)
    assert runner.calls == []


# ── общие правила слоя ───────────────────────────────────────────────────
def test_public_link_passes_through_untouched(monkeypatch, podmena):
    monkeypatch.setenv("MEDIA_MODE", "git")
    runner = podmena()
    assert media.put("https://sait.example/uzhe/v/vebe.jpg") == "https://sait.example/uzhe/v/vebe.jpg"
    assert runner.calls == [], "готовый адрес никуда не выкладывается заново"


def test_ready_mode_refuses_local_file_with_instruction(monkeypatch, podmena, kartinka):
    monkeypatch.setenv("MEDIA_MODE", "ready")
    podmena()
    with pytest.raises(media.MediaError) as caught:
        media.put(str(kartinka))
    text = str(caught.value)
    assert "MEDIA_MODE=git" in text and "MEDIA_MODE=ssh" in text, "ошибка обязана называть выход, а не только беду"


def test_missing_file_is_named_before_any_call(monkeypatch, podmena):
    monkeypatch.setenv("MEDIA_MODE", "git")
    runner = podmena()
    with pytest.raises(media.MediaError) as caught:
        media.put("/net/takogo/faila.png")
    assert "нет на диске" in str(caught.value)
    assert runner.calls == []


def test_describe_names_current_path(monkeypatch, repo):
    monkeypatch.setenv("MEDIA_MODE", "git")
    monkeypatch.setenv("MEDIA_GIT_DIR", str(repo))
    monkeypatch.setenv("MEDIA_PUBLIC_BASE", "https://raw.example/user/repo/main")
    assert "git:" in media.describe() and str(repo) in media.describe()
