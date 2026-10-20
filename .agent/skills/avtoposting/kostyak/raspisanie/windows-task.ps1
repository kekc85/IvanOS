# Расписание для Windows через Планировщик заданий.
# Что сделать:
#   1) подставь два пропуска ниже
#   2) запусти:  powershell -NoProfile -ExecutionPolicy Bypass -File windows-task.ps1
#   3) проверь:  Get-ScheduledTask -TaskName "Автопостинг"
# Выключить:     Unregister-ScheduledTask -TaskName "Автопостинг" -Confirm:$false

$python = "{{ПУТЬ_К_ПИТОНУ}}"
$engine = "{{ПУТЬ_К_ДВИЖКУ}}"
$taskName = "Автопостинг"

if (-not (Test-Path $python)) { Write-Host "не вижу питон по пути $python"; exit 1 }
if (-not (Test-Path (Join-Path $engine "cli.py"))) { Write-Host "не вижу cli.py в $engine"; exit 1 }

$action = New-ScheduledTaskAction -Execute $python `
    -Argument ("`"{0}\cli.py`" run" -f $engine) -WorkingDirectory $engine

# просыпаться раз в минуту в течение суток и так каждый день
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Движок автопостинга: отправить всё, чему пришло время" -Force

Write-Host "расписание поставлено. Проверь: Get-ScheduledTask -TaskName `"$taskName`""
