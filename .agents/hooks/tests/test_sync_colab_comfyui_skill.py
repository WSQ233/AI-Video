import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_REL = ".agents/hooks/sync_colab_comfyui_skill.py"
SKILL_REL = ".agents/skills/colab-comfyui-control/SKILL.md"


class ColabComfyUISkillHookTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="ai_video_skill_hook_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

        copy_Files = [
            SCRIPT_REL,
            ".agents/hooks.json",
            ".codex/hooks.json",
            "configs/runtime_profile.json",
            "configs/models_manifest.json",
            "configs/nodes_lock.json",
            "scripts/setup_env.py",
            "scripts/batch_runner.py",
            "scripts/sync_models_to_drive.py",
            "notebooks/00_sync_models_to_drive.ipynb",
            "notebooks/02_h100_batch_runner.ipynb",
            "workflows/shared/minimax_h3_fl2va_api.json",
        ]
        for rel in copy_Files:
            src = ROOT / rel
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

        self.skill_path = self.root / SKILL_REL
        self.skill_path.parent.mkdir(parents=True, exist_ok=True)
        self.skill_path.write_bytes(
            "---\r\nname: colab-comfyui-control\r\ndescription: test\r\n---\r\n"
            "手写规程前缀\r\n<!-- pipeline-baseline:begin -->\r\n<!-- pipeline-baseline:end -->\r\n手写规程后缀\r\n".encode(
                "utf-8"
            )
        )
        res = self.run_cli()
        self.assertEqual(res.returncode, 0, res.stderr)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-X", "utf8", SCRIPT_REL, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def run_antigravity_hook(self, event_name: str, continuation: bool = False) -> dict:
        payload = {
            "hookEventName": event_name,
            "continuationActive": continuation,
            "cwd": str(self.root),
        }
        res = subprocess.run(
            [sys.executable, "-X", "utf8", "hooks/sync_colab_comfyui_skill.py", "--hook"],
            cwd=self.root / ".agents",
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return json.loads(res.stdout)

    def run_codex_stop_hook(self, retry: bool = False) -> dict:
        config = json.loads((self.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        handler = config["hooks"]["Stop"][0]["hooks"][0]
        command = handler["commandWindows" if os.name == "nt" else "command"]
        res = subprocess.run(
            command,
            shell=True,
            cwd=self.root / "scripts",
            input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": retry}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=True,
        )
        return json.loads(res.stdout)

    def test_pipeline_change_auto_syncs_skill_and_preserves_handwritten_crlf(self) -> None:
        self.assertEqual(self.run_cli("--check").returncode, 0)

        # 修改 configs/runtime_profile.json 中的启动参数
        rt_path = self.root / "configs/runtime_profile.json"
        rt = json.loads(rt_path.read_text(encoding="utf-8"))
        rt["gpu_profiles"]["A100_40GB"]["comfyui_args"] = "--bf16-vae --cache-none --port 8199"
        rt_path.write_text(json.dumps(rt, ensure_ascii=False, indent=2), encoding="utf-8")

        # --check 应当检测到流程已变更而 SKILL.md 尚未同步
        self.assertNotEqual(self.run_cli("--check").returncode, 0)

        # 触发 Antigravity PostToolUse hook，应当自动同步 SKILL.md 并返回 {}
        out = self.run_antigravity_hook("PostToolUse")
        self.assertEqual(out, {})
        self.assertEqual(self.run_cli("--check").returncode, 0)

        raw = self.skill_path.read_bytes()
        self.assertIn(b"--port 8199", raw)
        self.assertTrue(raw.startswith("---\r\n".encode("utf-8")))
        self.assertTrue(raw.endswith("手写规程后缀\r\n".encode("utf-8")))
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))

    def test_script_and_workflow_changes_sync_on_stop_hooks(self) -> None:
        # 新增脚本 CLI 参数
        setup_path = self.root / "scripts/setup_env.py"
        setup_path.write_text(
            setup_path.read_text(encoding="utf-8")
            + '\n# parser.add_argument("--custom-fast-stage", action="store_true")\n',
            encoding="utf-8",
        )
        self.assertNotEqual(self.run_cli("--check").returncode, 0)

        codex_out = self.run_codex_stop_hook()
        self.assertIn("systemMessage", codex_out)
        self.assertIn("--custom-fast-stage", self.skill_path.read_text(encoding="utf-8"))
        self.assertEqual(self.run_codex_stop_hook(), {})

    def test_corrupt_marker_blocks_safely_without_data_loss(self) -> None:
        damaged = self.skill_path.read_bytes().replace(b"pipeline-baseline:end", b"corrupted")
        self.skill_path.write_bytes(damaged)

        agy_stop = self.run_antigravity_hook("Stop", continuation=False)
        self.assertEqual(agy_stop["decision"], "continue")
        self.assertEqual(self.skill_path.read_bytes(), damaged)

        agy_retry = self.run_antigravity_hook("Stop", continuation=True)
        self.assertEqual(agy_retry["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
