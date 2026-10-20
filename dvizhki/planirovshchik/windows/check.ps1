# Живая самопроверка планировщика на Windows. Зеркало mac/check.sh, пункт в пункт.
#
# Проверяет ровно четыре вещи и по каждой отвечает честно:
#   1. сервер отвечает или нет
#   2. данные на месте и читаются
#   3. расписание стоит
#   4. ритуалы реально запускаются (прогон в песочнице, рабочие данные не трогаем)
#
# При проблеме печатает, что именно чинить. Выход 0 - всё дышит, 1 - есть что чинить.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File windows\check.ps1

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$PlannerHome = if ($env:PLANNER_HOME) { $env:PLANNER_HOME } else { Join-Path $env:USERPROFILE 'planner' }
$PlannerData = if ($env:PLANNER_DATA) { $env:PLANNER_DATA } else { Join-Path $env:USERPROFILE 'planner-data' }
$PlannerPort = if ($env:PLANNER_PORT) { $env:PLANNER_PORT } else { '8791' }
$TaskFolder  = 'Planner'
$Url         = "http://localhost:$PlannerPort"
$script:Problems = 0

function Ok   ($m) { Write-Host "  v $m" -ForegroundColor Green }
function Bad  ($m) { Write-Host "  x $m" -ForegroundColor Red; $script:Problems++ }
function Fix  ($m) { Write-Host "      -> чинить так: $m" -ForegroundColor Yellow }
function Info ($m) { Write-Host "    $m" }
function Step ($m) { Write-Host ""; Write-Host $m -ForegroundColor White }

Write-Host ""
Write-Host "Проверка планировщика" -ForegroundColor White
Info "движок: $PlannerHome"
Info "данные: $PlannerData"
Info "адрес:  $Url"

$Py = $null
foreach ($cand in @('py', 'python3', 'python')) {
    $exe = (Get-Command $cand -ErrorAction SilentlyContinue)
    if (-not $exe) { continue }
    $a = if ($cand -eq 'py') { @('-3', '-c', 'import sys;print(sys.executable)') } else { @('-c', 'import sys;print(sys.executable)') }
    $out = & $exe.Source @a 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) { $Py = ($out | Select-Object -Last 1).Trim(); break }
}

# ---------------------------------------------------------------- 1. сервер
Step "1/4 Сервер"

if (-not $Py) {
    Bad "Python 3 не найден"
    Fix "поставь Python с python.org (галочка «Add python.exe to PATH») и запусти windows\install.ps1 заново"
} else {
    $v = & $Py -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>$null
    Ok "Python $v : $Py"
}

if (-not (Test-Path (Join-Path $PlannerHome 'server.py'))) {
    Bad "движка нет: $PlannerHome\server.py не найден"
    Fix "powershell -ExecutionPolicy Bypass -File windows\install.ps1"
} else {
    Ok "движок на месте"
}

$cfg = $null
# Пульс снимается с /api/where. Прежде стоял /api/config - такого эндпоинта у движка нет,
# живой сервер отвечал 404, и самопроверка на рабочем ките звала переустановку.
# Настройки модулей лежат файлом в папке данных, по HTTP их не отдают.
try { $cfg = Invoke-WebRequest -Uri "$Url/api/where" -UseBasicParsing -TimeoutSec 3 } catch {}
if ($cfg) {
    Ok "сервер отвечает на $Url"
    $cfgText = ""
    $cfgFile = Join-Path $PlannerData "config.json"
    if (Test-Path $cfgFile) { $cfgText = Get-Content -Raw -Encoding UTF8 $cfgFile }
    if ($cfgText -match 'eveningCheckin') {
        if ($cfgText -match '"enabled"\s*:\s*false') {
            Info "вечерний чек-ин выключен в config.json - так и задумано, если ты его выключал"
        } else { Ok "вечерний чек-ин включён" }
    }
    try {
        $page = Invoke-WebRequest -Uri "$Url/" -UseBasicParsing -TimeoutSec 3
        if ($page.Content -match 'tab-week\.js') { Ok "страница интерфейса отдаётся" }
        else { Bad "сервер жив, но страница интерфейса не отдалась"; Fix "проверь, что папка $PlannerHome\static не пустая, потом переустанови" }
    } catch {
        Bad "сервер жив, но страница интерфейса не отдалась"
        Fix "проверь, что папка $PlannerHome\static не пустая, потом переустанови"
    }
} else {
    Bad "сервер не отвечает на $Url"
    $busy = $null
    try { $busy = Get-NetTCPConnection -LocalPort ([int]$PlannerPort) -State Listen -ErrorAction SilentlyContinue } catch {}
    if ($busy) {
        Fix "порт $PlannerPort занят кем-то другим. Переустанови на другом порту: `$env:PLANNER_PORT='8792'; powershell -ExecutionPolicy Bypass -File windows\install.ps1"
    } else {
        Fix "запусти сервер руками: $PlannerHome\jobs\server.cmd ; ошибку смотри в $PlannerData\logs\server.log"
    }
}

# ---------------------------------------------------------------- 2. данные
Step "2/4 Данные"

if (-not (Test-Path $PlannerData)) {
    Bad "папки данных нет: $PlannerData"
    Fix "powershell -ExecutionPolicy Bypass -File windows\install.ps1"
} else {
    Ok "папка данных на месте"
    foreach ($f in @('sprint.json', 'profile.json', 'goals-cycle.json', 'tracker.json')) {
        $p = Join-Path $PlannerData $f
        if (-not (Test-Path $p)) {
            Bad "нет файла $f"
            Fix "переустанови: существующие файлы установщик не тронет, добавит только недостающие"
            continue
        }
        $parsed = $true
        try { Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null } catch { $parsed = $false }
        if ($parsed) { Ok "$f читается" }
        else {
            Bad "$f не читается как JSON"
            $last = Get-ChildItem (Join-Path $PlannerData 'backups') -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($last) { Fix "верни последний снимок: Copy-Item `"$($last.FullName)`" `"$p`" -Force" }
            else { Fix "снимков нет. Удали битый файл и переустанови - положится чистый шаблон" }
        }
    }
    $snaps = (Get-ChildItem (Join-Path $PlannerData 'backups') -ErrorAction SilentlyContinue | Measure-Object).Count
    Info "снимков в backups: $snaps"
}

# ---------------------------------------------------------------- 3. расписание
Step "3/4 Расписание"

foreach ($name in @('server', 'daily-open', 'daily-close', 'wam', 'watchdog')) {
    $taskName = "\$TaskFolder\$name"
    $q = schtasks /Query /TN $taskName /FO LIST 2>$null
    if ($LASTEXITCODE -ne 0) {
        Bad "$name : задачи нет в планировщике задач"
        Fix "powershell -ExecutionPolicy Bypass -File windows\install.ps1"
        continue
    }
    $line = ($q | Select-String -Pattern 'Disabled|Отключено')
    if ($line) {
        Bad "$name : задача есть, но выключена"
        Fix "schtasks /Change /TN $taskName /ENABLE"
    } else {
        Ok "$name : стоит и включена"
    }
    $jobCmd = Join-Path $PlannerHome "jobs\$name.cmd"
    if (-not (Test-Path $jobCmd)) {
        Bad "$name : нет файла запуска $jobCmd"
        Fix "powershell -ExecutionPolicy Bypass -File windows\install.ps1"
    }
}

# ---------------------------------------------------------------- 4. ритуалы
Step "4/4 Ритуалы"

if (-not $Py -or -not (Test-Path (Join-Path $PlannerHome 'rituals'))) {
    Bad "ритуалов нет: $PlannerHome\rituals"
    Fix "powershell -ExecutionPolicy Bypass -File windows\install.ps1"
} else {
    $sandbox = Join-Path ([System.IO.Path]::GetTempPath()) ("planner-check-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Force -Path (Join-Path $sandbox 'planner-data') | Out-Null
    foreach ($f in @('sprint.json', 'profile.json', 'goals-cycle.json', 'tracker.json')) {
        $p = Join-Path $PlannerData $f
        if (Test-Path $p) { Copy-Item $p (Join-Path $sandbox "planner-data\$f") -Force -ErrorAction SilentlyContinue }
    }
    # PLANNER_TEST_ROOT уводит ВСЕ пути ритуала внутрь песочницы, поэтому проверка
    # не может испортить твой реальный план и не покажет ни одного окна.
    $env:PLANNER_TEST_ROOT = $sandbox
    $env:PLANNER_NO_NOTIFY = '1'
    foreach ($r in @('daily_open', 'daily_close', 'wam', 'watchdog')) {
        $out = & $Py (Join-Path $PlannerHome "rituals\$r.py") 2>&1
        $code = $LASTEXITCODE
        $text = ($out | Out-String)
        # watchdog осознанно выходит 1, когда видит проблему - это не поломка ритуала
        if ($text -match 'УПАЛ|Traceback') {
            Bad "$r : падает"
            ($text -split "`n" | Select-Object -Last 5) | ForEach-Object { Write-Host "        $_" }
            Fix "покажи эти строки тому, кто выдал кит: ритуал не должен падать"
        } elseif ($code -ne 0 -and $r -ne 'watchdog') {
            Bad "$r : вышел с кодом $code"
            Fix "запусти руками и посмотри вывод: & `"$Py`" `"$PlannerHome\rituals\$r.py`""
        } else {
            Ok "$r : запускается"
        }
    }
    # это переменные окружения самого процесса проверки, а не твои файлы:
    # снимаем их, чтобы песочный режим не утёк в следующую команду
    Remove-Item Env:\PLANNER_TEST_ROOT -ErrorAction SilentlyContinue
    Remove-Item Env:\PLANNER_NO_NOTIFY -ErrorAction SilentlyContinue
    # 🔴 Песочница НЕ стирается: проверка ничего не удаляет на твоей машине.
    # Папка лежит во временном каталоге Windows, система убирает его сама
    Write-Host "        песочница проверки осталась лежать: $sandbox"
}

# ---------------------------------------------------------------- итог
Write-Host ""
if ($script:Problems -eq 0) {
    Write-Host "Всё дышит. Планировщик открывается на $Url" -ForegroundColor Green
    Write-Host ""
    exit 0
}
Write-Host "Нашлось проблем: $($script:Problems). Что чинить - написано выше стрелкой ->" -ForegroundColor Red
Write-Host ""
exit 1
