from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from search_motionsites import search  # noqa: E402


def rejected_expressive_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "react-signature-hero",
        "candidate_name": "Signature React hero",
        "source_type": "react_bits",
        "category": "expressive_visual",
        "problem_fit": "strong",
        "product_fit": "strong",
        "brand_fit": "strong",
        "stack_compatibility": "incompatible",
        "availability": "available",
        "evidence_level": "verified",
        "accessibility_risk": "low",
        "performance_cost": "medium",
        "dependency_cost": "medium",
        "customization_cost": "medium",
        "maintenance_cost": "medium",
        "license_status": "compatible",
        "design_system_fit": "adaptable",
        "responsive_support": "adequate",
    }


class WorkflowTests(unittest.TestCase):
    def test_standard_settings_skips_creative_sources_and_prototype(self) -> None:
        result = search(
            "请帮我修改设置页的表单层级、按钮优先级和保存反馈",
            project_facts="React TypeScript with an existing design system",
            task_mode="implementation",
        )
        task = result["decision_task"]
        self.assertEqual(task["schema_version"], "3.0")
        self.assertEqual(task["upgrade_track"], "standard")
        self.assertFalse(task["creative_reference_needed"])
        self.assertFalse(task["prototype_required"])
        self.assertEqual(task["prototype_gate"]["status"], "not_required")
        self.assertTrue(task["implementation_permissions"]["full_integration"])
        self.assertFalse(task["react_bits_search_recommended"])
        self.assertEqual(task["motionsites_candidates"], [])
        for legacy in ("mode", "react_bits_needed", "external_effect_queries", "top_cases"):
            self.assertNotIn(legacy, result)

    def test_experimental_implementation_stops_at_isolated_prototype(self) -> None:
        result = search(
            "请直接实现一个沉浸式数字艺术作品集强视觉原型，使用滚动和空间变化",
            project_facts="React TypeScript; existing motion utilities; no new dependencies",
            task_mode="implementation",
        )
        task = result["decision_task"]
        self.assertEqual(task["upgrade_track"], "experimental")
        self.assertTrue(task["prototype_required"])
        self.assertEqual(task["prototype_gate"]["status"], "not_started")
        self.assertTrue(task["prototype_gate"]["full_integration_blocked"])
        self.assertTrue(task["implementation_permissions"]["prototype_changes"])
        self.assertFalse(task["implementation_permissions"]["full_integration"])
        self.assertFalse(task["implementation_permissions"]["install_components"])
        self.assertEqual(task["verification_plan"]["stage"], "prototype_minimum")
        self.assertGreaterEqual(len(task["motionsites_candidates"]), 1)
        self.assertLessEqual(len(task["motionsites_candidates"]), 3)
        mechanism = task["creative_mechanism"]
        self.assertIsNotNone(mechanism)
        self.assertGreaterEqual(len(mechanism["key_states"]), 3)
        self.assertTrue(mechanism["implementation_primitives"])
        self.assertIn("five seconds", mechanism["five_second_difference_target"])

    def test_approved_experimental_prototype_unlocks_integration(self) -> None:
        result = search(
            "原型已通过，请整合这个沉浸式视觉实验",
            project_facts="React TypeScript",
            task_mode="implementation",
            upgrade_track="experimental",
            prototype_status="approved",
        )
        task = result["decision_task"]
        self.assertFalse(task["prototype_gate"]["full_integration_blocked"])
        self.assertTrue(task["implementation_permissions"]["full_integration"])
        self.assertTrue(task["implementation_permissions"]["install_components"])
        self.assertEqual(task["verification_plan"]["stage"], "integration_targeted")

    def test_rejected_expressive_candidate_gets_custom_equivalent(self) -> None:
        result = search(
            "为作品集设计沉浸式强视觉 hero 和标志性动效",
            project_facts="Vue 3; no React runtime",
            task_mode="proposal",
            component_candidates=[rejected_expressive_candidate()],
            upgrade_track="experimental",
        )
        task = result["decision_task"]
        fallbacks = result["visual_equivalence_fallbacks"]
        self.assertTrue(fallbacks)
        self.assertEqual(fallbacks[0]["required_action"], "prototype_custom_equivalent")
        self.assertTrue(fallbacks[0]["downgrade_requires_approval"])
        self.assertEqual(fallbacks[0]["custom_mechanism"], task["creative_mechanism"])


if __name__ == "__main__":
    unittest.main()
