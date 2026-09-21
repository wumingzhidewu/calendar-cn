param(
    [Parameter(Mandatory=$true)][ValidateSet('Check','Prepare','Configure','Rollback','Uninstall')][string]$Action,
    [Parameter(Mandatory=$true)][string]$RuntimePath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::Unicode
$expected = Join-Path $env:LOCALAPPDATA 'NativeCalendarHolidaysDesktop'
$runtime = [IO.Path]::GetFullPath($RuntimePath).TrimEnd('\')
if ($runtime -ne [IO.Path]::GetFullPath($expected).TrimEnd('\')) { throw '安装路径不匹配，操作已取消。' }
$markerFile = Join-Path $runtime '.native-calendar-holidays.json'
$sha = [Security.Cryptography.SHA256]::Create()
try { $suffix = (-join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($runtime.ToLowerInvariant())) | ForEach-Object { $_.ToString('x2') })).Substring(0,12) } finally { $sha.Dispose() }
$startupName = 'NativeCalendarHolidays-Start-' + $suffix
$updateName = 'NativeCalendarHolidays-DataUpdate-' + $suffix
$manager = Join-Path $runtime 'CalendarManager.exe'

function Assert-Owned {
    if (-not (Test-Path -LiteralPath $markerFile -PathType Leaf)) { throw '未找到本程序的安装标识，操作已取消。' }
    $script:marker = Get-Content -LiteralPath $markerFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($marker.owner -ne 'native-calendar-holidays-project-v1' -or $marker.path -ne $runtime -or -not $marker.installerManaged) { throw '安装标识不匹配，操作已取消。' }
    if ((Get-Item -LiteralPath $runtime).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '安装目录是链接，操作已取消。' }
    foreach ($entry in (Get-ChildItem -LiteralPath $runtime -Recurse -Force)) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '安装目录包含链接，请先检查后再卸载。' }
    }
}

function Assert-TaskOwner([string]$name, [string]$exe, [string]$arguments) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task -and (@($task.Actions).Count -ne 1 -or $task.Actions[0].Execute -ne $exe -or $task.Actions[0].Arguments -ne $arguments)) { throw '发现同名但属于其他程序的任务，操作已取消。' }
    return $task
}

try {
    if ($Action -in @('Check','Prepare')) {
        $build = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuildNumber
        if ($build -ne '22631') { throw '这个预览版只支持 Windows 11 23H2（22631）。' }
        $currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $sessionId = (Get-Process -Id $PID).SessionId
        foreach ($explorer in @(Get-CimInstance Win32_Process -Filter "Name='explorer.exe' AND SessionId=$sessionId")) {
            $owner = Invoke-CimMethod -InputObject $explorer -MethodName GetOwnerSid
            if ($owner.Sid -and $owner.Sid -ne $currentSid) { throw '请使用当前桌面登录账户安装；不要使用另一个账户的管理员凭据。' }
        }
        if (Get-Service -Name Windhawk -ErrorAction SilentlyContinue) { throw '已经安装另一套 Windhawk，请使用开发者版集成，避免两个加载器冲突。' }
        if (@(Get-Process windhawk -ErrorAction SilentlyContinue).Count -gt 0) { throw '另一套 Windhawk 正在运行，请先退出后再安装。' }
        if ((Test-Path -LiteralPath $runtime) -and @(Get-ChildItem -LiteralPath $runtime -Force).Count -gt 0) { throw '安装目录已存在，请先从“已安装的应用”卸载旧版。' }
        Assert-TaskOwner $startupName $manager '--startup' | Out-Null
        Assert-TaskOwner $updateName (Join-Path $runtime 'AutoUpdate/NativeCalendarHolidayUpdater.exe') ('--config "' + (Join-Path $runtime 'AutoUpdate/config.json') + '"') | Out-Null
        if ($Action -eq 'Prepare') {
            New-Item -ItemType Directory -Force $runtime | Out-Null
            $marker = [ordered]@{owner='native-calendar-holidays-project-v1';path=$runtime;version='0.5.3-preview';installerManaged=$true;startupTask=$startupName;updateTask=$updateName}
            [IO.File]::WriteAllText($markerFile, ($marker | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
        }
        exit 0
    }
    Assert-Owned
    if ($Action -eq 'Configure') {
        $auto = Join-Path $runtime 'AutoUpdate'
        $config = [ordered]@{owner='native-calendar-holidays-autoupdate-v1';runtimePath=$runtime;version='0.5.3-preview';taskName=$updateName;yearPolicy='previous-current-next';source='NateScarlet/holiday-cn';schedule=@{intervalDays=7;atLogon=$false;retryCount=0}}
        [IO.File]::WriteAllText((Join-Path $auto 'config.json'), ($config | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
        $writable = Join-Path $runtime 'AppData/Engine/ModsWritable'
        New-Item -ItemType Directory -Force $writable | Out-Null
        & icacls.exe $runtime /grant '*S-1-15-2-1:(OI)(CI)(RX)' '*S-1-15-2-2:(OI)(CI)(RX)' /Q | Out-Null
        if ($LASTEXITCODE -ne 0) { throw '无法设置日历扩展的读取权限。' }
        & icacls.exe $writable /grant '*S-1-15-2-1:(OI)(CI)(M)' '*S-1-15-2-2:(OI)(CI)(M)' /Q | Out-Null
        if ($LASTEXITCODE -ne 0) { throw '无法设置日历扩展的状态目录。' }
        & icacls.exe $writable /setintegritylevel '(OI)(CI)L' /Q | Out-Null
        if ($LASTEXITCODE -ne 0) { throw '无法初始化日历扩展的状态目录。' }
        & (Join-Path $auto 'Configure-AutoUpdate.ps1') -Action Enable -RuntimePath $runtime | Out-Null
        $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $logon = New-ScheduledTaskTrigger -AtLogOn -User $userSid
        $logon.Delay = 'PT15S'
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
        $principal = New-ScheduledTaskPrincipal -UserId $userSid -LogonType Interactive -RunLevel Limited
        $startAction = New-ScheduledTaskAction -Execute $manager -Argument '--startup' -WorkingDirectory $runtime
        Assert-TaskOwner $startupName $manager '--startup' | Out-Null
        Register-ScheduledTask -TaskName $startupName -Action $startAction -Trigger $logon -Settings $settings -Principal $principal -Description 'Enable China holiday badges in the original Windows calendar after login.' -Force | Out-Null
        Start-ScheduledTask -TaskName $updateName
        exit 0
    }
    # Rollback/uninstall: verify both task actions before deleting either.
    $startTask = Assert-TaskOwner $startupName $manager '--startup'
    $updateTask = Assert-TaskOwner $updateName (Join-Path $runtime 'AutoUpdate/NativeCalendarHolidayUpdater.exe') ('--config "' + (Join-Path $runtime 'AutoUpdate/config.json') + '"')
    foreach ($task in @($startTask,$updateTask)) {
        if ($task) {
            Stop-ScheduledTask -TaskName $task.TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
        }
    }
    $loader = Join-Path $runtime 'windhawk.exe'
    $running = @(Get-Process windhawk -ErrorAction SilentlyContinue)
    $own = @($running | Where-Object { $_.Path -eq $loader })
    if ($own.Count -gt 0) {
        if (@($running | Where-Object { $_.Path -ne $loader }).Count -gt 0) { throw '存在多个 Windhawk 实例，请先退出本程序后重试卸载。' }
        $p = Start-Process -FilePath $loader -ArgumentList '-exit -wait' -WindowStyle Hidden -PassThru
        if (-not $p.WaitForExit(35000) -or $p.ExitCode -ne 0) { throw '日历标记尚未退出，未删除运行文件。' }
    }
    # Stop only the updater/manager processes from this exact installation.
    foreach ($p in @(Get-Process NativeCalendarHolidayUpdater,CalendarManager -ErrorAction SilentlyContinue)) {
        if ($p.Path -and ([IO.Path]::GetDirectoryName($p.Path) -in @($runtime,(Join-Path $runtime 'AutoUpdate')))) { Stop-Process -Id $p.Id -Force }
    }
    # This is the exact fixed, ownership-checked directory; no cross-shell deletion.
    Remove-Item -LiteralPath $runtime -Recurse -Force
    exit 0
} catch {
    [Console]::OutputEncoding = [Text.Encoding]::Unicode
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
