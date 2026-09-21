Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
Name "中国节假日日历（预览版）"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\NativeCalendarHolidaysDesktop"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "中国节假日日历 · 0.5.3-preview"
VIProductVersion "0.5.3.0"
VIAddVersionKey "ProductName" "中国节假日日历"
VIAddVersionKey "FileDescription" "中国节假日日历安装程序（预览版）"
VIAddVersionKey "FileVersion" "0.5.3-preview"
VIAddVersionKey "LegalCopyright" "GPL-3.0; includes attributed open-source components"
Var PowerShell
Var Prepared
!define MUI_WELCOMEPAGE_TITLE "为原生日历添加休／班标记"
!define MUI_WELCOMEPAGE_TEXT "安装后，点击任务栏右下角时间，即可查看放假和补班标记。$\r$\n$\r$\n包含运行依赖，无需安装 Python 或 Windhawk。登录后自动启用，节假日数据自动更新。$\r$\n$\r$\n本预览版适用于 Windows 11 23H2 x64。标记布局和翻月效果仍需在你的设备上验证。"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}\LICENSE"
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "安装完成"
!define MUI_FINISHPAGE_TEXT "点击右下角时间查看日历。$\r$\n$\r$\n开始菜单中的“中国节假日日历”可以暂停标记、查看状态或卸载。$\r$\n$\r$\n明年的安排公布后会自动获取，无需再次导入。"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
    StrCpy $INSTDIR "$LOCALAPPDATA\NativeCalendarHolidaysDesktop"
    StrCpy $Prepared "0"
    ${IfNot} ${IsNativeAMD64}
        MessageBox MB_ICONSTOP "此预览版仅支持 x64 Windows 11 23H2。" /SD IDOK
        SetErrorLevel 10
        Abort
    ${EndIf}
    SetRegView 64
    ReadRegStr $0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentBuildNumber"
    ${If} $0 != "22631"
        MessageBox MB_ICONSTOP "此预览版仅支持 Windows 11 23H2（22631），未修改你的系统。" /SD IDOK
        SetErrorLevel 10
        Abort
    ${EndIf}
    StrCpy $PowerShell "$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File /oname=SetupRuntime.ps1 "${PAYLOAD}\SetupRuntime.ps1"
    nsExec::ExecToStack '"$PowerShell" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$PLUGINSDIR\SetupRuntime.ps1" -Action Check -RuntimePath "$INSTDIR"'
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "$1" /SD IDOK
        SetErrorLevel 11
        Abort
    ${EndIf}
FunctionEnd

Section "安装"
    SetShellVarContext current
    nsExec::ExecToStack '"$PowerShell" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$PLUGINSDIR\SetupRuntime.ps1" -Action Prepare -RuntimePath "$INSTDIR"'
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "$1" /SD IDOK
        SetErrorLevel 12
        Abort
    ${EndIf}
    StrCpy $Prepared "1"
    SetOutPath "$INSTDIR"
    ClearErrors
    File /r "${PAYLOAD}\*"
    IfErrors failed
    nsExec::ExecToStack '"$PowerShell" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$INSTDIR\SetupRuntime.ps1" -Action Configure -RuntimePath "$INSTDIR"'
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "安装配置未完成：$\r$\n$1" /SD IDOK
        Goto failed
    ${EndIf}
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    CreateDirectory "$SMPROGRAMS\中国节假日日历"
    CreateShortcut "$SMPROGRAMS\中国节假日日历\中国节假日日历.lnk" "$INSTDIR\CalendarManager.exe"
    CreateShortcut "$SMPROGRAMS\中国节假日日历\使用说明.lnk" "$INSTDIR\使用说明.html"
    CreateShortcut "$SMPROGRAMS\中国节假日日历\卸载.lnk" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "DisplayName" "中国节假日日历（预览版）"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "DisplayVersion" "0.5.3-preview"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "DisplayIcon" "$INSTDIR\CalendarManager.exe"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop" "NoRepair" 1
    Exec '"$INSTDIR\CalendarManager.exe" --enable'
    Goto done
failed:
    SetOutPath "$TEMP"
    nsExec::ExecToStack '"$PowerShell" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$PLUGINSDIR\SetupRuntime.ps1" -Action Rollback -RuntimePath "$INSTDIR"'
    Pop $0
    Pop $1
    SetErrorLevel 13
    Abort "安装未完成。"
done:
SectionEnd

Function un.onInit
    SetRegView 64
    StrCpy $PowerShell "$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
    SetShellVarContext current
FunctionEnd

Section "Uninstall"
    SetOutPath "$TEMP"
    nsExec::ExecToStack '"$PowerShell" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$INSTDIR\SetupRuntime.ps1" -Action Uninstall -RuntimePath "$INSTDIR"'
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_ICONSTOP "卸载尚未完成：$\r$\n$1" /SD IDOK
        SetErrorLevel 14
        Abort
    ${EndIf}
    Delete "$SMPROGRAMS\中国节假日日历\中国节假日日历.lnk"
    Delete "$SMPROGRAMS\中国节假日日历\使用说明.lnk"
    Delete "$SMPROGRAMS\中国节假日日历\卸载.lnk"
    RMDir "$SMPROGRAMS\中国节假日日历"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NativeCalendarHolidaysDesktop"
SectionEnd
