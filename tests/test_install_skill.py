from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from install_skill import install_skill  # noqa: E402


class InstallSkillTests(unittest.TestCase):
    def create_source(self, root: Path) -> Path:
        source = root / "source" / "vibe-upgrader"
        (source / "agents").mkdir(parents=True)
        (source / "scripts" / "__pycache__").mkdir(parents=True)
        (source / "tests").mkdir(parents=True)
        (source / "SKILL.md").write_text(
            "---\nname: vibe-upgrader\ndescription: Test skill.\n---\n\n# Test\n",
            encoding="utf-8",
        )
        (source / "agents" / "openai.yaml").write_text(
            'interface:\n  default_prompt: "Use $vibe-upgrader to test."\npolicy:\n  allow_implicit_invocation: false\n',
            encoding="utf-8",
        )
        (source / "scripts" / "run.py").write_text("print('ok')\n", encoding="utf-8")
        (source / "scripts" / "__pycache__" / "run.pyc").write_bytes(b"cache")
        (source / "tests" / "test_example.py").write_text("pass\n", encoding="utf-8")
        return source

    def test_install_excludes_development_artifacts_and_matches_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = root / "skills" / "vibe-upgrader"
            result = install_skill(source, target)
            self.assertTrue(result["matches"])
            self.assertEqual(result["source_digest"], result["installed_digest"])
            self.assertEqual(result["source_manifest"], result["installed_manifest"])
            self.assertEqual(len(result["source_manifest"]), 3)
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse((target / "tests").exists())
            self.assertFalse((target / "scripts" / "__pycache__").exists())

    def test_replace_creates_rollback_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = root / "skills" / "vibe-upgrader"
            install_skill(source, target)
            (source / "scripts" / "run.py").write_text("print('updated')\n", encoding="utf-8")
            result = install_skill(source, target, replace=True)
            self.assertTrue(result["matches"])
            self.assertIsNotNone(result["backup_path"])
            backup_path = Path(result["backup_path"])
            self.assertTrue(backup_path.is_dir())
            self.assertEqual(backup_path.parent, source.parent / "output" / "install-backups")
            self.assertNotEqual(backup_path.parent, target.parent)

    def test_rejects_backup_root_inside_skill_scan_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.create_source(root)
            target = root / "skills" / "vibe-upgrader"
            install_skill(source, target)
            with self.assertRaisesRegex(ValueError, "outside the Skill scan directory"):
                install_skill(
                    source,
                    target,
                    replace=True,
                    backup_root=target.parent / "install-backups",
                )


if __name__ == "__main__":
    unittest.main()
