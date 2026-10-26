---
name: auto-commit-push
description: 分析当前改动、生成 `type: subject` 格式的 commit message 并创建 commit，完成后询问用户是否需要 push，不自动 push。用户说"提交代码""commit 一下""帮我 commit 这些改动"时使用。
---

当用户要求提交代码时，按以下步骤执行：

## 1. 收集改动信息（并行执行）

- `git status`（不加 `-uall`）
- `git diff` 和 `git diff --staged`
- `git log -n 10 --oneline`，参考本仓库最近的 commit 风格

## 2. 起草 commit message

- 格式：`<type>: <subject>`，例如 `feat: 新增自定义分析面板导出功能`
- `type` 参考本仓库常见类型：`feat`（新功能）、`fix`（修复）、`refactor`（重构）、`docs`（文档）、`chore`（杂项）等，不加 scope、不加 gitmoji 前缀
- 聚焦"为什么改"而不是逐行复述 diff
- 多行 message 用 heredoc 传递

## 3. 暂存并创建 commit

- 按文件名精确 `git add`，不用 `git add -A` / `git add .`
- **不要**提交可能含密钥的文件（`.env`、`credentials.json` 等），发现时提醒用户
- 创建 commit，**不加** `--no-verify` / `--no-gpg-sign`
- 若 pre-commit hook（lint-staged）修改了文件：重新 `git add` 变更后的文件，**新建一次 commit**（不要 `--amend`，因为原 commit 未成功）
- `git commit` 后跑一次 `git status` 确认结果

## 4. 询问是否 push（关键步骤，不可跳过）

- commit 成功后，**必须**明确询问用户是否要 push 到远程，例如："commit 已完成，需要我 push 到远程分支吗？"
- 在用户明确确认之前，**不要**执行 `git push`

## 5. 用户确认 push 后

- 检查当前分支是否已 track 远程分支，未 track 则用 `git push -u origin <branch>`
- 禁止 `--force` / `--force-with-lease`，除非用户明确要求；若目标是 `main`/`master`，需再次向用户确认后才能执行
- push 完成后告知用户结果（分支名、是否有远程 PR 链接等）
