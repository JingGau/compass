from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from tools.python_env import detect_python_environment


class PythonEnvTest(unittest.TestCase):
    def test_prefers_compass_python_override(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_python = root / "python"
            fake_python.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"-c\" ]; then\n"
                "  echo '3.11.8'\n"
                "else\n"
                "  echo 'Python 3.11.8'\n"
                "fi\n",
                encoding="utf-8",
            )
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

            report = detect_python_environment(root, environ={"COMPASS_PYTHON": str(fake_python)})

            self.assertTrue(report.usable)
            self.assertEqual(report.selected_python, str(fake_python))
            self.assertEqual(report.source, "COMPASS_PYTHON")
            self.assertEqual(report.version, "3.11.8")
            self.assertIn(f"{fake_python} -m pip install", report.install_command)

    def test_uses_project_venv_before_current_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            venv_bin = root / ".venv" / "bin"
            venv_bin.mkdir(parents=True)
            fake_python = venv_bin / "python"
            fake_python.write_text("#!/bin/sh\nif [ \"$1\" = \"-c\" ]; then echo '3.10.13'; fi\n", encoding="utf-8")
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

            report = detect_python_environment(root, environ={})

            self.assertTrue(report.usable)
            self.assertEqual(report.selected_python, str(fake_python))
            self.assertEqual(report.source, ".venv")

    def test_falls_back_to_current_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            report = detect_python_environment(root, environ={}, include_path=False)

            self.assertTrue(report.usable)
            self.assertEqual(report.selected_python, sys.executable)
            self.assertEqual(report.source, "current")
            self.assertIn("python -m venv .venv", report.create_venv_command)
            self.assertIn(".venv/bin/python -m pip install", report.install_command)


if __name__ == "__main__":
    unittest.main()
