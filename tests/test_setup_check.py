from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

from tools.setup_check import inspect_setup, render_setup_report


class SetupCheckTest(unittest.TestCase):
    def test_missing_env_reports_minimum_required_step(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            report = inspect_setup(root, environ={})
            rendered = render_setup_report(report)

            self.assertFalse(report.env_exists)
            self.assertFalse(report.minimum_ready)
            self.assertIn("CODE_ROOT", report.missing_minimum)
            self.assertIn("cp .env.example .env", rendered)
            self.assertIn("先完成配置", rendered)

    def test_code_root_only_is_minimum_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code_root = root / "projects"
            code_root.mkdir()
            (root / ".env").write_text(f"CODE_ROOT={code_root}\n", encoding="utf-8")

            report = inspect_setup(root, environ={})

            self.assertTrue(report.env_exists)
            self.assertTrue(report.minimum_ready)
            self.assertEqual(report.code_root, str(code_root))
            self.assertTrue(report.code_root_exists)
            self.assertFalse(report.adapter_status["sls"].configured)
            self.assertFalse(report.adapter_status["platform"].configured)

    def test_adapter_status_uses_env_file_and_runtime_environment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code_root = root / "projects"
            code_root.mkdir()
            (root / ".env").write_text(
                "\n".join(
                    [
                        f"CODE_ROOT={code_root}",
                        "SLS_ACCESS_KEY_ID=ak",
                        "SLS_ACCESS_KEY_SECRET=sk",
                    ]
                ),
                encoding="utf-8",
            )

            report = inspect_setup(
                root,
                environ={"PLATFORM_USERNAME": "user", "PLATFORM_PASSWORD": "pass"},
            )

            self.assertTrue(report.adapter_status["sls"].configured)
            self.assertTrue(report.adapter_status["platform"].configured)

    def test_python_override_can_come_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code_root = root / "projects"
            code_root.mkdir()
            (root / ".env").write_text(
                "\n".join(
                    [
                        f"CODE_ROOT={code_root}",
                        f"COMPASS_PYTHON={sys.executable}",
                    ]
                ),
                encoding="utf-8",
            )

            report = inspect_setup(root, environ={})

            self.assertTrue(report.python_environment.usable)
            self.assertEqual(report.python_environment.source, "COMPASS_PYTHON")
            self.assertEqual(report.python_environment.selected_python, sys.executable)


if __name__ == "__main__":
    unittest.main()
