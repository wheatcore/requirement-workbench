---
name: frontend-dev-workflow
description: 根据需求拆解前端任务，先准备本地 feature 分支，再逐项实现、验证并分别提交。
---

## 1. 理解需求

- 阅读用户提供的需求 URL、附件或粘贴正文；缺少关键内容时明确指出缺口。
- 将前端工作拆成可独立验收、独立提交的小任务。纯后端工作列为依赖，不在前端任务中臆造接口行为。
- 用户在工作台编辑并确认任务后再执行。

## 2. 准备分支

- 先检查当前分支和工作区状态。
- 若在 `main`，从当前 `main` 创建并切换到 `feature/<module>-<short-description>`，名称使用小写 kebab-case。例如 `git switch -c feature/account-login`。
- 若已在 `feature/` 分支，继续使用当前分支；其他分支遵守目标仓库约定。
- 工作台负责实际分支操作；模型在只读 Skills 准备阶段返回明确的分支动作和名称，编码阶段不自行切分支。

## 3. 逐项实现和验证

- 每次只实现一项任务，并遵守目标仓库 `AGENTS.md` 以及 [project-conventions](../project-conventions/SKILL.md)。
- 根据该项验收标准运行相关检查，记录真实结果。失败时停止并报告原因。

## 4. 逐项提交

- 每项任务完成且验证通过后单独创建一个 Git commit，不合并多个任务。
- 提交信息参考 [auto-commit-push](../auto-commit-push/SKILL.md) 的格式，使用 `<type>: <subject>`，例如 `feat: add account login`。
- 工作台负责暂存和提交；模型编码阶段不执行 `git add`、`git commit` 或 `git push`。不自动推送远程分支。
