from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from component_retrieval import retrieve_components  # noqa: E402


def task(*requests: dict[str, object]) -> dict[str, object]:
    return {
        "task_mode": "proposal",
        "page_type": "marketing_homepage",
        "candidate_requests": list(requests),
        "implementation_permissions": {
            "modify_files": False,
            "install_components": False,
            "add_dependencies": False,
        },
    }


def request(request_id: str, source_type: str, query: str, category: str) -> dict[str, object]:
    return {
        "request_id": request_id,
        "source_type": source_type,
        "query": query,
        "category": category,
        "status": "pending",
    }


def custom_candidate() -> dict[str, object]:
    return {
        "candidate_id": "custom-compatible",
        "candidate_name": "Compatible custom fallback",
        "source_type": "custom_build",
        "category": "hero",
        "query_origin": {"request_id": "custom", "method": "project_analysis", "query": "hero"},
        "problem_fit": "strong",
        "product_fit": "strong",
        "brand_fit": "strong",
        "stack_compatibility": "not_applicable",
        "availability": "not_applicable",
        "evidence_level": "verified",
        "accessibility_risk": "low",
        "performance_cost": "low",
        "dependency_cost": "not_applicable",
        "customization_cost": "low",
        "maintenance_cost": "low",
        "license_status": "not_applicable",
        "design_system_fit": "compatible",
        "responsive_support": "strong",
    }


class ComponentRetrievalTests(unittest.TestCase):
    def test_real_mcp_shape_normalizes_shadcn_metadata_without_invented_safety(self) -> None:
        req = request("foundation-button", "foundation_ui", "button", "button")
        result = retrieve_components(
            task(req),
            PROJECT_ROOT,
            declared_stack_facts="React TypeScript Tailwind",
            raw_attempts=[
                {
                    "request_id": "foundation-button",
                    "retrieval_method": "mcp",
                    "registry_namespace": "@shadcn",
                    "query": "button",
                    "status": "success",
                    "raw_results": [
                        {
                            "name": "button",
                            "type": "registry:ui",
                            "dependencies": ["radix-ui"],
                            "files": [{"path": "registry/new-york-v4/ui/button.tsx", "type": "registry:ui"}],
                        }
                    ],
                }
            ],
        )
        candidate = result["component_candidates"][0]
        self.assertEqual(candidate["source_type"], "foundation_ui")
        self.assertEqual(candidate["availability"], "available")
        self.assertEqual(candidate["accessibility_risk"], "unknown")
        self.assertEqual(candidate["performance_cost"], "unknown")
        self.assertEqual(candidate["license_status"], "unknown")
        self.assertEqual(candidate["field_evidence"]["availability"], "verified_fact")
        self.assertTrue(result["runtime_capabilities"]["shadcn_mcp"]["verified_by_call"])
        self.assertEqual(result["adoption_decisions"][0]["recommended_action"], "defer")

    def test_react_bits_variant_and_dependencies_remain_traceable(self) -> None:
        req = request("react-text", "react_bits", "animated brand text", "text")
        result = retrieve_components(
            task(req),
            PROJECT_ROOT,
            declared_stack_facts="Next.js React TypeScript Tailwind",
            raw_attempts=[
                {
                    "request_id": "react-text",
                    "retrieval_method": "registry_http",
                    "registry_namespace": "@react-bits",
                    "query": "animated brand text",
                    "status": "success",
                    "raw_results": [
                        {
                            "name": "BlurText-TS-TW",
                            "title": "BlurText",
                            "description": "Text starts blurred then resolves.",
                            "type": "registry:component",
                            "dependencies": ["motion@^12.23.12"],
                            "registryDependencies": [],
                            "files": [{"path": "BlurText/BlurText.tsx", "type": "registry:component"}],
                        }
                    ],
                }
            ],
        )
        candidate = result["component_candidates"][0]
        self.assertEqual(candidate["technology_variant"], {"language": "typescript", "styling": "tailwind"})
        self.assertEqual(candidate["npm_dependencies"], ["motion@^12.23.12"])
        self.assertEqual(candidate["retrieval_method"], "registry_http")
        self.assertTrue(candidate["raw_evidence_reference"].startswith("sha256:"))
        self.assertEqual(candidate["responsive_support"], "unknown")
        self.assertEqual(result["adoption_decisions"][0]["recommended_action"], "defer")

    def test_cli_search_and_view_are_the_read_only_mcp_fallback(self) -> None:
        req = request("foundation-button", "foundation_ui", "button", "button")

        def runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
            self.assertNotIn("add", args)
            if "search" in args:
                return subprocess.CompletedProcess(args, 0, "Found 1 item\n- @shadcn/button (ui)\n", "")
            payload = [
                {
                    "name": "button",
                    "type": "registry:ui",
                    "files": [{"path": "ui/button.tsx", "type": "registry:ui"}],
                }
            ]
            return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")

        with patch("component_retrieval.shutil.which", return_value="npx"):
            result = retrieve_components(
                task(req),
                PROJECT_ROOT,
                declared_stack_facts="React",
                enable_cli=True,
                cli_runner=runner,
            )
        self.assertEqual(result["fallback_used"], "cli")
        attempt = result["retrieval_attempts"][0]
        self.assertEqual(attempt["retrieval_method"], "cli")
        self.assertTrue(attempt["search_succeeded"])
        self.assertTrue(attempt["view_succeeded"])
        self.assertTrue(result["runtime_capabilities"]["shadcn_cli"]["search_supported"])

    def test_non_react_target_skips_react_bits_and_selects_compatible_fallback(self) -> None:
        req = request("react-hero", "react_bits", "animated hero", "hero")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package.json"
            original = '{"dependencies":{"vue":"^3.5.0"}}'
            package.write_text(original, encoding="utf-8")
            result = retrieve_components(
                task(req),
                PROJECT_ROOT,
                target_root=root,
                seed_candidates=[custom_candidate()],
                enable_cli=True,
                cli_runner=lambda args, timeout: self.fail("CLI must not run for an incompatible React Bits request"),
            )
            self.assertEqual(package.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "components.json").exists())
        self.assertEqual(result["target_stack"]["compatibility"], "react_incompatible")
        self.assertEqual(result["retrieval_attempts"][0]["status"], "skipped_incompatible")
        self.assertIn("non-React", result["retrieval_attempts"][0]["rejection_reason"])
        self.assertEqual(result["category_recommendations"][0]["candidate_id"], "custom-compatible")

    def test_no_retrieval_path_reports_unresolved_without_writing(self) -> None:
        req = request("react-hero", "react_bits", "animated hero", "hero")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            result = retrieve_components(task(req), PROJECT_ROOT, target_root=root)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(result["candidate_requests"][0]["status"], "unresolved")
        self.assertEqual(result["component_candidates"], [])
        self.assertEqual(result["side_effects"], [])


if __name__ == "__main__":
    unittest.main()
