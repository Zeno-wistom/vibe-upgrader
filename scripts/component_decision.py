#!/usr/bin/env python3
"""Source-neutral component candidate protocol and decision engine.

The engine compares supplied evidence only. It never queries MCP, installs a
component, changes a project, or treats a discovered candidate as adopted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SOURCE_TYPES = {
    "existing_project",
    "existing_design_system",
    "foundation_ui",
    "react_bits",
    "external_component",
    "custom_build",
}
RECOMMENDED_ACTIONS = {"reuse", "adapt", "install", "custom_build", "reject", "defer"}
FIT_LEVELS = {"unknown", "none", "weak", "moderate", "strong"}
STACK_LEVELS = {"unknown", "incompatible", "partial", "compatible", "not_applicable"}
AVAILABILITY_LEVELS = {"unknown", "unavailable", "available", "not_applicable"}
EVIDENCE_LEVELS = {"unknown", "inferred", "reported", "documented", "verified"}
RISK_LEVELS = {"unknown", "low", "medium", "high", "unacceptable", "not_applicable"}
COST_LEVELS = {"unknown", "low", "medium", "high", "unacceptable", "not_applicable"}
LICENSE_LEVELS = {"unknown", "incompatible", "restricted", "compatible", "not_applicable"}
SYSTEM_FIT_LEVELS = {"unknown", "conflict", "adaptable", "compatible", "not_applicable"}
RESPONSIVE_LEVELS = {"unknown", "weak", "adequate", "strong", "not_applicable"}
FIELD_EVIDENCE_LEVELS = {"unknown", "inference", "reported_fact", "verified_fact"}

REQUIRED_CANDIDATE_FIELDS = [
    "candidate_id",
    "candidate_name",
    "source_type",
    "category",
    "query_origin",
    "problem_fit",
    "product_fit",
    "brand_fit",
    "stack_compatibility",
    "availability",
    "evidence_level",
    "accessibility_risk",
    "performance_cost",
    "dependency_cost",
    "customization_cost",
    "maintenance_cost",
    "license_status",
    "design_system_fit",
    "responsive_support",
    "recommended_action",
    "confidence",
    "adoption_reasons",
    "rejection_reasons",
]

ENUM_FIELDS = {
    "problem_fit": FIT_LEVELS,
    "product_fit": FIT_LEVELS,
    "brand_fit": FIT_LEVELS,
    "stack_compatibility": STACK_LEVELS,
    "availability": AVAILABILITY_LEVELS,
    "evidence_level": EVIDENCE_LEVELS,
    "accessibility_risk": RISK_LEVELS,
    "performance_cost": RISK_LEVELS,
    "dependency_cost": COST_LEVELS,
    "customization_cost": COST_LEVELS,
    "maintenance_cost": COST_LEVELS,
    "license_status": LICENSE_LEVELS,
    "design_system_fit": SYSTEM_FIT_LEVELS,
    "responsive_support": RESPONSIVE_LEVELS,
}

DEFAULTS: dict[str, Any] = {
    "candidate_name": "Unnamed candidate",
    "source_type": "external_component",
    "category": "unknown",
    "query_origin": {"request_id": "unknown", "method": "manual", "query": ""},
    "problem_fit": "unknown",
    "product_fit": "unknown",
    "brand_fit": "unknown",
    "stack_compatibility": "unknown",
    "availability": "unknown",
    "evidence_level": "unknown",
    "accessibility_risk": "unknown",
    "performance_cost": "unknown",
    "dependency_cost": "unknown",
    "customization_cost": "unknown",
    "maintenance_cost": "unknown",
    "license_status": "unknown",
    "design_system_fit": "unknown",
    "responsive_support": "unknown",
    "recommended_action": "defer",
    "confidence": "low",
    "adoption_reasons": [],
    "rejection_reasons": [],
    "field_evidence": {},
    "notes": [],
}

FIT_RANK = {"unknown": 0, "none": 0, "weak": 1, "moderate": 2, "strong": 3}
EVIDENCE_RANK = {"unknown": 0, "inferred": 1, "reported": 2, "documented": 3, "verified": 4}
RISK_RANK = {"not_applicable": 0, "low": 0, "medium": 1, "unknown": 2, "high": 3, "unacceptable": 4}
COST_RANK = {"not_applicable": 0, "low": 0, "medium": 1, "unknown": 2, "high": 3, "unacceptable": 4}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "candidate"


def _candidate_id(raw: dict[str, Any]) -> str:
    if raw.get("candidate_id"):
        return str(raw["candidate_id"])
    basis = "|".join(
        str(raw.get(key) or "") for key in ("source_type", "candidate_name", "category")
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]
    return f"{_slug(str(raw.get('candidate_name') or 'candidate'))}-{digest}"


def _enum_value(field: str, value: Any, issues: list[str]) -> str:
    text = str(value or "unknown")
    allowed = ENUM_FIELDS[field]
    if text not in allowed:
        issues.append(f"Invalid {field}={text!r}; normalized to 'unknown'.")
        return "unknown"
    return text


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize incomplete or mixed-source input without inventing safety facts."""
    if not isinstance(raw, dict):
        raise TypeError("Each component candidate must be a JSON object.")

    issues: list[str] = []
    candidate = {key: value for key, value in DEFAULTS.items()}
    candidate.update(raw)
    candidate["candidate_id"] = _candidate_id(raw)

    source_type = str(candidate.get("source_type") or "external_component")
    if source_type not in SOURCE_TYPES:
        issues.append(f"Invalid source_type={source_type!r}; normalized to 'external_component'.")
        source_type = "external_component"
    candidate["source_type"] = source_type

    for field in ENUM_FIELDS:
        candidate[field] = _enum_value(field, candidate.get(field), issues)

    action = str(candidate.get("recommended_action") or "defer")
    if action not in RECOMMENDED_ACTIONS:
        issues.append(f"Invalid recommended_action={action!r}; normalized to 'defer'.")
        action = "defer"
    candidate["recommended_action"] = action

    if not isinstance(candidate.get("query_origin"), dict):
        candidate["query_origin"] = {
            "request_id": "unknown",
            "method": "manual",
            "query": str(candidate.get("query_origin") or ""),
        }

    for field in ("adoption_reasons", "rejection_reasons", "notes"):
        value = candidate.get(field)
        if not isinstance(value, list):
            candidate[field] = [str(value)] if value else []

    raw_field_evidence = candidate.get("field_evidence")
    if not isinstance(raw_field_evidence, dict):
        raw_field_evidence = {}
    field_evidence: dict[str, str] = {
        str(field): str(status)
        for field, status in raw_field_evidence.items()
        if str(status) in FIELD_EVIDENCE_LEVELS
    }
    for field in REQUIRED_CANDIDATE_FIELDS:
        status = str(raw_field_evidence.get(field) or "")
        if status not in FIELD_EVIDENCE_LEVELS:
            value = candidate.get(field)
            status = "unknown" if value is None or value == "" or value == "unknown" else "reported_fact"
        field_evidence[field] = status
    candidate["field_evidence"] = field_evidence
    candidate["protocol_issues"] = issues
    return candidate


def build_candidate_requests(decision_task: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn stage-4 opportunities into unresolved, source-neutral requests."""
    preferred = {
        item.get("source")
        for item in decision_task.get("preferred_sources", [])
        if isinstance(item, dict)
    }
    preferred.update({"current_project_components", "current_project_context"})
    source_map = {
        "current_project_components": "existing_project",
        "foundation_ui": "foundation_ui",
        "react_bits": "react_bits",
        "custom_build": "custom_build",
    }
    allowed = {source_map[source] for source in preferred if source in source_map}
    allowed.update({"existing_project", "existing_design_system"})

    queries_by_source = {
        "foundation_ui": list(decision_task.get("foundation_ui_queries") or []),
        "react_bits": list(decision_task.get("react_bits_queries") or []),
    }
    requests: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for opportunity_index, opportunity in enumerate(decision_task.get("component_opportunities") or [], start=1):
        if not isinstance(opportunity, dict):
            continue
        categories = opportunity.get("candidate_categories") or [opportunity.get("area") or "unknown"]
        biases = [source_map.get(source, source) for source in opportunity.get("source_bias") or []]
        sources = [source for source in biases if source in allowed]
        for always_source in ("existing_project", "existing_design_system"):
            if always_source not in sources:
                sources.insert(0, always_source)
        if "custom_build" in allowed and "custom_build" not in sources:
            sources.append("custom_build")

        category_list = [str(category) for category in categories]
        request_category = str(opportunity.get("area") or category_list[0])
        for source_type in sources:
            if source_type not in SOURCE_TYPES:
                source_type = "external_component"
            source_queries = queries_by_source.get(source_type) or [str(opportunity.get("problem") or "")]
            query = next((str(item) for item in source_queries if item), "")
            key = (source_type, request_category, query)
            if key in seen:
                continue
            seen.add(key)
            requests.append(
                {
                    "request_id": f"cr-{opportunity_index:02d}-{len(requests) + 1:03d}",
                    "source_type": source_type,
                    "category": request_category,
                    "categories": category_list,
                    "problem": str(opportunity.get("problem") or ""),
                    "query": query,
                    "query_origin": "decision_task",
                    "task_mode": decision_task.get("task_mode", "analysis"),
                    "required_candidate_fields": REQUIRED_CANDIDATE_FIELDS,
                    "status": "pending",
                }
            )
    return requests


def _gate(name: str, status: str, effect: str, reason: str) -> dict[str, str]:
    return {"gate": name, "status": status, "effect": effect, "reason": reason}


def evaluate_hard_gates(candidate: dict[str, Any], decision_task: dict[str, Any]) -> list[dict[str, str]]:
    gates: list[dict[str, str]] = []
    external = candidate["source_type"] in {"foundation_ui", "react_bits", "external_component"}

    stack = candidate["stack_compatibility"]
    if stack == "incompatible":
        gates.append(_gate("stack", "fail", "reject", "The candidate is incompatible with the target stack."))
    elif stack == "unknown" and external:
        gates.append(_gate("stack", "unknown", "defer", "Stack compatibility is unknown for an external candidate."))
    else:
        gates.append(_gate("stack", "pass", "none", "No blocking stack conflict is reported."))

    availability = candidate["availability"]
    if availability == "unavailable":
        gates.append(_gate("availability", "fail", "defer", "The candidate is currently unavailable."))
    elif availability == "unknown" and external:
        gates.append(_gate("availability", "unknown", "defer", "Candidate availability has not been verified."))
    else:
        gates.append(_gate("availability", "pass", "none", "The candidate is available or availability is not applicable."))

    license_status = candidate["license_status"]
    if license_status == "incompatible":
        gates.append(_gate("license", "fail", "reject", "The reported license is incompatible with the project."))
    elif license_status == "restricted":
        gates.append(_gate("license", "fail", "defer", "License restrictions require human confirmation."))
    elif license_status == "unknown" and external:
        gates.append(_gate("license", "unknown", "defer", "License status is unknown and cannot be treated as safe."))
    else:
        gates.append(_gate("license", "pass", "none", "No blocking license issue is reported."))

    if candidate["problem_fit"] == "none" or candidate["product_fit"] == "none":
        gates.append(_gate("task_fit", "fail", "reject", "The candidate does not fit the diagnosed problem or product task."))
    elif candidate["problem_fit"] == "unknown" or candidate["product_fit"] == "unknown":
        gates.append(_gate("task_fit", "unknown", "defer", "Critical task-fit information is missing."))
    else:
        gates.append(_gate("task_fit", "pass", "none", "The candidate has a stated problem and product fit."))

    system_fit = candidate["design_system_fit"]
    if system_fit == "conflict" and external:
        gates.append(_gate("design_system", "fail", "reject", "The external candidate would introduce a conflicting visual or interaction system."))
    elif system_fit == "conflict":
        gates.append(_gate("design_system", "fail", "adapt_required", "The existing candidate must be adapted before reuse."))
    elif system_fit == "unknown" and external:
        gates.append(_gate("design_system", "unknown", "defer", "Design-system compatibility is not known."))
    else:
        gates.append(_gate("design_system", "pass", "none", "No blocking design-system conflict is reported."))

    accessibility = candidate["accessibility_risk"]
    if accessibility == "unacceptable":
        gates.append(_gate("accessibility", "fail", "reject", "Accessibility risk is unacceptable."))
    elif accessibility == "high":
        gates.append(_gate("accessibility", "fail", "adapt_required", "Accessibility remediation is required before adoption."))
    elif accessibility == "unknown" and external:
        gates.append(_gate("accessibility", "unknown", "defer", "Accessibility risk has not been assessed."))
    else:
        gates.append(_gate("accessibility", "pass", "none", "No blocking accessibility risk is reported."))

    performance = candidate["performance_cost"]
    if performance == "unacceptable":
        gates.append(_gate("performance", "fail", "reject", "Performance cost is unacceptable."))
    elif performance == "high":
        gates.append(_gate("performance", "fail", "adapt_required", "A lighter or degraded variant is required."))
    elif performance == "unknown" and external:
        gates.append(_gate("performance", "unknown", "defer", "Performance cost is unknown."))
    else:
        gates.append(_gate("performance", "pass", "none", "No blocking performance cost is reported."))

    dependency = candidate["dependency_cost"]
    if dependency == "unacceptable":
        gates.append(_gate("dependency_value", "fail", "reject", "Dependency cost is unacceptable for the value provided."))
    elif dependency == "high" and candidate["problem_fit"] != "strong":
        gates.append(_gate("dependency_value", "fail", "reject", "High dependency cost is not justified by the problem fit."))
    elif dependency == "high":
        gates.append(_gate("dependency_value", "fail", "defer", "High dependency cost requires explicit value confirmation."))
    elif dependency == "unknown" and external:
        gates.append(_gate("dependency_value", "unknown", "defer", "Dependency cost is unknown."))
    else:
        gates.append(_gate("dependency_value", "pass", "none", "Dependency cost is proportionate or not applicable."))

    task_mode = decision_task.get("task_mode", "analysis")
    if task_mode in {"analysis", "proposal"}:
        gates.append(_gate("permission", "blocked", "execution_blocked", f"{task_mode} mode permits recommendations but not project changes."))
    else:
        permissions = decision_task.get("implementation_permissions") or {}
        if not permissions.get("modify_files", False):
            gates.append(_gate("permission", "blocked", "execution_blocked", "Implementation permission is not available."))
        elif candidate["source_type"] in {"foundation_ui", "react_bits", "external_component"} and not permissions.get("install_components", False):
            gates.append(_gate("permission", "blocked", "execution_blocked", "External component installation is blocked until the prototype gate permits integration."))
        elif decision_task.get("prototype_required") and (decision_task.get("prototype_gate") or {}).get("status") != "approved":
            if permissions.get("prototype_changes", False):
                gates.append(_gate("prototype_scope", "limited", "prototype_only", "The candidate may be used only inside the isolated prototype surface before human approval."))
            else:
                gates.append(_gate("prototype_scope", "blocked", "execution_blocked", "The prototype gate blocks integration until human approval."))
        else:
            gates.append(_gate("permission", "pass", "none", "The mode permits later execution after explicit authorization."))
    return gates


def _base_action(source_type: str) -> str:
    if source_type in {"existing_project", "existing_design_system"}:
        return "reuse"
    if source_type == "custom_build":
        return "custom_build"
    return "install"


def _confidence(candidate: dict[str, Any], gates: list[dict[str, str]]) -> str:
    if any(gate["status"] == "unknown" for gate in gates):
        return "low"
    evidence = candidate["evidence_level"]
    if evidence in {"verified", "documented"} and not candidate["protocol_issues"]:
        return "high"
    if evidence in {"reported", "inferred"}:
        return "medium"
    return "low"


def decide_candidate(raw: dict[str, Any], decision_task: dict[str, Any]) -> dict[str, Any]:
    candidate = normalize_candidate(raw)
    gates = evaluate_hard_gates(candidate, decision_task)
    effects = {gate["effect"] for gate in gates}
    adoption_reasons = list(candidate["adoption_reasons"])
    rejection_reasons = list(candidate["rejection_reasons"])
    required_followups: list[str] = []

    if "reject" in effects:
        action = "reject"
    elif "defer" in effects:
        action = "defer"
    elif "adapt_required" in effects:
        action = "adapt" if candidate["source_type"] != "custom_build" else "custom_build"
    elif candidate["problem_fit"] == "weak":
        action = "reject"
        rejection_reasons.append("The candidate addresses the problem too weakly to justify adoption.")
    else:
        action = _base_action(candidate["source_type"])
        if action == "reuse" and (
            candidate["brand_fit"] == "weak"
            or candidate["stack_compatibility"] == "partial"
            or candidate["design_system_fit"] == "adaptable"
        ):
            action = "adapt"
        elif action == "install" and candidate["brand_fit"] == "weak":
            action = "adapt"
        if candidate["customization_cost"] == "high" and candidate["problem_fit"] != "strong":
            action = "defer"
            required_followups.append("Confirm that customization value justifies its high cost.")
        if candidate["maintenance_cost"] == "high" and candidate["problem_fit"] != "strong":
            action = "defer"
            required_followups.append("Confirm a maintenance owner before adoption.")

    for gate in gates:
        if gate["effect"] in {"reject", "defer"}:
            rejection_reasons.append(gate["reason"])
        elif gate["effect"] == "adapt_required":
            required_followups.append(gate["reason"])

    if action in {"reuse", "adapt", "install", "custom_build"}:
        adoption_reasons.extend(
            [
                f"Problem fit is {candidate['problem_fit']} and product fit is {candidate['product_fit']}.",
                f"The source-specific path is {action}; discovery alone was not treated as adoption.",
            ]
        )

    execution_status = "allowed_after_authorization"
    if "execution_blocked" in effects:
        execution_status = "recommendation_only"
    elif "prototype_only" in effects:
        execution_status = "prototype_only"
    if action in {"reject", "defer"}:
        execution_status = "not_actionable"

    confidence = _confidence(candidate, gates)
    candidate["recommended_action"] = action
    candidate["confidence"] = confidence
    candidate["adoption_reasons"] = list(dict.fromkeys(adoption_reasons))
    candidate["rejection_reasons"] = list(dict.fromkeys(rejection_reasons))

    decision_status = "rejected" if action == "reject" else "deferred" if action == "defer" else "conditional" if "adapt_required" in effects else "recommended"

    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_name": candidate["candidate_name"],
        "source_type": candidate["source_type"],
        "category": candidate["category"],
        "recommended_action": action,
        "decision_status": decision_status,
        "execution_status": execution_status,
        "confidence": confidence,
        "hard_gates": gates,
        "comparison_factors": {
            "problem_fit": candidate["problem_fit"],
            "product_fit": candidate["product_fit"],
            "brand_fit": candidate["brand_fit"],
            "responsive_support": candidate["responsive_support"],
            "accessibility_risk": candidate["accessibility_risk"],
            "performance_cost": candidate["performance_cost"],
            "dependency_cost": candidate["dependency_cost"],
            "customization_cost": candidate["customization_cost"],
            "maintenance_cost": candidate["maintenance_cost"],
            "evidence_level": candidate["evidence_level"],
        },
        "adoption_reasons": candidate["adoption_reasons"],
        "rejection_reasons": candidate["rejection_reasons"],
        "required_followups": list(dict.fromkeys(required_followups)),
        "normalized_candidate": candidate,
    }


def _source_preference(source_type: str, page_type: str, category: str) -> int:
    expressive = category in {"hero", "text", "background", "brand_motion", "image_display", "card_interaction"}
    if page_type in {"enterprise_admin", "settings", "dashboard", "form_flow"}:
        order = {
            "existing_design_system": 6,
            "existing_project": 5,
            "foundation_ui": 4,
            "custom_build": 3,
            "react_bits": 2,
            "external_component": 1,
        }
    elif expressive and page_type in {"marketing_homepage", "landing_page", "product_page", "portfolio"}:
        order = {
            "custom_build": 6,
            "react_bits": 5,
            "existing_project": 4,
            "existing_design_system": 3,
            "foundation_ui": 2,
            "external_component": 1,
        }
    else:
        order = {
            "existing_project": 6,
            "existing_design_system": 5,
            "foundation_ui": 4,
            "custom_build": 3,
            "react_bits": 2,
            "external_component": 1,
        }
    return order.get(source_type, 0)


def _selection_key(decision: dict[str, Any], page_type: str) -> tuple[int, ...]:
    factors = decision["comparison_factors"]
    return (
        FIT_RANK[factors["problem_fit"]],
        FIT_RANK[factors["product_fit"]],
        FIT_RANK[factors["brand_fit"]],
        -RISK_RANK[factors["accessibility_risk"]],
        -RISK_RANK[factors["performance_cost"]],
        -COST_RANK[factors["dependency_cost"]],
        -COST_RANK[factors["maintenance_cost"]],
        EVIDENCE_RANK[factors["evidence_level"]],
        _source_preference(decision["source_type"], page_type, decision["category"]),
    )


def select_category_recommendations(
    decisions: list[dict[str, Any]], decision_task: dict[str, Any]
) -> list[dict[str, Any]]:
    """Select without a composite score: fit first, then risk/cost, then context."""
    page_type = str(decision_task.get("page_type") or "generic_page")
    categories = sorted({decision["category"] for decision in decisions})
    recommendations: list[dict[str, Any]] = []
    for category in categories:
        recommended = [
            decision
            for decision in decisions
            if decision["category"] == category
            and decision["decision_status"] == "recommended"
        ]
        conditional = [
            decision
            for decision in decisions
            if decision["category"] == category
            and decision["decision_status"] == "conditional"
        ]
        eligible = recommended or conditional
        if not eligible:
            recommendations.append(
                {
                    "category": category,
                    "candidate_id": None,
                    "recommended_action": "defer",
                    "reason": "No candidate in this category passed the hard gates.",
                }
            )
            continue
        winner = max(eligible, key=lambda item: _selection_key(item, page_type))
        recommendations.append(
            {
                "category": category,
                "candidate_id": winner["candidate_id"],
                "candidate_name": winner["candidate_name"],
                "recommended_action": winner["recommended_action"],
                "reason": "Selected by ordered comparison: problem and product fit, brand fit, risk and cost, evidence, then page-context source preference.",
            }
        )
    return recommendations


EXPRESSIVE_CATEGORIES = {
    "expressive_visual",
    "brand_motion",
    "hero",
    "text",
    "background",
    "image_display",
    "card_interaction",
    "effect",
}


def build_visual_equivalence_fallbacks(
    decisions: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    decision_task: dict[str, Any],
) -> list[dict[str, Any]]:
    if decision_task.get("upgrade_track") != "experimental":
        return []

    requested = {
        str(item.get("area") or "")
        for item in decision_task.get("component_opportunities") or []
        if isinstance(item, dict) and str(item.get("area") or "") == "expressive_visual"
    }
    requested.update(
        decision["category"]
        for decision in decisions
        if decision["category"] in EXPRESSIVE_CATEGORIES
    )
    winner_by_category = {item["category"]: item for item in recommendations}
    fallback: list[dict[str, Any]] = []
    for category in sorted(requested):
        winner = winner_by_category.get(category)
        if winner and winner.get("candidate_id"):
            winning_decision = next(
                (item for item in decisions if item["candidate_id"] == winner["candidate_id"]),
                None,
            )
            if winning_decision and winning_decision["source_type"] == "custom_build":
                continue
        category_decisions = [item for item in decisions if item["category"] == category]
        if category_decisions and not any(item["decision_status"] in {"rejected", "deferred"} for item in category_decisions):
            continue
        mechanism = decision_task.get("creative_mechanism")
        fallback.append(
            {
                "category": category,
                "status": "human_confirmation_required",
                "required_action": "prototype_custom_equivalent",
                "reason": "No external expressive candidate safely preserves the requested visual ambition.",
                "custom_mechanism": mechanism or {
                    "name": f"custom {category} mechanism",
                    "target_surface": category,
                    "five_second_difference_target": "Preserve the requested expressive role with a clearly observable structural or interaction change.",
                },
                "downgrade_requires_approval": True,
            }
        )
    return fallback


def decide_candidates(decision_task: dict[str, Any], raw_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [decide_candidate(raw, decision_task) for raw in raw_candidates]
    category_recommendations = select_category_recommendations(decisions, decision_task)
    visual_equivalence_fallbacks = build_visual_equivalence_fallbacks(
        decisions, category_recommendations, decision_task
    )
    return {
        "schema_version": "2.0",
        "candidate_protocol_version": "1.0",
        "candidate_requests": build_candidate_requests(decision_task),
        "component_candidates": [decision["normalized_candidate"] for decision in decisions],
        "adoption_decisions": [
            {key: value for key, value in decision.items() if key != "normalized_candidate"}
            for decision in decisions
        ],
        "category_recommendations": category_recommendations,
        "visual_equivalence_fallbacks": visual_equivalence_fallbacks,
        "recommended_candidate_ids": [
            item["candidate_id"] for item in category_recommendations if item["candidate_id"]
        ],
        "selection_policy": [
            "Apply hard gates before comparison.",
            "Compare problem and product fit before brand fit.",
            "When fit is comparable, prefer lower accessibility, performance, dependency, and maintenance risk.",
            "Use page context as a final source preference, not a mechanical global order.",
            "Permission mode controls execution, not whether analysis may recommend an action.",
            "Experimental expressive gaps require a custom equivalent or explicit approval to reduce ambition.",
        ],
    }


def load_decision_task(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("decision_task"), dict):
        return payload["decision_task"]
    if not isinstance(payload, dict):
        raise ValueError("Decision task input must be a JSON object.")
    return payload


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("component_candidates")
    if not isinstance(payload, list):
        raise ValueError("Candidate input must be a JSON list or an object with component_candidates.")
    return payload


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Compare supplied component candidates without querying or installing them.")
    parser.add_argument("--decision-task", required=True, help="UTF-8 JSON file containing decision_task or the full stage-4 output.")
    parser.add_argument("--candidates", required=True, help="UTF-8 JSON list or object containing component_candidates.")
    args = parser.parse_args(argv)

    result = decide_candidates(
        load_decision_task(Path(args.decision_task)),
        load_candidates(Path(args.candidates)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
