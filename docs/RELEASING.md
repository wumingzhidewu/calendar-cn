# 发布流程 / Releasing

源码提交到 Git，安装程序作为 GitHub Release 附件分发，不提交 `build/`、`releases/` 或本机配置。当前版本仍使用预览发布。

1. 更新 `project.json`、安装器版本、中英文 README 和 CHANGELOG。
2. 在 Windows 构建机器上运行 `python -m unittest discover -s tests -v`。构建更新器、原生 DLL 和安装包，命令见 [开发与构建](BUILDING.md)。
3. 检查安装包包含项目及依赖许可证、对应源码。核对支持的 Windows 版本和已知限制。
4. 提交源码后，从该提交创建带说明的标签。当前标签格式为 `<版本>-<日期>-<短提交号>`；Release 标为 pre-release。
5. 先创建 Release 草稿，上传安装器与 `SHA256SUMS.txt`，核对附件名称、大小和 SHA-256，再发布草稿。每个发布使用新标签；不要替换已发布的二进制附件。
6. 发布后检查标签目标、附件下载地址和 Windows CI 结果。GitHub 自动提供该标签的源码归档，普通用户下载 EXE 即可。

`SHA256SUMS.txt` 可以用 PowerShell 的 `Get-FileHash -Algorithm SHA256` 核对。哈希用于核对下载完整性，不等于代码签名。当前程序没有 Authenticode 签名。

Source stays in Git; installers and checksums are release assets. Test and build on Windows, tag the exact source commit, upload all assets to a draft release, verify them, and publish as a pre-release until visual acceptance is complete. Use new tags for subsequent builds rather than replacing published assets. GitHub provides source archives automatically.

References: [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).
