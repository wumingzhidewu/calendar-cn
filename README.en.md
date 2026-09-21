# calendar-cn

Chinese holiday and adjusted-workday badges for the native Windows calendar, with 20 themes.

[Download](https://github.com/wumingzhidewu/calendar-cn/releases) · [简体中文](README.md)

## Install

Supports **Windows 11 23H2 (22631), x64 only**. This is a preview; see [known limitations](CHANGELOG.md).

1. Download `Calendar-CN-Setup-0.5.3-x64.exe` from [Releases](https://github.com/wumingzhidewu/calendar-cn/releases) and run it. No separate Python or Windhawk installation is needed.
2. Click the clock in the bottom-right corner to open the Windows calendar.
3. Green **休** means a day off; orange **班** means an adjusted working day.

Uninstall older versions before upgrading. Close other Windhawk instances before installation.

## Change themes

Open **中国节假日日历** from the Start menu. The app interface is in Chinese.

1. Choose a theme.
2. Choose **插画背景** for artwork, or **渐变底色／纯色背景** for gradient/solid colors without artwork.
3. Click **应用主题** (Apply theme), then close and reopen the calendar.

Choose **系统默认** (System default) to restore the original appearance while keeping holiday badges.

![Theme design previews, not system screenshots](docs/design/expressive-contact-sheet.jpg)

*Design previews, not system screenshots.*

## Updates and removal

- **Holiday data** updates every seven days. Next year's schedule is fetched once published and added to the data source. Click **立即更新数据** to check manually.
- **Pause badges** with **暂停本次**. They will start again at the next login.
- **Uninstall** through Windows Settings → Apps → Installed apps → **中国节假日日历**.

---

[Report an issue](https://github.com/wumingzhidewu/calendar-cn/issues) · [Build from source](docs/BUILDING.md) · [GPL-3.0](LICENSE)

Built on [Windhawk](https://github.com/ramensoftware/windhawk), with holiday data from [holiday-cn](https://github.com/NateScarlet/holiday-cn). [Third-party licenses](THIRD_PARTY_NOTICES.md)
