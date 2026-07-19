#!/usr/bin/env python3
"""Validate and install the canonical Vibe Upgrader source deterministically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = SCRIPT_DIR.parent
EXCLUDED_DIRS = {"__pycache__", "tests"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def installable_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name in {".DS_Store"}:
            continue
        files.append(path)
    return sorted(files, key=lambda value: value.relative_to(source).as_posix())


def file_manifest(root: Path, files: list[Path] | None = None) -> list[dict[str, Any]]:
    selected = files if files is not None else installable_files(root)
    manifest: list[dict[str, Any]] = []
    for path in selected:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        manifest.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return manifest


def tree_digest(manifest: list[dict[str, Any]]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_source(source: Path) -> None:
    skill_file = source / "SKILL.md"
    metadata_file = source / "agents" / "openai.yaml"
    if not skill_file.is_file() or not metadata_file.is_file():
        raise ValueError("Source must contain SKILL.md and agents/openai.yaml.")
    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError("SKILL.md frontmatter is missing or malformed.")
    keys = {
        line.split(":", 1)[0].strip()
        for line in match.group(1).splitlines()
        if ":" in line and not line.startswith((" ", "\t"))
    }
    if keys != {"name", "description"}:
        raise ValueError("SKILL.md frontmatter must contain only name and description.")
    if "name: vibe-upgrader" not in match.group(1):
        raise ValueError("Skill name must be vibe-upgrader.")
    metadata = metadata_file.read_text(encoding="utf-8")
    if 'allow_implicit_invocation: false' not in metadata:
        raise ValueError("agents/openai.yaml must disable implicit invocation.")
    if "$vibe-upgrader" not in metadata:
        raise ValueError("agents/openai.yaml default_prompt must mention $vibe-upgrader.")


def default_target() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "skills" / "vibe-upgrader"


def default_backup_root(source: Path) -> Path:
    return source.resolve().parent / "output" / "install-backups"


def install_skill(
    source: Path,
    target: Path,
    *,
    replace: bool = False,
    dry_run: bool = False,
    backup_root: Path | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    target = target.expanduser().resolve()
    backup_root = (
        backup_root.expanduser().resolve()
        if backup_root is not None
        else default_backup_root(source)
    )
    validate_source(source)
    if source == target or source in target.parents:
        raise ValueError("Install target must not be the source or a child of the source.")
    if backup_root == target.parent or target.parent in backup_root.parents:
        raise ValueError("Backup root must be outside the Skill scan directory.")

    source_files = installable_files(source)
    source_manifest = file_manifest(source, source_files)
    source_digest = tree_digest(source_manifest)
    result: dict[str, Any] = {
        "source": str(source),
        "target": str(target),
        "file_count": len(source_manifest),
        "source_manifest": source_manifest,
        "installed_manifest": None,
        "source_digest": source_digest,
        "installed_digest": None,
        "matches": False,
        "backup_path": None,
        "backup_root": str(backup_root),
        "dry_run": dry_run,
        "excluded": ["tests/", "__pycache__/", "*.pyc", "*.pyo", ".DS_Store"],
    }
    if dry_run:
        result["installed_manifest"] = source_manifest
        result["installed_digest"] = source_digest
        result["matches"] = True
        return result
    if target.exists() and not replace:
        raise FileExistsError(f"Target exists; rerun with --replace: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.install-{uuid.uuid4().hex}"
    backup: Path | None = None
    try:
        staging.mkdir()
        for source_file in source_files:
            relative = source_file.relative_to(source)
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
        staged_manifest = file_manifest(staging)
        if tree_digest(staged_manifest) != source_digest:
            raise RuntimeError("Staged install does not match the canonical source manifest.")

        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / f"{target.name}.backup-{stamp}"
            if backup.exists():
                backup = backup_root / f"{target.name}.backup-{stamp}-{uuid.uuid4().hex[:8]}"
            target.replace(backup)
        staging.replace(target)
        installed_manifest = file_manifest(target)
        installed_digest = tree_digest(installed_manifest)
        if installed_digest != source_digest:
            raise RuntimeError("Installed files do not match the canonical source manifest.")
        result.update(
            {
                "installed_digest": installed_digest,
                "installed_manifest": installed_manifest,
                "matches": True,
                "backup_path": str(backup) if backup else None,
            }
        )
        return result
    except Exception:
        if target.exists() and backup and backup.exists():
            shutil.rmtree(target)
            backup.replace(target)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and install the canonical Vibe Upgrader Skill.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Canonical skill source directory.")
    parser.add_argument("--target", default=str(default_target()), help="Installed skill directory.")
    parser.add_argument(
        "--backup-root",
        help="Rollback backup directory outside the Skill scan root (default: project output/install-backups).",
    )
    parser.add_argument("--replace", action="store_true", help="Back up and replace an existing installation.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and calculate the manifest without writing.")
    parser.add_argument("--manifest-output", help="Optional JSON file for the release/install result.")
    args = parser.parse_args(argv)
    result = install_skill(
        Path(args.source),
        Path(args.target),
        replace=args.replace,
        dry_run=args.dry_run,
        backup_root=Path(args.backup_root) if args.backup_root else None,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.manifest_output:
        output = Path(args.manifest_output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
