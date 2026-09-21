# Changelog / 版本记录

## 0.5.3-preview — 2026-09-21

首次公开预览版。仅支持 Windows 11 23H2（22631）x64。

- 保留 Windows 原生日历，增加绿色“休”和橙色“班”。
- 内置二十套主题，提供插画、渐变及纯色背景。
- 每七天自动获取 holiday-cn 的上一年、当年和下一年数据；离线保留缓存。
- 使用独立覆盖层，并将标记移动绑定到原生日历的合成滚动属性，替代定时位置轮询。
- 主题应用提示同时显示所选主题与背景类型。
- 提供不依赖系统 Python 的安装包。

验证：41 项本地自动测试通过，原生 DLL、管理程序与安装包构建成功。连续滚动同步、多种 DPI 和全部主题组合尚待实机验收。之前内部版本曾发生日期区缩短和切换主题后无响应，不建议分发旧安装包。当前版本尚未签名，不作为稳定版发布。

First public preview, for Windows 11 23H2 (22631), x64 only.

- Native calendar holiday/workday badges and twenty themes with three background modes.
- Seven-day holiday updates with a rolling previous/current/next-year window and offline cache.
- Separate badge overlay driven by native compositor scrolling instead of periodic position polling.
- Theme confirmation includes the selected background type.
- Standalone installer; no system Python installation required.

Validation: 41 local automated tests passed; DLL, manager and installer builds succeeded. Continuous scrolling, DPI combinations and every theme still require visual acceptance. Earlier internal builds had collapsed calendar layouts and unresponsive theme switching; do not distribute those installers. This unsigned preview is not a stable release.
