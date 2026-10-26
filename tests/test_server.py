import base64
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from requirement_workbench import server


class RequirementTests(unittest.TestCase):
    def test_browser_folder_listing_and_path_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "b").mkdir()
            (root / "a").mkdir()
            (root / "a" / ".git").mkdir()
            (root / "file.txt").write_text("not a folder", encoding="utf-8")
            result = server.browse_folders(str(root))
            self.assertEqual(result["path"], str(root.resolve()))
            self.assertEqual([item["name"] for item in result["directories"]], ["a", "b"])
            self.assertTrue(result["directories"][0]["git"])
            self.assertEqual(result["parent"], str(root.parent.resolve()))
        with self.assertRaisesRegex(ValueError, "绝对路径"):
            server.browse_folders("relative/path")

    def test_text_and_docx_attachment(self):
        self.assertEqual(server.extract_attachment("req.md", b"# Hello"), "# Hello")
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>需求内容</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(server.extract_attachment("req.docx", out.getvalue()), "需求内容")

    def test_requirement_combines_sources(self):
        payload = {"note": "完成登录页", "attachment": {"name": "a.txt", "data": base64.b64encode("验收通过".encode()).decode()}}
        value = server.load_requirement(payload)
        self.assertIn("完成登录页", value)
        self.assertIn("验收通过", value)

    def test_feishu_doc_is_read_before_planning(self):
        url = "https://example.feishu.cn/wiki/AbC123"
        response = subprocess.CompletedProcess([], 0, json.dumps({"ok": True, "data": {"document": {"content": "# 登录页需求\n支持密码登录"}}}), "")
        with patch.object(server.shutil, "which", return_value="lark-cli"), patch.object(server.subprocess, "run", return_value=response) as runner:
            content = server.load_requirement({"url": url})
        self.assertIn("支持密码登录", content)
        self.assertIn("docs", runner.call_args.args[0])
        self.assertIn("+fetch", runner.call_args.args[0])
        self.assertNotIn("shell", runner.call_args.kwargs)

    def test_unreadable_feishu_doc_requests_visible_input(self):
        url = "https://example.feishu.cn/wiki/AbC123"
        with patch.object(server, "fetch_feishu_doc", side_effect=server.NeedsInputError("没有权限")):
            with self.assertRaisesRegex(server.NeedsInputError, "补充需求正文"):
                server.load_requirement({"url": url})
            self.assertIn("人工说明", server.load_requirement({"url": url, "note": "人工说明"}))

    def test_model_can_request_missing_input_instead_of_making_up_tasks(self):
        with self.assertRaisesRegex(server.NeedsInputError, "接口文档"):
            server.validate_plan({"status": "needs_input", "missing_input": "请提供接口文档", "tasks": [], "risks": [], "summary": ""})

    def test_private_url_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "内网"):
            server.validate_public_url("http://127.0.0.1/private")

    def test_plan_validation(self):
        plan = server.validate_plan({"summary": "test", "risks": [], "tasks": [{"title": "任务", "description": "修改组件", "acceptance": "构建通过", "commit_message": "feat: ui\nother", "skills": ["vue"]}]})
        self.assertEqual(plan["tasks"][0]["commit_message"], "feat: ui other")
        with self.assertRaises(ValueError):
            server.validate_plan({"tasks": []})

    def test_role_skills_defaults_and_legacy_config_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch.object(server, "DATA_DIR", folder), patch.object(server, "CONFIG_FILE", folder / "config.json"):
                defaults = server.load_config()
                self.assertNotIn("agents", defaults)
                self.assertEqual(len(defaults["skills"]), 4)
                self.assertEqual(set(server.ROLES), {"frontend", "backend"})
                self.assertIn("frontend-dev-workflow", server.selected_guides({"role": "frontend"}))
                self.assertIn("backend-dev-workflow", server.selected_guides({"role": "backend"}))
                server.save_config({"skills": [
                    {"id": "s1", "role": "frontend", "name": "Vue", "content": "Use Vue components", "default": False},
                    {"id": "s2", "role": "test", "name": "Smoke", "content": "Check browser behavior", "default": True},
                ]})
                self.assertEqual(len(server.load_config()["skills"]), 2)
                text = server.selected_guides({"role": "frontend", "selected": {"skills": ["s1"]}})
                self.assertIn("Use Vue components", text)
                with self.assertRaisesRegex(ValueError, "岗位无效"):
                    server.selected_guides({"role": "test"})
                self.assertIn("s2", {item["id"] for item in server.load_config()["skills"]})
                with self.assertRaisesRegex(ValueError, "不属于当前岗位"):
                    server.selected_guides({"role": "backend", "selected": {"skills": ["s1"]}})
                (folder / "config.json").write_text(json.dumps({"skills": [
                    {"id": "legacy", "name": "P0 冒烟", "content": "old custom rule"}],
                    "agents": [{"id": "a1", "name": "Reviewer", "content": "old agent"}]}), encoding="utf-8")
                migrated = server.load_config()
                self.assertEqual(migrated["version"], 4)
                self.assertEqual(len(migrated["skills"]), 5)
                self.assertEqual(next(item for item in migrated["skills"] if item["id"] == "legacy")["role"], "test")
                (folder / "config.json").write_text(json.dumps({"version": 2, "skills": [
                    {"id": "custom", "role": "frontend", "name": "Custom", "content": "keep me"}]}), encoding="utf-8")
                upgraded = server.load_config()
                self.assertEqual(upgraded["version"], 4)
                self.assertEqual(len(upgraded["skills"]), 5)
                self.assertIn("custom", {item["id"] for item in upgraded["skills"]})

    def test_codex_command_uses_compatible_sandbox_flags(self):
        with patch.object(server, "codex_path", return_value="codex"):
            read = server.codex_command(Path("project"), Path("out"), read_only=True, output_schema=Path("schema.json"))
            write = server.codex_command(Path("project"), Path("out"), read_only=False, output_schema=Path("schema.json"))
            smoke = server.codex_command(Path("project"), Path("out"), read_only=True, output_schema=Path("schema.json"), skip_git_repo_check=True)
        self.assertIn("read-only", read)
        self.assertNotIn("--approve-for-me", read)
        self.assertIn("--approve-for-me", write)
        self.assertNotIn("-s", write)
        self.assertNotIn("--skip-git-repo-check", read)
        self.assertIn("--skip-git-repo-check", smoke)

    def test_workflow_includes_referenced_skills_and_task_skill_names(self):
        entries = server.selected_skill_entries({"role": "frontend", "selected": {
            "skills": ["builtin-frontend-dev-workflow"]}})
        self.assertEqual({entry["name"] for entry in entries},
                         {"frontend-dev-workflow", "project-conventions", "auto-commit-push"})
        from_task = server.selected_skill_entries({"role": "frontend", "selected": {"skills": []}},
                                                  ["frontend-dev-workflow"])
        self.assertEqual({entry["name"] for entry in from_task},
                         {"frontend-dev-workflow", "project-conventions", "auto-commit-push"})

    def test_claude_command_and_structured_output(self):
        with patch.object(server, "claude_path", return_value="claude"):
            planning = server.claude_command(read_only=True, output_schema=server.SCHEMA)
            coding = server.claude_command(read_only=False, output_schema=server.EXEC_SCHEMA)
        self.assertIn("plan", planning)
        self.assertNotIn("Bash", planning)
        self.assertIn("acceptEdits", coding)
        self.assertIn("Read,Glob,Grep,Edit,Write,Bash", coding)
        self.assertIn("--json-schema", coding)
        self.assertEqual(json.loads(coding[coding.index("--json-schema") + 1])["required"], ["status", "summary", "verification"])

        class FakeProcess:
            stdin = io.StringIO()
            stdout = io.StringIO(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "已检查项目"}]}}) + "\n" + json.dumps({"type": "result", "structured_output": {"status": "complete", "summary": "done", "verification": "checked"}}) + "\n")

            def wait(self):
                return 0

        job = server.Job(kind="run")
        with patch.object(server, "claude_path", return_value="claude"), patch.object(server.subprocess, "Popen", return_value=FakeProcess()):
            answer = server.run_claude(job, Path("project"), "implement", read_only=False, output_schema=server.EXEC_SCHEMA)
        self.assertEqual(json.loads(answer)["status"], "complete")
        self.assertIn("已检查项目", "\n".join(job.logs))

    def test_provider_dispatch(self):
        self.assertEqual(server.selected_provider({}), "codex")
        with self.assertRaisesRegex(ValueError, "执行器无效"):
            server.selected_provider({"provider": "unknown"})
        with patch.object(server, "run_claude", return_value='{"status":"ready"}') as claude:
            answer = server.run_provider("claude", server.Job("plan"), Path("project"), "plan", read_only=True, output_schema=server.SCHEMA)
        self.assertIn("ready", answer)
        claude.assert_called_once()

    def test_clean_git_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            subprocess.run(["git", "init", "-q", str(folder)], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.name", "Test"], check=True)
            (folder / "README.md").write_text("test")
            subprocess.run(["git", "-C", str(folder), "add", "--all"], check=True)
            subprocess.run(["git", "-C", str(folder), "commit", "-qm", "init"], check=True)
            self.assertTrue(server.project_info(str(folder))["clean"])
            (folder / "README.md").write_text("changed")
            self.assertFalse(server.project_info(str(folder))["clean"])

    def test_execute_creates_one_commit_per_task(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(folder)], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.name", "Test"], check=True)
            (folder / "README.md").write_text("initial", encoding="utf-8")
            subprocess.run(["git", "-C", str(folder), "add", "--all"], check=True)
            subprocess.run(["git", "-C", str(folder), "commit", "-qm", "init"], check=True)
            plan = {"summary": "example", "risks": [], "tasks": [
                {"title": "first", "description": "one", "acceptance": "file exists", "commit_message": "feat: one", "skills": []},
                {"title": "second", "description": "two", "acceptance": "file exists", "commit_message": "feat: two", "skills": []},
            ]}
            calls = 0
            phases = []

            def fake_codex(job, project, prompt, **kwargs):
                nonlocal calls
                phases.append(kwargs["read_only"])
                if kwargs["read_only"]:
                    self.assertIn("整份任务计划的 Skill 准备", prompt)
                    return json.dumps({"status": "ready", "applied_skills": ["frontend-dev-workflow"],
                                       "instructions": "全部任务按组件规范实现", "verification": "检查文件",
                                       "branch_action": "create", "branch_name": "feature/two-tasks", "branch_reason": "frontend-dev-workflow 要求",
                                       "task_guidance": [
                                           {"task_index": 1, "instructions": "先实现第一个任务", "verification": "检查任务一"},
                                           {"task_index": 2, "instructions": "再实现第二个任务", "verification": "检查任务二"}],
                                       "reason": ""})
                self.assertIn("全部任务按组件规范实现", prompt)
                self.assertIn("先实现第一个任务" if calls == 0 else "再实现第二个任务", prompt)
                self.assertEqual(subprocess.check_output(["git", "-C", str(project), "branch", "--show-current"], text=True).strip(),
                                 "feature/two-tasks")
                calls += 1
                (project / f"task-{calls}.txt").write_text(f"task {calls}", encoding="utf-8")
                return json.dumps({"status": "complete", "summary": "implemented", "verification": "checked files"})

            job = server.Job(kind="run")
            with patch.object(server, "run_codex", side_effect=fake_codex):
                result = server.execute_plan(job, {"project": str(folder), "role": "frontend", "plan": plan})
            self.assertEqual(len(result["commits"]), 2)
            self.assertEqual(phases, [True, False, False])
            self.assertEqual(result["branch"], "feature/two-tasks")
            self.assertIn("已应用 Skills", "\n".join(job.logs))
            self.assertEqual(subprocess.check_output(["git", "-C", str(folder), "log", "-2", "--format=%s"], text=True).splitlines(), ["feat: two", "feat: one"])
            self.assertTrue(server.project_info(str(folder))["clean"])

    def test_skill_preflight_blocks_code_execution(self):
        task = {"title": "feature", "description": "work", "acceptance": "done", "skills": []}
        job = server.Job(kind="run")
        blocked = json.dumps({"status": "blocked", "applied_skills": [], "instructions": "",
                              "verification": "", "branch_action": "keep", "branch_name": "", "branch_reason": "",
                              "task_guidance": [], "reason": "缺少项目接口定义"})
        plan = {"summary": "feature", "tasks": [task]}
        with patch.object(server, "run_provider", return_value=blocked) as runner:
            with self.assertRaisesRegex(RuntimeError, "缺少项目接口定义"):
                server.prepare_plan_skills(job, "codex", Path("project"), "frontend", plan, [], "main")
        self.assertTrue(runner.call_args.kwargs["read_only"])
        self.assertEqual(runner.call_args.kwargs["output_schema"], server.SKILL_SCHEMA)
        incomplete = json.dumps({"status": "ready", "applied_skills": [], "instructions": "通用要求",
                                 "verification": "", "branch_action": "keep", "branch_name": "", "branch_reason": "",
                                 "task_guidance": [], "reason": ""})
        with patch.object(server, "run_provider", return_value=incomplete):
            with self.assertRaisesRegex(RuntimeError, "未覆盖全部任务"):
                server.prepare_plan_skills(job, "codex", Path("project"), "frontend", plan, [], "main")

    def test_frontend_skill_creates_local_feature_branch_before_coding(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(folder)], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(folder), "config", "user.name", "Test"], check=True)
            (folder / "README.md").write_text("initial", encoding="utf-8")
            subprocess.run(["git", "-C", str(folder), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(folder), "commit", "-qm", "init"], check=True)
            skill = next(item for item in server.bundled_skills() if item["name"] == "frontend-dev-workflow")
            job = server.Job(kind="run")
            with self.assertRaisesRegex(RuntimeError, "要求先从 main 创建 feature 分支"):
                server.prepare_local_branch(job, folder, "main", {"branch_action": "keep", "branch_name": ""}, [skill])
            notes = {"branch_action": "create", "branch_name": "feature/report-filter", "branch_reason": "frontend-dev-workflow 要求"}
            branch = server.prepare_local_branch(job, folder, "main", notes, [skill])
            self.assertEqual(branch, "feature/report-filter")
            self.assertEqual(subprocess.check_output(["git", "-C", str(folder), "branch", "--show-current"], text=True).strip(), branch)
            self.assertEqual(server.prepare_local_branch(job, folder, branch,
                                                         {"branch_action": "keep", "branch_name": ""}, [skill]), branch)

    def test_verification_command_blocks_failed_result(self):
        with tempfile.TemporaryDirectory() as temp:
            job = server.Job(kind="run")
            server.run_verification(job, Path(temp), f'"{sys.executable}" -c "print(123)"')
            self.assertIn("123", "\n".join(job.logs))
            with self.assertRaisesRegex(RuntimeError, "退出码"):
                server.run_verification(job, Path(temp), f'"{sys.executable}" -c "raise SystemExit(2)"')


if __name__ == "__main__":
    unittest.main()
