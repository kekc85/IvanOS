# Установщик планировщика для Windows. Зеркало mac/install.sh, шаг в шаг.
#
# Что делает по шагам:
#   1. проверяет Python 3
#   2. разворачивает движок в %USERPROFILE%\planner
#   3. создаёт %USERPROFILE%\planner-data из шаблонов, НЕ трогая то, что уже есть
#   4. ставит автозапуск сервера
#   5. ставит расписание четырёх ритуалов
#   6. открывает браузер
#   7. рассказывает человеческим языком, что дальше
#
# Права администратора не нужны. Повторный запуск безопасен: службы
# переставляются поверх, данные не трогаются. Перед перезаписью делается бэкап.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File windows\install.ps1
#
# Настроить можно переменными окружения (по умолчанию не нужно):
#   PLANNER_HOME, PLANNER_DATA, PLANNER_PORT

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$KitDir      = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PlannerHome = if ($env:PLANNER_HOME) { $env:PLANNER_HOME } else { Join-Path $env:USERPROFILE 'planner' }
$PlannerData = if ($env:PLANNER_DATA) { $env:PLANNER_DATA } else { Join-Path $env:USERPROFILE 'planner-data' }
$PlannerPort = if ($env:PLANNER_PORT) { $env:PLANNER_PORT } else { '8791' }
$TaskFolder  = 'Planner'
$Stamp       = Get-Date -Format 'yyyyMMdd-HHmmss'

function Ok   ($m) { Write-Host "  v $m" -ForegroundColor Green }
function Info ($m) { Write-Host "    $m" }
function Warn ($m) { Write-Host "  ! $m" -ForegroundColor Yellow }
function Step ($m) { Write-Host ""; Write-Host $m -ForegroundColor White }
function Die  ($m) { Write-Host ""; Write-Host "  x $m" -ForegroundColor Red; Write-Host ""; exit 1 }

Write-Host ""
Write-Host "Установка планировщика" -ForegroundColor White
Info "движок:  $PlannerHome"
Info "данные:  $PlannerData"
Info "порт:    $PlannerPort"

# ---------------------------------------------------------------- 1. Python 3
Step "1/7 Проверяю Python 3"

$Py = $null
foreach ($cand in @('py', 'python3', 'python')) {
    $exe = (Get-Command $cand -ErrorAction SilentlyContinue)
    if (-not $exe) { continue }
    $args = if ($cand -eq 'py') { @('-3', '-c', 'import sys;print(sys.executable)') } else { @('-c', 'import sys;print(sys.executable)') }
    $out = & $exe.Source @args 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) { $Py = ($out | Select-Object -Last 1).Trim(); break }
}
if (-not $Py) {
    Die "Python 3 не найден. Поставь его с python.org (кнопка «Download Python») и обязательно отметь галочку «Add python.exe to PATH», потом запусти установщик снова"
}

$PyVer = & $Py -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
$okVer = & $Py -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>$null; $verCode = $LASTEXITCODE
if ($verCode -ne 0) { Die "Нужен Python 3.8 или новее, а стоит $PyVer. Обнови его с python.org" }
Ok "Python $PyVer : $Py"

# pythonw запускает сервер без чёрного окна консоли. Нет его - обойдёмся python.
$Pyw = Join-Path (Split-Path -Parent $Py) 'pythonw.exe'
if (-not (Test-Path $Pyw)) { $Pyw = $Py }

# ---------------------------------------------------------------- 2. движок
Step "2/7 Разворачиваю движок"

$EngineSrc = Join-Path $KitDir 'engine'
if (-not (Test-Path $EngineSrc)) { Die "В ките нет папки engine. Распакуй архив целиком и запускай установщик из него" }

if (Test-Path $PlannerHome) {
    $backup = "$PlannerHome.backup-$Stamp"
    try { Copy-Item $PlannerHome $backup -Recurse -Force -ErrorAction Stop; Ok "старый движок сохранён: $backup" }
    catch { Warn "не получилось сделать бэкап старого движка, продолжаю" }
}

New-Item -ItemType Directory -Force -Path $PlannerHome | Out-Null
Copy-Item (Join-Path $EngineSrc '*') $PlannerHome -Recurse -Force
# Установщик НИЧЕГО не удаляет на твоей машине. Кэш байткода из кита питон
# подхватывать не должен, поэтому папка ПЕРЕИМЕНОВЫВАЕТСЯ рядом, а не стирается
Get-ChildItem $PlannerHome -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Rename-Item $_.FullName ($_.Name + ".staroe-$Stamp") -ErrorAction SilentlyContinue }
Ok "движок на месте: $PlannerHome"

& $Py -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" (Join-Path $PlannerHome 'server.py') 2>$null
if ($LASTEXITCODE -ne 0) { Die "server.py не разбирается этим Python. Скорее всего кит распаковался наполовину" }
Ok "server.py читается без ошибок"

# ---------------------------------------------------------------- 3. данные
Step "3/7 Готовлю папку данных"

$seed = & $Py (Join-Path $PlannerHome 'tools\seed_data.py') --templates (Join-Path $KitDir 'data-template') --target $PlannerData 2>&1
$seedCode = $LASTEXITCODE
$seed | ForEach-Object { Info $_ }
if ($seedCode -ne 0) { Die "не получилось разложить шаблоны в $PlannerData" }
Ok "данные в $PlannerData (существующие файлы не тронуты)"

# ---------------------------------------------------------------- 4-5. службы
# Планировщик задач Windows не умеет передавать переменные окружения напрямую,
# поэтому на каждую работу кладём крошечный .cmd: он выставляет переменные и
# зовёт python. Побочная польза - любую работу можно запустить руками двойным
# кликом по её .cmd и увидеть, что она печатает.
$JobsDir = Join-Path $PlannerHome 'jobs'
New-Item -ItemType Directory -Force -Path $JobsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PlannerData 'logs') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PlannerData 'backups') | Out-Null

function Write-Job {
    param([string]$Name, [string]$Script, [switch]$Background)
    $jobPath = Join-Path $JobsDir "$Name.cmd"
    $exe = if ($Background) { $Pyw } else { $Py }
    $target = Join-Path $PlannerHome $Script
    $log = Join-Path $PlannerData "logs\$Name.log"
    $body = @(
        '@echo off',
        "set ""PLANNER_DATA=$PlannerData""",
        "set ""PLANNER_PORT=$PlannerPort""",
        $(if ($Background) { "start """" ""$exe"" ""$target""" } else { """$exe"" ""$target"" >> ""$log"" 2>&1" })
    ) -join "`r`n"
    Set-Content -Path $jobPath -Value $body -Encoding ASCII
    return $jobPath
}

function Set-Job {
    param([string]$Name, [string]$JobPath, [string[]]$ScheduleArgs)
    $taskName = "\$TaskFolder\$Name"
    $existing = schtasks /Query /TN $taskName 2>$null
    if ($LASTEXITCODE -eq 0) {
        $xml = schtasks /Query /TN $taskName /XML 2>$null
        if ($xml) { Set-Content -Path (Join-Path $PlannerData "backups\task-$Name.xml.backup-$Stamp") -Value $xml -Encoding UTF8 }
    }
    $out = schtasks /Create /F /TN $taskName /TR "`"$JobPath`"" @ScheduleArgs 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "$taskName" }
    else {
        Warn "$taskName не создалась планировщиком задач"
        Info ($out -join ' ')
        Info "запустить руками можно так: $JobPath"
    }
}

Step "4/7 Ставлю автозапуск сервера"
$serverJob = Write-Job -Name 'server' -Script 'server.py' -Background
Set-Job -Name 'server' -JobPath $serverJob -ScheduleArgs @('/SC', 'ONLOGON')
# запускаем прямо сейчас, не дожидаясь следующего входа в систему
Start-Process -FilePath $serverJob -WindowStyle Hidden | Out-Null

Step "5/7 Ставлю расписание ритуалов"
$openJob  = Write-Job -Name 'daily-open'  -Script 'rituals\daily_open.py'
$closeJob = Write-Job -Name 'daily-close' -Script 'rituals\daily_close.py'
$wamJob   = Write-Job -Name 'wam'         -Script 'rituals\wam.py'
$dogJob   = Write-Job -Name 'watchdog'    -Script 'rituals\watchdog.py'
Set-Job -Name 'daily-open'  -JobPath $openJob  -ScheduleArgs @('/SC', 'DAILY', '/ST', '09:00')
Set-Job -Name 'daily-close' -JobPath $closeJob -ScheduleArgs @('/SC', 'DAILY', '/ST', '21:30')
Set-Job -Name 'wam'         -JobPath $wamJob   -ScheduleArgs @('/SC', 'WEEKLY', '/D', 'SAT', '/ST', '20:00')
Set-Job -Name 'watchdog'    -JobPath $dogJob   -ScheduleArgs @('/SC', 'DAILY', '/ST', '13:00')
Info "утро 09:00 сводка · вечер 21:30 закрытие дня · суббота 20:00 разбор недели · день 13:00 сторож"

# ---------------------------------------------------------------- 6. браузер
Step "6/7 Поднимаю интерфейс"

$Url = "http://localhost:$PlannerPort"
$alive = $false
foreach ($i in 1..10) {
    try {
        Invoke-WebRequest -Uri "$Url/api/where" -UseBasicParsing -TimeoutSec 2 | Out-Null  # /api/config у движка нет, он отвечал 404
        $alive = $true; break
    } catch { Start-Sleep -Seconds 1 }
}

if ($alive) {
    Ok "сервер отвечает на $Url"
    try { Start-Process $Url | Out-Null; Info "браузер открыт" } catch { Info "открой в браузере: $Url" }
} else {
    Warn "сервер пока не ответил. Загляни в $PlannerData\logs\server.log и запусти windows\check.ps1"
}

# ---------------------------------------------------------------- 7. что дальше
Step "7/7 Готово. Что делать дальше"

Write-Host @"

  Планировщик живёт по адресу $Url - открывай его как обычный сайт,
  можно положить в закладки. Интернет ему не нужен, всё работает офлайн.

  Первым делом:
    1. Зайди во вкладку «Настройки» и выставь свой режим дня. Вся сетка
       считается от него, пока цифры не твои - день на экране чужой
    2. Открой «Как пользоваться» в шапке, это пять минут чтения
    3. Замени примеры своими задачами и целями, примеры для того и лежат

  Дальше движок работает сам: утром собирает сводку дня, вечером закрывает
  день и переносит несделанное, в субботу вечером считает разбор недели,
  днём сторож проверяет, что система жива, а не крутится вхолостую.

  Твои данные:   $PlannerData
  Проверка:      powershell -ExecutionPolicy Bypass -File "$KitDir\windows\check.ps1"
  Снять службы:  schtasks /Delete /TN \$TaskFolder\server /F (и так же остальные)

"@
