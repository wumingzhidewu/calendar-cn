param(
    [Parameter(Mandatory=$true)][ValidateSet('Apply')][string]$Action,
    [Parameter(Mandatory=$true)][string]$RuntimePath,
    [Parameter(Mandatory=$true)][string]$ThemeId,
    [ValidateSet('art','gradient','solid')][string]$BackgroundMode = 'art'
)
$ErrorActionPreference = 'Stop'
$runtime = (Resolve-Path -LiteralPath $RuntimePath).Path
try {
    $marker = Get-Content (Join-Path $runtime '.native-calendar-holidays.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($marker.owner -ne 'native-calendar-holidays-project-v1' -or $marker.path -ne $runtime) { throw '安装目录不匹配。' }
    $catalog = Get-Content (Join-Path $runtime 'themes/catalog.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $theme = @($catalog.themes | Where-Object { $_.id -eq $ThemeId })
    if ($ThemeId -ne 'system' -and ($theme.Count -ne 1 -or $ThemeId -notmatch '^[a-z0-9-]+$')) { throw '未找到所选主题。' }
    $iniPath = Join-Path $runtime 'AppData/Engine/Mods/local-native-calendar-holidays.ini'
    $original = Get-Content -LiteralPath $iniPath -Raw -Encoding Unicode
    $backup = Join-Path $runtime 'theme-original.ini'
    if (-not (Test-Path -LiteralPath $backup)) { [IO.File]::WriteAllText($backup, $original, [Text.Encoding]::Unicode) }
    $base = Get-Content -LiteralPath $backup -Raw -Encoding Unicode
    $sections = [ordered]@{}
    $section = ''
    foreach ($line in ($base -split '\r?\n')) {
        if ($line -match '^\s*\[([^\]]+)\]\s*$') { $section=$matches[1]; $sections[$section]=[ordered]@{} }
        elseif ($section -and $line -match '^([^=;#]+)=(.*)$') { $sections[$section][$matches[1].Trim()]=$matches[2] }
    }
    if (-not $sections.Contains('Mod') -or $sections['Mod']['LibraryFileName'] -ne 'native-calendar-holidays.dll') { throw '日历模块配置不匹配。' }
    if ($ThemeId -ne 'system') {
        $settings = [ordered]@{}
        $preset = Get-Content (Join-Path $runtime "themes/presets/$ThemeId.$BackgroundMode.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $imagePath = Join-Path $runtime "themes/assets/$ThemeId.jpg"
        if ($BackgroundMode -eq 'art' -and -not (Test-Path -LiteralPath $imagePath -PathType Leaf)) { throw '主题背景图片缺失。' }
        $uri = [Security.SecurityElement]::Escape(([Uri]$imagePath).AbsoluteUri)
        foreach ($property in $preset.PSObject.Properties) { $settings[$property.Name]=([string]$property.Value).Replace('{BACKGROUND_URI}', $uri) }
        $sections['Settings']=$settings
    }
    # Windhawk observes this value to reload settings without restarting Explorer.
    $stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if ($original -match '(?m)^SettingsChangeTime=(\d+)') { $stamp=[Math]::Max($stamp,([long]$matches[1]+1)) }
    $sections['Mod']['SettingsChangeTime']=[string]$stamp
    $lines = @()
    foreach ($key in $sections.Keys) {
        $lines += "[$key]"
        foreach ($name in $sections[$key].Keys) { $lines += $name+'='+$sections[$key][$name] }
        $lines += ''
    }
    $temporary=$iniPath+'.theme-tmp'
    [IO.File]::WriteAllLines($temporary,$lines,[Text.Encoding]::Unicode)
    [IO.File]::Replace($temporary,$iniPath,($iniPath+'.theme-previous'))
    $selected = [ordered]@{id=$ThemeId;backgroundMode=$BackgroundMode;appliedAt=[DateTimeOffset]::Now.ToString('o')}
    [IO.File]::WriteAllText((Join-Path $runtime 'selected-theme.json'),($selected | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    exit 0
} catch {
    [IO.File]::WriteAllText((Join-Path $runtime 'last-error.txt'),$_.Exception.Message,[Text.UTF8Encoding]::new($true))
    exit 1
}
