from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def tree_manifest(root: Path) -> list[tuple[str, int, str]]:
    return [
        (
            path.relative_to(root).as_posix(),
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


class RuntimeWriteTests(unittest.TestCase):
    def test_standard_and_experimental_cli_do_not_mutate_skill_tree_without_dash_b(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "skills" / "vibe-upgrader"
            work = root / "work"
            shutil.copytree(
                SKILL_DIR,
                installed,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc", "*.pyo"),
            )
            work.mkdir()
            before = tree_manifest(installed)
            env = os.environ.copy()
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            env.pop("PYTHONPYCACHEPREFIX", None)

            for track in ("standard", "experimental"):
                with self.subTest(track=track):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(installed / "scripts" / "search_motionsites.py"),
                            "runtime write regression probe",
                            "--task-mode",
                            "proposal",
                            "--upgrade-track",
                            track,
                        ],
                        cwd=work,
                        env=env,
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(tree_manifest(installed), before)
                    self.assertFalse((installed / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
