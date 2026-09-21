# 日历主题

主题修改的范围限于原生日历区域：背景、文字颜色、边框、圆角及选中边框。休班标记由独立覆盖层绘制，不修改日期格模板或字体，主题不会覆盖它。

## 使用

管理窗口中有两个下拉框：主题和背景。背景可选插画、渐变、纯色。选好后点击“应用主题”，再展开系统日历。选择“系统默认”会还原第一次应用主题时保存的配置。

首次应用时，模块配置备份为安装目录中的 `theme-original.ini`。每次写入使用临时文件替换，并保存上一份配置。`selected-theme.json` 记录当前主题和背景模式。管理窗口下次打开时会恢复这两个选项。

## 文件

- `themes/catalog.json`：主题名称、明暗、配色、圆角及背景生成提示。
- `themes/assets/*.jpg`：运行时使用的本地背景。
- `themes/presets/*.json`：二十套主题、三种模式，共六十份配置。
- `docs/design/generated-backgrounds/*.png`：未加字的原始生成背景。
- `docs/design/previews/*.png`：加上真实日期和休班标记的完整设计图。
- `docs/design/index.html`：本地主题图册。
- `docs/design/provenance.json`：模型、参考图、图片尺寸和校验值。

## 重新导出

```powershell
python -m pip install -r requirements-design.txt
python theme_presets.py
python tools/prepare_theme_assets.py
python tools/render_theme_previews.py
python tools/build_theme_gallery.py
```

预览使用固定的 2026 年 10 月数据。农历来自 Windows `ChineseLunisolarCalendar`，休班来自仓库中的年度 JSON。中文文本、数字和徽标由 Pillow 排版，不由图像模型生成。

更新背景生成时使用了用户提供的原生日历截图和统一布局参考；图像模型为 `gpt-image-2`。配置和密钥没有放进仓库。JPEG 是供运行时加载的版本，原始 PNG 保留在设计目录中。

## 验证范围

已检查十张设计图，修正了选中圈与节日文字重叠的问题，并淡化了月白山水主题中穿过日期标题的竹叶。配色测试要求日期正文在主题纯色底上达到至少 4.5:1 的对比度。

Windows PowerShell 集成测试覆盖插画、渐变、纯色、恢复默认、中文与空格路径，以及无效主题不改写配置。它们是配置层测试，不等于十套主题已经在真实系统日历中完成验收。

仍需检查实际日历的背景加载、深浅主题文字、今日状态、日期选择、农历、翻月和不同 DPI。Windows 内部布局与设计稿不一定完全一致；如插画模式未加载，可先用渐变或纯色模式定位问题。


## 新增艺术系列

0.5.0 新增二次元、国风、科技、立体幻想和深海装饰主题十套，原主题保留。新作在下拉列表顶部，名称前带“新 ·”。完整创意提示词及构图说明见 [艺术主题设计记录](design/expressive/ART_DIRECTION.md)。

## 滚动与插画背景

0.5.3 将休班覆盖层绑定到原生 ScrollViewer 的合成滚动属性，滚动和惯性移动不再依赖 250 毫秒位置轮询。日期容器更新在渲染事件中处理，覆盖层在日期视口内裁剪；关闭扩展时解除动画和事件。

要显示完整主题画面，在“背景”中选择“插画背景”。“渐变底色”和“纯色背景”只使用主题配色，不显示插画。应用后的提示会同时显示主题名和背景类型。
