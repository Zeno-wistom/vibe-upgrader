from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from component_decision import REQUIRED_CANDIDATE_FIELDS, decide_candidates  # noqa: E402


def decision_task(page_type: str, task_mode: str = "proposal") -> dict[str, Any]:
    can_modify = task_mode == "implementation"
    return {
        "task_mode": task_mode,
        "page_type": page_type,
        "component_opportunities": [
            {
                "area": "test",
                "problem": "Solve the stated page problem.",
                "candidate_categories": ["test"],
                "source_bias": [
                    "current_project_components",
                    "foundation_ui",
                    "react_bits",
                    "custom_build",
                ],
            }
        ],
        "preferred_sources": [
            {"source": "current_project_components"},
            {"source": "foundation_ui"},
            {"source": "react_bits"},
            {"source": "custom_build"},
        ],
        "foundation_ui_queries": ["accessible foundation control"],
        "react_bits_queries": ["expressive component"],
        "implementation_permissions": {
            "modify_files": can_modify,
            "install_components": can_modify,
            "add_dependencies": can_modify,
        },
    }


def candidate(candidate_id: str, name: str, source_type: str, category: str, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "candidate_id": candidate_id,
        "candidate_name": name,
        "source_type": source_type,
        "category": category,
        "query_origin": {"request_id": "fixture", "method": "test_fixture", "query": category},
        "problem_fit": "strong",
        "product_fit": "strong",
        "brand_fit": "strong",
        "stack_compatibility": "compatible",
        "availability": "available",
        "evidence_level": "verified",
        "accessibility_risk": "low",
        "performance_cost": "low",
        "dependency_cost": "low",
        "customization_cost": "low",
        "maintenance_cost": "low",
        "license_status": "compatible",
        "design_system_fit": "compatible",
        "responsive_support": "strong",
        "field_evidence": {
            "availability": "verified_fact",
            "stack_compatibility": "verified_fact",
            "license_status": "verified_fact",
        },
    }
    data.update(overrides)
    if source_type in {"existing_project", "existing_design_system", "custom_build"}:
        data.setdefault("license_status", "not_applicable")
        data.setdefault("dependency_cost", "not_applicable")
    return data


class ComponentDecisionEngineTests(unittest.TestCase):
    def test_saas_settings_prefers_existing_and_rejects_irrelevant_motion(self) -> None:
        task = decision_task("settings", "analysis")
        result = decide_candidates(
            task,
            [
                candidate("existing-form", "Existing form", "existing_project", "form"),
                candidate(
                    "foundation-form",
                    "Foundation form",
                    "foundation_ui",
                    "form",
                    brand_fit="moderate",
                    customization_cost="medium",
                ),
                candidate(
                    "animated-form",
                    "High-animation form",
                    "react_bits",
                    "form",
                    problem_fit="none",
                    performance_cost="high",
                ),
                candidate(
                    "custom-form",
                    "Custom form",
                    "custom_build",
                    "form",
                    problem_fit="moderate",
                    maintenance_cost="medium",
                ),
            ],
        )
        actions = {item["candidate_id"]: item["recommended_action"] for item in result["adoption_decisions"]}
        self.assertEqual(actions["existing-form"], "reuse")
        self.assertEqual(actions["foundation-form"], "install")
        self.assertEqual(actions["animated-form"], "reject")
        self.assertEqual(actions["custom-form"], "custom_build")
        self.assertEqual(result["category_recommendations"][0]["candidate_id"], "existing-form")
        self.assertTrue(all(item["execution_status"] != "allowed_after_authorization" for item in result["adoption_decisions"]))

    def test_marketing_home_allows_react_bits_but_custom_brand_can_win(self) -> None:
        task = decision_task("marketing_homepage", "proposal")
        result = decide_candidates(
            task,
            [
                candidate(
                    "static-hero",
                    "Static hero",
                    "existing_project",
                    "hero",
                    problem_fit="moderate",
                    product_fit="moderate",
                    brand_fit="weak",
                ),
                candidate(
                    "react-hero",
                    "React Bits hero",
                    "react_bits",
                    "hero",
                    brand_fit="moderate",
                    performance_cost="medium",
                ),
                candidate(
                    "heavy-hero",
                    "Heavy animation hero",
                    "react_bits",
                    "hero",
                    performance_cost="high",
                    dependency_cost="medium",
                ),
                candidate("brand-hero", "Custom brand hero", "custom_build", "hero"),
                candidate(
                    "foundation-nav",
                    "Foundation navigation",
                    "foundation_ui",
                    "navigation",
                    brand_fit="moderate",
                ),
            ],
        )
        decisions = {item["candidate_id"]: item for item in result["adoption_decisions"]}
        self.assertEqual(decisions["react-hero"]["recommended_action"], "install")
        self.assertEqual(decisions["heavy-hero"]["recommended_action"], "adapt")
        self.assertEqual(decisions["heavy-hero"]["decision_status"], "conditional")
        category_winners = {item["category"]: item["candidate_id"] for item in result["category_recommendations"]}
        self.assertEqual(category_winners["hero"], "brand-hero")
        self.assertEqual(category_winners["navigation"], "foundation-nav")

    def test_enterprise_admin_prefers_design_system_and_small_adaptation(self) -> None:
        task = decision_task("enterprise_admin", "proposal")
        result = decide_candidates(
            task,
            [
                candidate("system-loading", "Design system loading", "existing_design_system", "loading"),
                candidate(
                    "react-loading",
                    "React Bits loading",
                    "react_bits",
                    "loading",
                    design_system_fit="conflict",
                ),
                candidate(
                    "third-party-loading",
                    "Third-party loading",
                    "external_component",
                    "loading",
                    problem_fit="moderate",
                    dependency_cost="high",
                ),
                candidate(
                    "adapt-loading",
                    "Small existing loading adaptation",
                    "existing_project",
                    "loading",
                    design_system_fit="adaptable",
                    customization_cost="low",
                ),
            ],
        )
        actions = {item["candidate_id"]: item["recommended_action"] for item in result["adoption_decisions"]}
        self.assertEqual(actions["system-loading"], "reuse")
        self.assertEqual(actions["adapt-loading"], "adapt")
        self.assertEqual(actions["react-loading"], "reject")
        self.assertEqual(actions["third-party-loading"], "reject")
        self.assertEqual(result["category_recommendations"][0]["candidate_id"], "system-loading")

    def test_unavailable_incompatible_and_unknown_candidates_fall_back(self) -> None:
        task = decision_task("generic_page", "implementation")
        result = decide_candidates(
            task,
            [
                candidate("unavailable", "Unavailable MCP result", "react_bits", "effect", availability="unavailable"),
                candidate("wrong-stack", "React-only component", "react_bits", "effect", stack_compatibility="incompatible"),
                candidate("unknown-license", "Unknown license component", "external_component", "effect", license_status="unknown"),
                {
                    "candidate_id": "incomplete",
                    "candidate_name": "Incomplete candidate",
                    "source_type": "external_component",
                    "category": "effect",
                },
                candidate("light-custom", "Lightweight custom effect", "custom_build", "effect"),
            ],
        )
        decisions = {item["candidate_id"]: item for item in result["adoption_decisions"]}
        self.assertEqual(decisions["unavailable"]["recommended_action"], "defer")
        self.assertEqual(decisions["wrong-stack"]["recommended_action"], "reject")
        self.assertEqual(decisions["unknown-license"]["recommended_action"], "defer")
        self.assertEqual(decisions["incomplete"]["recommended_action"], "defer")
        self.assertEqual(decisions["incomplete"]["confidence"], "low")
        self.assertEqual(decisions["light-custom"]["recommended_action"], "custom_build")
        self.assertEqual(result["category_recommendations"][0]["candidate_id"], "light-custom")
        self.assertTrue(
            set(REQUIRED_CANDIDATE_FIELDS).issubset(result["component_candidates"][0])
        )


if __name__ == "__main__":
    unittest.main()
