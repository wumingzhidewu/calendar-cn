param(
    [Parameter(Mandatory=$true)][ValidateSet('Enable','Start','Stop','Update','Status')][string]$Action,
    [Parameter(Mandatory=$true)][string]$RuntimePath
)
$ErrorActionPreference = 'Stop'
$runtime = (Resolve-Path -LiteralPath $RuntimePath).Path
$marker = Get-Content (Join-Path $runtime '.native-calendar-holidays.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($marker.owner -ne 'native-calendar-holidays-project-v1' -or $marker.path -ne $runtime) { throw 'Installation ownership mismatch.' }
$loader = Join-Path $runtime 'windhawk.exe'
try {
    $running = @(Get-Process windhawk -ErrorAction SilentlyContinue)
    $own = @($running | Where-Object { $_.Path -eq $loader })
    $other = @($running | Where-Object { $_.Path -ne $loader })
    switch ($Action) {
        'Enable' {
            if ($other.Count -gt 0) { throw '另一套 Windhawk 正在运行，请先退出它，再启用日历标记。' }
            $task = Get-ScheduledTask -TaskName $marker.startupTask
            if ($task.Actions[0].Execute -ne (Join-Path $runtime 'CalendarManager.exe') -or $task.Actions[0].Arguments -ne '--startup') { throw '启动任务与安装目录不一致。' }
            Start-ScheduledTask -TaskName $marker.startupTask
        }
        'Start' {
            if ($other.Count -gt 0) { throw '另一套 Windhawk 正在运行，请先退出它，再启用日历标记。' }
            if ($own.Count -eq 0) { Start-Process -FilePath $loader -ArgumentList '-tray-only' -WindowStyle Hidden }
        }
        'Stop' {
            if ($own.Count -gt 0) {
                if ($other.Count -gt 0) { throw '发现多个 Windhawk 实例，已取消关闭操作。' }
                $p = Start-Process -FilePath $loader -ArgumentList '-exit -wait' -WindowStyle Hidden -PassThru
                if (-not $p.WaitForExit(35000)) { throw '关闭日历标记超时，请稍后重试。' }
                if ($p.ExitCode -ne 0) { throw '关闭日历标记失败。' }
            }
        }
        'Update' {
            $config = Get-Content (Join-Path $runtime 'AutoUpdate/config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
            $task = Get-ScheduledTask -TaskName $config.taskName
            if ($task.Actions[0].Execute -ne (Join-Path $runtime 'AutoUpdate/NativeCalendarHolidayUpdater.exe')) { throw '更新任务与安装目录不一致。' }
            Start-Process -FilePath (Join-Path $runtime 'AutoUpdate/NativeCalendarHolidayUpdater.exe') -ArgumentList @('--config',('"'+(Join-Path $runtime 'AutoUpdate/config.json')+'"'),'--force') -WindowStyle Hidden
        }
        'Status' {
            $text = @('中国节假日日历（预览版）', '')
            $text += if ($own.Count -gt 0) { '日历标记：已启用' } else { '日历标记：已暂停' }
            $text += if ($other.Count -gt 0) { '检测到另一套 Windhawk，启用前请先退出它。' } else { '' }
            $startup = Get-ScheduledTask -TaskName $marker.startupTask -ErrorAction SilentlyContinue
            $text += if ($startup -and $startup.State -ne 'Disabled') { '登录时自动启用：已开启' } else { '登录时自动启用：未开启' }
            $text += '数据检查：每 7 天一次；“立即更新数据”可手动刷新。'
            $statusPath = Join-Path $runtime 'AutoUpdate/status.json'
            if (Test-Path -LiteralPath $statusPath) {
                $status = Get-Content $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $text += if ($status.status -eq 'ok') { '最近数据检查：成功' } else { '最近数据检查：暂未成功，保留旧数据，等待下一次七天检查；也可手动更新。' }
                if ($status.lastSuccessfulCheckAt) { $text += '最近成功时间：' + ([DateTimeOffset]::Parse($status.lastSuccessfulCheckAt).ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')) }
                if ($status.availableYears) { $text += '已有数据：' + (($status.availableYears | Select-Object -First 1).ToString()) + '—' + (($status.availableYears | Select-Object -Last 1).ToString()) + ' 年' }
                if ($status.unpublishedYears) { $text += '等待公布：' + ($status.unpublishedYears -join '、') + ' 年（公布后自动获取）' }
            } else { $text += '首次数据检查尚未完成；内置离线数据可以正常使用。' }
            $text += @('', '绿色“休”：放假；橙色“班”：调休上班。', '暂停只影响本次会话；下次登录会重新启用。')
            [IO.File]::WriteAllLines((Join-Path $runtime 'status-report.txt'), $text, [Text.UTF8Encoding]::new($true))
        }
    }
    exit 0
} catch {
    [IO.File]::WriteAllText((Join-Path $runtime 'last-error.txt'), $_.Exception.Message, [Text.UTF8Encoding]::new($true))
    exit 1
}
