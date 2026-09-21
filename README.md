# calendar-cn

给 Windows 原生日历添加中国节假日「休／班」标记，支持 20 套主题。

[下载](https://github.com/wumingzhidewu/calendar-cn/releases) · [English](README.en.md)

## 安装

仅支持 **Windows 11 23H2（22631）x64**。当前为预览版，[已知限制](CHANGELOG.md)。

1. 在 [Releases](https://github.com/wumingzhidewu/calendar-cn/releases) 下载 `Calendar-CN-Setup-0.5.3-x64.exe`，双击安装，无需另装 Python 或 Windhawk。
2. 点击任务栏右下角时间，打开系统日历。
3. 绿色 **休** 表示放假，橙色 **班** 表示调休上班。

升级前先卸载旧版；安装时请退出其他 Windhawk 实例。

## 换主题

在开始菜单打开 **中国节假日日历**：

1. 选择主题。
2. 选择背景：**插画背景**显示主题画面，**渐变底色／纯色背景**只显示配色。
3. 点击 **应用主题**，关闭日历后重新展开。

选择 **系统默认**恢复原外观，休班标记保留。

![主题设计预览，非系统实拍](docs/design/expressive-contact-sheet.jpg)

*主题设计预览，非系统实拍。*

## 更新与卸载

- **节假日数据**：每七天自动更新。下一年安排公布并被数据源收录后自动获取；也可点击 **立即更新数据**。
- **暂停标记**：点击 **暂停本次**，下次登录会重新启用。
- **卸载**：打开 Windows「设置 → 应用 → 已安装的应用」，找到 **中国节假日日历**并卸载。

---

[问题反馈](https://github.com/wumingzhidewu/calendar-cn/issues) · [开发与构建](docs/BUILDING.md) · [GPL-3.0](LICENSE)

基于 [Windhawk](https://github.com/ramensoftware/windhawk)，节假日数据来自 [holiday-cn](https://github.com/NateScarlet/holiday-cn)。[第三方许可](THIRD_PARTY_NOTICES.md)
