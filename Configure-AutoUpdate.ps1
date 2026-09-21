param(
    [Parameter(Mandatory=$true)][ValidateSet('Enable','Disable','Status')][string]$Action,
    [Parameter(Mandatory=$true)][string]$RuntimePath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$runtime = (Resolve-Path -LiteralPath $RuntimePath).Path
$configFile = Join-Path $runtime 'AutoUpdate\config.json'
$config = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.owner -ne 'native-calendar-holidays-autoupdate-v1' -or
    [IO.Path]::GetFullPath($config.runtimePath).TrimEnd('\') -ne $runtime.TrimEnd('\') -or
    $config.taskName -notmatch '^NativeCalendarHolidays-DataUpdate-[a-f0-9]{12}$') {
    throw 'Invalid updater configuration or task name.'
}
$taskName = [string]$config.taskName
$executable = Join-Path $runtime 'AutoUpdate\NativeCalendarHolidayUpdater.exe'
$arguments = '--config "' + $configFile + '"'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    if (@($existing.Actions).Count -ne 1 -or $existing.Actions[0].Execute -ne $executable -or $existing.Actions[0].Arguments -ne $arguments) {
        throw 'An unrelated task already uses this task name.'
    }
}
if ($Action -eq 'Enable') {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'Updater executable is missing.' }
    $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $firstRun = (Get-Date).AddDays(7).AddMinutes(5)
    $statusFile = Join-Path $runtime 'AutoUpdate\status.json'
    if (Test-Path -LiteralPath $statusFile) {
        try {
            $last = Get-Content -LiteralPath $statusFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($last.lastSuccessfulCheckAt) {
                $candidate = [DateTimeOffset]::Parse($last.lastSuccessfulCheckAt).LocalDateTime.AddDays(7).AddMinutes(5)
                if ($candidate -gt (Get-Date) -and $candidate -lt (Get-Date).AddDays(8)) { $firstRun = $candidate }
                elseif ($candidate -le (Get-Date)) { $firstRun = (Get-Date).AddMinutes(2) }
            }
        } catch { }
    }
    $weekly = New-ScheduledTaskTrigger -Daily -DaysInterval 7 -At $firstRun
    $taskAction = New-ScheduledTaskAction -Execute $executable -Argument $arguments -WorkingDirectory (Split-Path -Parent $executable)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    $principal = New-ScheduledTaskPrincipal -UserId $userSid -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $weekly -Settings $settings -Principal $principal -Description 'Check China holiday JSON once every 7 days. Keep cached data when offline. No login-triggered check.' -Force | Out-Null
} elseif ($Action -eq 'Disable') {
    if ($existing) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
}
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    [ordered]@{taskName=$taskName;state=[string]$task.State;nextRunTime=[string]$info.NextRunTime;lastTaskResult=$info.LastTaskResult;daysInterval=7;atLogon=$false;runLevel=[string]$task.Principal.RunLevel;executable=$executable} | ConvertTo-Json -Compress
} else {
    [ordered]@{taskName=$taskName;state='NotRegistered'} | ConvertTo-Json -Compress
}
