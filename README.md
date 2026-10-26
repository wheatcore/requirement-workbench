# 需求工作台

本地网页工具：前端和后端岗位使用需求 URL、附件、Git 项目和运行者自己电脑上的 Codex CLI 或 Claude Code CLI 拆解代码任务。可以先编辑计划，再逐项实现、验证并创建 Git commit。Skills 按岗位分类，可在网页中新增、编辑、删除、多选和设置默认项。

**[在线交互演示](https://wheatcore.github.io/requirement-workbench/)** · [源代码](https://github.com/wheatcore/requirement-workbench) · [MIT License](LICENSE)

在线页使用浏览器中的示例项目和模拟结果，可以体验需求输入、任务编辑、Skills 选择和分点提交界面。它不会调用 AI、读取本机文件或创建真实 Git commit。真实执行需在自己的电脑运行下述本地版。

## 分享给其他人

从 GitHub 下载源码或 Release ZIP 即可。仓库不包含本机的 `.data` 配置。每个人在自己的电脑上准备：

1. Python 3.11 或更新版本、Git 和需要开发的 Git 项目。
2. 至少安装一种 AI 执行器：Codex CLI（运行 `codex login` 登录），或 Claude Code CLI（运行 `claude auth login` 登录）。

读取飞书 Wiki / Docx 链接时，还需在运行者自己的电脑安装 `lark-cli` 并运行 `lark-cli auth login`，使用有文档权限的飞书账号授权。未安装或无权限时，页面会提供粘贴正文、上传附件和重试入口。

工具只在本机 `127.0.0.1` 开网页服务，调用当前选择的本机 CLI。不会使用分享者的账号、配置或项目文件。内置 Skills 随工具分发；自定义 Skills 保存在运行者自己的数据目录中。旧版本的测试 Skill 配置仍保留在本机数据文件里，但不在新版页面显示。

本公开仓库内置的是通用 Skill 范例。请在网页“管理 Skills”中加入你所在项目的约定；不要把公司内部规则、凭据或需求附件提交到公开仓库。

### 从源码运行

```sh
git clone https://github.com/wheatcore/requirement-workbench.git
cd requirement-workbench
python -m requirement_workbench --open
```

在 Windows 上也可以双击 `start.bat`；macOS / Linux 可执行 `sh start.sh`。

### 直接运行

- Windows：双击 `start.bat`。
- macOS / Linux：执行 `sh start.sh`。
- 通用：在本目录执行 `python -m requirement_workbench --open`（部分系统用 `python3`）。

“浏览…”按钮会打开网页内的目录选择界面，可逐级进入文件夹，也可输入绝对路径后点击“前往”。macOS 路径示例：`/Users/name/projects/my-app`。

默认地址：<http://127.0.0.1:8765>。可用 `--port 9000` 改端口。

### 安装为 CLI 命令

在解压后的目录执行：

```sh
python -m pip install .
requirement-workbench --open
```

如需读取 PDF，改用 `python -m pip install '.[pdf]'`。其他支持的格式为 DOCX、TXT、MD、CSV、JSON、HTML。安装后可以在任意目录运行 `requirement-workbench --open`。如 CLI 不在 PATH，可设置 `CODEX_BIN` 或 `CLAUDE_BIN` 指向对应的可执行文件。

## 工作流程

1. 输入公开网页或飞书 Wiki / Docx URL、上传附件或直接粘贴需求。其他需要登录的网页请导出附件。
2. 选择前端或后端，再选择 Codex CLI 或 Claude Code CLI；从当前岗位的 Skills 下拉列表多选，最后选择 Git 项目文件夹。前端默认选中 `frontend-dev-workflow`，后端默认选中 `backend-dev-workflow`。前端还内置 `project-conventions` 和 `auto-commit-push`；可在“管理”中调整默认项。
3. 点击“分析并拆解任务”。页面进入 02 / 编辑任务；当前执行器只读分析项目，飞书正文由本机授权读取。
4. 在 02 步编辑任务顺序、工作内容、验收标准和 commit message。可选填每项提交前的验证命令。
5. 点击执行。当前执行器先以只读模式调用一次所选 Skills、任务中引用的 Skills 及其同岗位依赖，检查项目内相关 Skills 和 `AGENTS.md`，生成覆盖全部任务的共用要求、逐项要求和本地分支操作。若 Skill 要求先切分支，工作台会在编码前创建或切换本地分支，并将实际分支写入日志。之后按顺序逐项修改代码、报告验证结果；任务完成且可选验证命令返回零时，工具才创建对应 commit。切换执行器后需重新生成计划。

Claude Code 的任务拆解使用 `plan` 权限模式；编码使用 `acceptEdits` 模式，并明确允许文件读写和 Bash 命令。可在“每项提交前的验证命令”填写项目测试命令，由工作台在每项提交前再运行一次。Claude Code 的认证状态可在页面顶部查看。

执行前项目必须没有未提交改动。失败或中断时会保留已有改动，不自动回滚；请在项目中检查后再继续。工具不会推送 Git 远端。运行日志仅保存在当前服务进程内，关闭服务后清空。

## 开发与反馈

运行 `python -m unittest discover -s tests` 执行测试。修改工作台界面后，运行 `python scripts/build_demo.py` 更新 `docs/` 中的静态演示页。欢迎通过 GitHub Issues 报告问题或提交 PR；请先删除日志、截图和复现材料中的私有仓库路径、需求正文与访问令牌。
