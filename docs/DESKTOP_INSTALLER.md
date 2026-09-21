# 面向普通用户的安装包

## 分发与使用

只需分发 `Calendar-CN-Setup-0.4.0-x64.exe`。用户不需要 Python、Windhawk、命令行或编译器。安装向导、开始菜单入口、管理窗口和使用说明均为中文。

安装包包含 C++ 日历扩展、最小 Windhawk 1.7.3 运行库、LLVM 运行库、独立数据更新器及离线数据。更新器所需 Python 已封装在 EXE 内部，不使用系统 Python 或 Codex 的运行环境。

当前仍是未签名预览版，只允许 Windows 11 23H2（22631）x64。日期格视觉验收尚未完成，不应宣称已经支持全部 Windows 11 版本。标准用户如果必须输入另一账户的管理员凭据，会被账户检查拒绝，避免把程序装到错误账户；请由当前登录的管理员账户安装。

## 安装行为

- 安装在当前用户 `%LOCALAPPDATA%\NativeCalendarHolidaysDesktop`。
- 在开始菜单创建管理程序、说明和卸载入口，在 Windows“已安装的应用”中登记。
- 注册当前用户登录后 15 秒启动标记的任务，及每七天自动更新数据的任务。
- 两个任务均以当前用户普通权限执行，不保存密码，不注册系统服务。
- 每次启动检查其他 Windhawk 实例，避免误操作别人的安装。
- 只给安装目录授予沙盒读取权限；可写的低完整性区域限于运行状态子目录。
- 内部调用 Windows 自带的 PowerShell，RemoteSigned 只对这些子进程生效，不修改系统执行策略；企业组策略如果禁止运行脚本，安装会报告失败。

0.3.0 的安装与卸载测试记录保留在 `docs/INSTALLER_VERIFIED.json`。0.4.0 增加了主题选择器；本版本的主题配置与构建记录见 `docs/THEME_VALIDATION.json`。

## 卸载与失败保护

卸载先验证固定安装路径和归属标识，再停止并删除本实例的两项任务、退出本实例加载器、移除安装文件和应用登记。目录含链接、归属不匹配或同名任务指向别的程序时拒绝继续。

预检发现已有 Windhawk、重复安装目录或不支持的系统时，不写入安装文件。安装配置失败会尝试回滚本次创建的目录和任务。卸载不会删除项目源码、其他 Windhawk、此前原型或无关文件。

## 构建

开发环境需要 Python、完整 Windhawk 1.7.3 工具链和 NSIS 3.12；普通用户不需要。

```powershell
python manage.py build --windhawk C:\Tools\Windhawk
python -m pip install -r requirements-build.txt
python manage.py build-updater
python installer\build_installer.py --windhawk C:\Tools\Windhawk --nsis C:\Tools\NSIS\makensis.exe --output Calendar-CN-Setup-0.4.0-x64.exe
```

`vendor/windhawk-1.7.3-source.zip` 是官方 v1.7.3 源码归档，随运行库一起分发。安装目录 `Source` 中还包含本项目的对应源码；许可证在根目录和 `licenses` 中。

## 已验证与未验证

已在当前机器验证：

- 已有 Windhawk 冲突时退出码为 11，原进程不变、未创建安装目录。
- 静默完整安装退出码为 0，应用登记、开始菜单入口和两个计划任务创建成功。
- 普通权限启动任务成功启动安装目录中的 Windhawk；数据更新任务成功执行并核对数据。
- 中文管理窗口的无障碍控件树包含所有按钮；状态命令生成中文运行报告。
- 错误卸载路径被拒绝，无关文件保留。
- 卸载退出正常，安装目录、两项任务及应用登记均被删除。
- 此前原型恢复运行，原型自动数据更新任务保留。

限制：桌面捕获工具在本次界面检查时返回黑图，激活窗口报告拒绝访问，因此管理窗口像素布局没有完成视觉验收。系统日历宿主被挂起并保留了此前原型模块，本次没有把新路径的原生日历注入视为已验证；仍需在干净登录会话测试首次注入、日期格遮挡和翻月。这些限制与“安装任务成功”分开记录。
