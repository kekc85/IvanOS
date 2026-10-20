# Установка движка автопостинга на Windows.
# Ровно 7 шагов, те же самые и в том же порядке, что в setup.sh для macOS и Linux.
# Запуск:  powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot

function Step($n, $title) { Write-Host ""; Write-Host ("ШАГ {0}/7 {1}" -f $n, $title) }
function Ok($text)        { Write-Host ("  готово: {0}" -f $text) }
function Warn($text)      { Write-Host ("  внимание: {0}" -f $text) }

Step 1 "проверяю питон"
$py = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $found) {
        & $candidate -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
    }
}
if ($null -eq $py) {
    Warn "питон 3.9 или новее не найден. Поставь его с python.org и запусти setup.ps1 заново"
    exit 1
}
Ok (& $py --version 2>&1)

Step 2 "ставлю зависимости"
& $py -c "import httpx" 2>$null
if ($LASTEXITCODE -eq 0) {
    Ok "httpx уже стоит"
} else {
    & $py -m pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) { & $py -m pip install --quiet --break-system-packages -r requirements.txt }
    & $py -c "import httpx" 2>$null
    if ($LASTEXITCODE -eq 0) { Ok "httpx поставлен" } else { Warn "pip не смог поставить httpx, поставь вручную" }
}

Step 3 "готовлю файл ключей .env"
if (Test-Path ".env") {
    Ok ".env уже есть, не трогаю"
} else {
    Copy-Item "env.example" ".env"
    Ok "создан .env из образца. Открой его и впиши свои ключи"
}

Step 4 "готовлю рабочий дом"
$homeDir = & $py -c "import os,pathlib;v=os.environ.get('AUTOPOST_HOME','').strip();p=pathlib.Path(v).expanduser() if v else pathlib.Path.home()/'.autopost';p.mkdir(parents=True,exist_ok=True);print(p)"
Ok ("очередь и лог будут лежать в {0} (вне папки движка)" -f $homeDir)

Step 5 "проверяю движок тестами"
# имя отчёта уникальное, как в setup.sh: два прогона рядом не перетирают файл друг друга
$report = Join-Path ([System.IO.Path]::GetTempPath()) ("autopost-tests-" + [System.IO.Path]::GetRandomFileName().Substring(0,6) + ".txt")
# -p no:cacheprovider: проверки не оставляют кэш прогона в папке движка. То же правило
# лежит в pytest.ini рядом - там оно работает и для запуска руками, и из редактора.
# Здесь флаг стоит вторым замком, ровно как в setup.sh
& $py -m pytest tests -q -p no:cacheprovider 2>&1 | Tee-Object -FilePath $report | Out-Host
if ($LASTEXITCODE -eq 0) {
    Ok "тесты прошли"
    Ok ("полный отчёт: {0}" -f $report)
} else {
    & $py -c "import pytest" 2>$null
    if ($LASTEXITCODE -eq 0) { Warn ("тесты не прошли, смотри {0}" -f $report) }
    else { Warn "pytest не установлен, шаг пропущен (на работу движка не влияет)" }
}

Step 6 "спрашиваю доктора"
& $py cli.py doctor
if ($LASTEXITCODE -ne 0) { Warn "доктор завершился с ошибкой" }

Step 7 "расписание"
Write-Host "  шаблоны автозапуска лежат в raspisanie/"
Write-Host "    твоя система: Windows, бери raspisanie/windows-task.ps1 (Планировщик заданий)"
Write-Host "    поставить расписание можно позже, движок работает и по ручному запуску"

Write-Host ""
Write-Host ("УСТАНОВКА ЗАВЕРШЕНА. Дальше: впиши ключи в .env, потом {0} cli.py doctor" -f $py)
