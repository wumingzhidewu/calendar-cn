# 开发与构建 / Building


开发环境需要 Python 3.10+、Windhawk 1.7.3 的完整便携目录、NSIS 3.12。普通用户不需要这些工具。

```powershell
python -m unittest discover -s tests -v
python manage.py data
python theme_presets.py
python manage.py build --windhawk C:\Tools\Windhawk
python -m pip install -r requirements-build.txt
python manage.py build-updater
python installer\build_installer.py --windhawk C:\Tools\Windhawk --nsis C:\Tools\NSIS\makensis.exe --output releases\Calendar-CN-Setup-0.5.3-x64.exe
```

构建目录需预先存在。`build/`、`releases/`、临时文件和本地密钥配置不会纳入 Git。

常用维护命令：

```powershell
python manage.py update --years 2025 2026 2027
python manage.py auto-status --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
python manage.py disable-auto --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
python manage.py enable-auto --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
```

安装包版本请使用 Windows 的卸载入口；`manage.py uninstall` 会拒绝直接删除它，避免遗留登录任务。开发者命令行安装与桌面安装包的行为区别见 [安装说明](DESKTOP_INSTALLER.md)。

## English


Developers need Python 3.10+, the complete Windhawk 1.7.3 portable toolchain and NSIS 3.12. End users do not need them.

```powershell
python -m unittest discover -s tests -v
python manage.py data
python theme_presets.py
python manage.py build --windhawk C:\Tools\Windhawk
python -m pip install -r requirements-build.txt
python manage.py build-updater
python installer\build_installer.py --windhawk C:\Tools\Windhawk --nsis C:\Tools\NSIS\makensis.exe --output releases\Calendar-CN-Setup-0.5.3-x64.exe
```

Create the output directory first. Git ignores `build/`, `releases/`, temporary files and local key configuration.

Maintenance commands:

```powershell
python manage.py update --years 2025 2026 2027
python manage.py auto-status --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
python manage.py disable-auto --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
python manage.py enable-auto --path "$env:LOCALAPPDATA\NativeCalendarHolidaysDesktop"
```

Use the Windows uninstall entry for the desktop installer edition. `manage.py uninstall` refuses to remove it directly, which avoids leaving the login task behind. The developer CLI installation has a different startup policy; see [installer notes](DESKTOP_INSTALLER.md).

