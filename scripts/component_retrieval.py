#!/usr/bin/env python3
"""Read-only component retrieval and normalization for Vibe Upgrader.

Codex calls an available MCP tool and may pass its raw result to this adapter.
This module does not pretend to be a Codex MCP client. It can instead use the
read-only shadcn CLI or public Registry metadata as explicit fallbacks. It
never runs ``shadcn add`` and never writes to a target project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Direct CLI execution imports component_decision from the installed Skill.
# Keep that import read-only even when the caller omits Python's -B flag.
sys.dont_write_bytecode = True

from component_decision import decide_candidates


RETRIEVAL_METHODS = {"mcp", "cli", "registry_http", "fixture", "prefilter"}
REGISTRIES = {
    "foundation_ui": {
        "namespace": "@shadcn",
        "search_target": "@shadcn",
        "index_url": "https://ui.shadcn.com/r/index.json",
        "item_url": "@shadcn/{name}",
    },
    "react_bits": {
        "namespace": "@react-bits",
        "search_target": "https://reactbits.dev/r/registry.json",
        "index_url": "https://reactbits.dev/r/registry.json",
        "item_url": "https://reactbits.dev/r/{name}.json",
    },
}
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
WORD_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a", "an", "and", "for", "from", "in", "of", "or", "the", "to", "ui",
    "accessible", "component", "components", "interaction", "product", "state",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_ansi(value: str) -> str:
    return ANSI_RE.sub("", value).replace("\r", "")


def _json_from_output(value: str) -> Any:
    clean = _strip_ansi(value).strip()
    starts = [index for index in (clean.find("["), clean.find("{")) if index >= 0]
    if not starts:
        raise ValueError("CLI view output did not contain JSON.")
    return json.loads(clean[min(starts):])


def _items_from_payload(value: Any) -> list[dict[str, Any]]:
    """Extract Registry-like items without assuming one MCP response shape."""
    if isinstance(value, str):
        try:
            return _items_from_payload(json.loads(value))
        except json.JSONDecodeError:
            return []
    if isinstance(value, list):
        direct = [item for item in value if isinstance(item, dict) and item.get("name")]
        if direct:
            return direct
        items: list[dict[str, Any]] = []
        for item in value:
            items.extend(_items_from_payload(item))
        return items
    if not isinstance(value, dict):
        return []
    if value.get("name") and any(key in value for key in ("type", "files", "description")):
        return [value]
    for key in ("items", "raw_results", "components", "results", "result", "structuredContent", "content"):
        if key in value:
            items = _items_from_payload(value[key])
            if items:
                return items
    return []


def inspect_target_stack(target_root: Path | None, declared_facts: str = "") -> dict[str, Any]:
    """Read only the smallest common files needed to classify React compatibility."""
    evidence: list[str] = []
    package_data: dict[str, Any] = {}
    root = target_root.resolve() if target_root else None
    if root and (root / "package.json").is_file():
        try:
            package_data = _read_json(root / "package.json")
            evidence.append("package.json")
        except (OSError, json.JSONDecodeError):
            evidence.append("package.json:unreadable")
    if root and (root / "components.json").is_file():
        evidence.append("components.json")
    if root:
        for name in ("next.config.js", "next.config.mjs", "next.config.ts", "vite.config.js", "vite.config.ts"):
            if (root / name).is_file():
                evidence.append(name)

    dependencies: dict[str, Any] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package_data.get(key)
        if isinstance(value, dict):
            dependencies.update(value)
    names = {str(name).lower() for name in dependencies}
    facts = declared_facts.lower()
    react_signals = names & {"react", "react-dom", "next"}
    non_react_signals = names & {"vue", "svelte", "@angular/core", "solid-js", "preact"}
    if react_signals or re.search(r"\b(react|next\.js|nextjs)\b", facts):
        compatibility = "react_compatible"
        reason = "React compatibility is supported by the declared project facts or package metadata."
    elif non_react_signals or re.search(r"\b(vue|svelte|angular|solidjs|solid\.js)\b", facts):
        compatibility = "react_incompatible"
        reason = "A non-React framework is declared and no React dependency was found."
    else:
        compatibility = "unknown"
        reason = "The inspected files do not prove whether the target is React-compatible."
    return {
        "compatibility": compatibility,
        "reason": reason,
        "evidence_files": evidence,
        "react_dependencies": sorted(react_signals),
        "non_react_dependencies": sorted(non_react_signals),
    }


def _config_has_shadcn(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return bool(re.search(r"(?m)^\s*\[mcp_servers\.shadcn\]\s*$", path.read_text(encoding="utf-8")))
    except OSError:
        return False


def detect_runtime_capabilities(
    project_root: Path,
    attempts: list[dict[str, Any]] | None = None,
    mcp_available_in_session: bool = False,
) -> dict[str, Any]:
    attempts = attempts or []
    project_config = project_root / ".codex" / "config.toml"
    user_config = Path.home() / ".codex" / "config.toml"
    project_configured = _config_has_shadcn(project_config)
    user_configured = _config_has_shadcn(user_config)
    mcp_success = any(
        item.get("retrieval_method") == "mcp" and item.get("status") == "success"
        for item in attempts
    )
    cli_attempts = [item for item in attempts if item.get("retrieval_method") == "cli"]
    react_success = any(
        item.get("status") == "success"
        and item.get("registry_namespace") == "@react-bits"
        and item.get("retrieval_method") in {"mcp", "cli", "registry_http"}
        for item in attempts
    )
    configured = project_configured or user_configured
    available = bool(mcp_available_in_session or mcp_success)
    return {
        "shadcn_mcp": {
            "configured": configured,
            "configuration_scope": "project" if project_configured else "user" if user_configured else None,
            "available_in_session": available,
            "verified_by_call": mcp_success,
        },
        "react_bits_registry": {
            "discoverable": react_success,
            "verified_by_query": react_success,
        },
        "shadcn_cli": {
            "available": bool(shutil.which("npx")),
            "search_supported": any(item.get("search_succeeded") for item in cli_attempts),
            "view_supported": any(item.get("view_succeeded") for item in cli_attempts),
        },
        "restart_required": bool(configured and not available),
    }


def _variant(name: str, files: list[dict[str, Any]]) -> dict[str, str]:
    upper = name.upper()
    paths = " ".join(str(item.get("path") or "") for item in files).lower()
    language = "typescript" if "-TS-" in upper or ".tsx" in paths else "javascript" if "-JS-" in upper or ".jsx" in paths else "unknown"
    styling = "tailwind" if upper.endswith("-TW") else "css" if upper.endswith("-CSS") else "unknown"
    return {"language": language, "styling": styling}


def normalize_registry_item(
    item: dict[str, Any],
    request: dict[str, Any],
    attempt: dict[str, Any],
    stack_profile: dict[str, Any],
) -> dict[str, Any]:
    """Convert a real Registry item to the stage-5 source-neutral protocol."""
    source_type = str(request.get("source_type") or "external_component")
    name = str(item.get("name") or item.get("title") or "Unnamed registry item")
    files = [
        {"path": str(value.get("path") or ""), "type": str(value.get("type") or "")}
        for value in item.get("files") or []
        if isinstance(value, dict)
    ]
    registry = REGISTRIES.get(source_type, {})
    namespace = str(attempt.get("registry_namespace") or registry.get("namespace") or "")
    item_url = str(attempt.get("item_url") or registry.get("item_url", "")).format(name=name)
    compatibility = stack_profile.get("compatibility", "unknown")
    if source_type in {"foundation_ui", "react_bits"}:
        stack_value = {
            "react_compatible": "compatible",
            "react_incompatible": "incompatible",
            "unknown": "unknown",
        }.get(str(compatibility), "unknown")
    else:
        stack_value = "unknown"
    description = str(item.get("description") or "")
    query = str(attempt.get("query") or request.get("query") or "")
    problem_fit = "moderate" if attempt.get("status") == "success" else "unknown"
    raw_reference = str(attempt.get("raw_evidence_reference") or _sha(item))
    retrieved_at = str(attempt.get("retrieved_at") or _now())
    field_evidence = {
        "candidate_name": "verified_fact",
        "source_type": "verified_fact",
        "category": "reported_fact",
        "query_origin": "verified_fact",
        "problem_fit": "inference" if problem_fit != "unknown" else "unknown",
        "product_fit": "unknown",
        "brand_fit": "unknown",
        "stack_compatibility": "verified_fact" if stack_value != "unknown" else "unknown",
        "availability": "verified_fact",
        "evidence_level": "verified_fact",
        "accessibility_risk": "unknown",
        "performance_cost": "unknown",
        "dependency_cost": "unknown",
        "customization_cost": "unknown",
        "maintenance_cost": "unknown",
        "license_status": "unknown",
        "design_system_fit": "unknown",
        "responsive_support": "unknown",
        "recommended_action": "unknown",
        "confidence": "unknown",
        "adoption_reasons": "unknown",
        "rejection_reasons": "unknown",
        "retrieval_method": "verified_fact",
        "registry_namespace": "verified_fact",
        "registry_item": "verified_fact",
        "description": "verified_fact" if description else "unknown",
        "npm_dependencies": "verified_fact",
        "registry_dependencies": "verified_fact",
        "files": "verified_fact",
        "technology_variant": "verified_fact",
        "retrieved_at": "verified_fact",
        "raw_evidence_reference": "verified_fact",
    }
    return {
        "candidate_id": f"{source_type}:{name}",
        "candidate_name": str(item.get("title") or name),
        "source_type": source_type,
        "category": str(request.get("category") or item.get("type") or "unknown"),
        "query_origin": {
            "request_id": str(request.get("request_id") or "unknown"),
            "method": str(attempt.get("retrieval_method") or "unknown"),
            "query": query,
        },
        "problem_fit": problem_fit,
        "product_fit": "unknown",
        "brand_fit": "unknown",
        "stack_compatibility": stack_value,
        "availability": "available",
        "evidence_level": "verified",
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
        "field_evidence": field_evidence,
        "description": description,
        "registry_type": str(item.get("type") or "unknown"),
        "registry_namespace": namespace,
        "registry_item": name,
        "registry_item_reference": item_url,
        "npm_dependencies": [str(value) for value in item.get("dependencies") or []],
        "registry_dependencies": [str(value) for value in item.get("registryDependencies") or []],
        "files": files,
        "technology_variant": _variant(name, files),
        "retrieval_method": str(attempt.get("retrieval_method") or "unknown"),
        "query": query,
        "retrieved_at": retrieved_at,
        "raw_evidence_reference": raw_reference,
        "notes": [
            "Registry metadata verifies identity and declared files/dependencies only; fit and operational risks still require project evidence."
        ],
    }


def normalize_attempt(value: dict[str, Any], ordinal: int = 1) -> dict[str, Any]:
    attempt = dict(value)
    method = str(attempt.get("retrieval_method") or "fixture")
    if method not in RETRIEVAL_METHODS:
        method = "fixture"
    attempt["retrieval_method"] = method
    attempt.setdefault("attempt_id", f"attempt-{ordinal:03d}")
    attempt.setdefault("request_id", "unknown")
    attempt.setdefault("query", "")
    attempt.setdefault("registry_namespace", "")
    attempt.setdefault("retrieved_at", _now())
    items = _items_from_payload(attempt)
    attempt["status"] = str(attempt.get("status") or ("success" if items else "no_results"))
    attempt["result_count"] = len(items)
    attempt.setdefault("raw_evidence_reference", _sha(value))
    attempt["_items"] = items
    return attempt


def _search_tokens(query: str) -> set[str]:
    tokens = {token for token in WORD_RE.findall(query.lower()) if token not in STOP_WORDS}
    expanded = set(tokens)
    expanded.update(token[:-1] for token in tokens if len(token) > 4 and token.endswith("s"))
    return expanded


def _http_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "Vibe-Upgrader/1.0 read-only"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def retrieve_registry_http(request: dict[str, Any], limit: int = 3) -> dict[str, Any]:
    source_type = str(request.get("source_type") or "")
    registry = REGISTRIES[source_type]
    query = str(request.get("query") or request.get("category") or "")
    attempt: dict[str, Any] = {
        "attempt_id": f"{request.get('request_id', 'unknown')}-registry",
        "request_id": request.get("request_id", "unknown"),
        "retrieval_method": "registry_http",
        "registry_namespace": registry["namespace"],
        "query": query,
        "retrieved_at": _now(),
        "source_reference": registry["index_url"],
    }
    try:
        payload = _http_json(registry["index_url"])
        items = payload.get("items", []) if isinstance(payload, dict) else payload
        query_tokens = _search_tokens(query)
        ranked: list[tuple[int, dict[str, Any]]] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get(key) or "") for key in ("name", "title", "description")).lower()
            score = sum(1 for token in query_tokens if token in text)
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("name") or "")))
        selected = [item for _, item in ranked[:limit]]
        attempt.update({
            "status": "success" if selected else "no_results",
            "raw_results": selected,
            "result_count": len(selected),
            "raw_evidence_reference": _sha(payload),
        })
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        attempt.update({"status": "failed", "result_count": 0, "error": str(exc)})
    return attempt


def _default_cli_runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)


def retrieve_shadcn_cli(
    request: dict[str, Any],
    limit: int = 3,
    runner: Callable[[list[str], int], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    source_type = str(request.get("source_type") or "")
    registry = REGISTRIES[source_type]
    query = str(request.get("query") or request.get("category") or "")
    attempt: dict[str, Any] = {
        "attempt_id": f"{request.get('request_id', 'unknown')}-cli",
        "request_id": request.get("request_id", "unknown"),
        "retrieval_method": "cli",
        "registry_namespace": registry["namespace"],
        "query": query,
        "retrieved_at": _now(),
        "result_count": 0,
        "search_succeeded": False,
        "view_succeeded": False,
    }
    npx = shutil.which("npx")
    if not npx:
        attempt.update({"status": "unavailable", "error": "npx is not available."})
        return attempt
    call = runner or _default_cli_runner
    search_args = [npx, "--yes", "shadcn@latest", "search", registry["search_target"], "--query", query, "--limit", str(limit)]
    attempt["search_command"] = ["npx", "--yes", "shadcn@latest", "search", registry["search_target"], "--query", query, "--limit", str(limit)]
    try:
        searched = call(search_args, 60)
    except (OSError, subprocess.SubprocessError) as exc:
        attempt.update({"status": "failed", "error": str(exc)})
        return attempt
    search_output = _strip_ansi((searched.stdout or "") + "\n" + (searched.stderr or ""))
    attempt["search_succeeded"] = searched.returncode == 0
    if searched.returncode != 0:
        attempt.update({"status": "failed", "error": search_output.strip()[-500:]})
        return attempt
    item_refs: list[str] = []
    for line in search_output.splitlines():
        match = re.match(r"^\s*-\s+([^\s]+)\s+\(", line)
        if match:
            item_refs.append(match.group(1))
    items: list[dict[str, Any]] = []
    view_commands: list[list[str]] = []
    for item_ref in item_refs[:limit]:
        view_args = [npx, "--yes", "shadcn@latest", "view", item_ref]
        view_commands.append(["npx", "--yes", "shadcn@latest", "view", item_ref])
        try:
            viewed = call(view_args, 60)
            if viewed.returncode == 0:
                items.extend(_items_from_payload(_json_from_output(viewed.stdout or "")))
        except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
            continue
    attempt["view_commands"] = view_commands
    attempt["view_succeeded"] = bool(items)
    attempt["status"] = "success" if items else "no_results"
    attempt["result_count"] = len(items)
    attempt["raw_results"] = items
    attempt["raw_evidence_reference"] = _sha({"search": search_output, "items": items})
    return attempt


def _prefilter_attempt(request: dict[str, Any], stack_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt_id": f"{request.get('request_id', 'unknown')}-prefilter",
        "request_id": request.get("request_id", "unknown"),
        "retrieval_method": "prefilter",
        "registry_namespace": "@react-bits",
        "query": request.get("query", ""),
        "retrieved_at": _now(),
        "status": "skipped_incompatible",
        "result_count": 0,
        "rejection_reason": stack_profile.get("reason"),
        "raw_evidence_reference": _sha(stack_profile),
    }


def retrieve_components(
    decision_task: dict[str, Any],
    project_root: Path,
    target_root: Path | None = None,
    declared_stack_facts: str = "",
    raw_attempts: list[dict[str, Any]] | None = None,
    seed_candidates: list[dict[str, Any]] | None = None,
    enable_cli: bool = False,
    enable_registry_http: bool = False,
    mcp_available_in_session: bool = False,
    cli_runner: Callable[[list[str], int], subprocess.CompletedProcess[str]] | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    """Resolve external requests, normalize evidence, then call stage 5."""
    requests = [dict(item) for item in decision_task.get("candidate_requests") or [] if isinstance(item, dict)]
    stack_profile = inspect_target_stack(target_root, declared_stack_facts)
    attempts = [normalize_attempt(item, index) for index, item in enumerate(raw_attempts or [], start=1)]
    candidates = list(seed_candidates or [])
    resolved_request_ids: set[str] = set()

    def add_attempt(attempt_value: dict[str, Any], request: dict[str, Any]) -> None:
        attempt = normalize_attempt(attempt_value, len(attempts) + 1)
        attempts.append(attempt)
        if attempt["status"] == "success":
            for item in attempt["_items"]:
                candidates.append(normalize_registry_item(item, request, attempt, stack_profile))
            resolved_request_ids.add(str(request.get("request_id") or "unknown"))

    by_request: dict[str, list[dict[str, Any]]] = {}
    for attempt in list(attempts):
        by_request.setdefault(str(attempt.get("request_id") or "unknown"), []).append(attempt)

    for request in requests:
        request_id = str(request.get("request_id") or "unknown")
        source_type = str(request.get("source_type") or "")
        for attempt in by_request.get(request_id, []):
            if attempt["status"] == "success":
                for item in attempt["_items"]:
                    candidates.append(normalize_registry_item(item, request, attempt, stack_profile))
                resolved_request_ids.add(request_id)
        if source_type not in REGISTRIES or request_id in resolved_request_ids:
            continue
        if source_type == "react_bits" and stack_profile["compatibility"] == "react_incompatible":
            attempts.append(normalize_attempt(_prefilter_attempt(request, stack_profile), len(attempts) + 1))
            continue
        if enable_cli:
            add_attempt(retrieve_shadcn_cli(request, limit, cli_runner), request)
        if request_id not in resolved_request_ids and enable_registry_http:
            add_attempt(retrieve_registry_http(request, limit), request)

    public_attempts = [{key: value for key, value in item.items() if key not in {"_items", "raw_results"}} for item in attempts]
    unresolved = []
    for request in requests:
        copy = dict(request)
        request_id = str(copy.get("request_id") or "unknown")
        relevant = [item for item in public_attempts if str(item.get("request_id")) == request_id]
        copy["status"] = "resolved" if request_id in resolved_request_ids else "unresolved"
        copy["retrieval_attempt_ids"] = [str(item.get("attempt_id")) for item in relevant]
        if relevant and relevant[-1].get("rejection_reason"):
            copy["rejection_reason"] = relevant[-1]["rejection_reason"]
        unresolved.append(copy)

    decision_result = decide_candidates(decision_task, candidates)
    successful_methods = [
        item["retrieval_method"] for item in public_attempts
        if item.get("status") == "success" and item.get("retrieval_method") in {"mcp", "cli", "registry_http"}
    ]
    fallback_used: str | None = None
    if successful_methods and "mcp" not in successful_methods:
        fallback_used = "registry_http" if "registry_http" in successful_methods else "cli"
        if "cli" in successful_methods and "registry_http" in successful_methods:
            fallback_used = "cli_then_registry_http"
    runtime = detect_runtime_capabilities(project_root, public_attempts, mcp_available_in_session)
    return {
        "runtime_capabilities": runtime,
        "target_stack": stack_profile,
        "candidate_requests": unresolved,
        "retrieval_attempts": public_attempts,
        "component_candidates": decision_result["component_candidates"],
        "adoption_decisions": decision_result["adoption_decisions"],
        "category_recommendations": decision_result["category_recommendations"],
        "visual_equivalence_fallbacks": decision_result["visual_equivalence_fallbacks"],
        "fallback_used": fallback_used,
        "restart_required": runtime["restart_required"],
        "side_effects": [],
    }


def _load_task(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    if isinstance(value, dict) and isinstance(value.get("decision_task"), dict):
        return value["decision_task"]
    if not isinstance(value, dict):
        raise ValueError("Decision task JSON must be an object.")
    return value


def load_retrieval_attempts(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    value = _read_json(path)
    if isinstance(value, dict):
        value = value.get("retrieval_attempts", [value])
    if not isinstance(value, list):
        raise ValueError("Raw retrieval input must be a JSON object or array.")
    return [item for item in value if isinstance(item, dict)]


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Retrieve and normalize component candidates without installation.")
    parser.add_argument("--decision-task", required=True, help="UTF-8 JSON decision_task or full Vibe Upgrader output.")
    parser.add_argument("--raw-results", help="Optional MCP/CLI/Registry JSON captured by the calling agent.")
    parser.add_argument("--project-root", default=".", help="Vibe Upgrader project root for configuration detection.")
    parser.add_argument("--target-root", help="Target frontend root for minimal stack inspection.")
    parser.add_argument("--stack-facts", default="", help="Verified stack facts when no target files are available.")
    parser.add_argument("--use-cli", action="store_true", help="Allow read-only shadcn search/view fallback.")
    parser.add_argument("--allow-registry-http", action="store_true", help="Allow read-only public Registry index fallback.")
    parser.add_argument("--mcp-available-in-session", action="store_true", help="Set only after the calling Codex session can see the shadcn MCP tools.")
    parser.add_argument("--limit", type=int, default=3, help="Maximum candidates viewed per request. Default: 3.")
    args = parser.parse_args(argv)
    task = _load_task(Path(args.decision_task))
    result = retrieve_components(
        task,
        Path(args.project_root),
        Path(args.target_root) if args.target_root else None,
        args.stack_facts,
        load_retrieval_attempts(Path(args.raw_results)) if args.raw_results else None,
        enable_cli=args.use_cli,
        enable_registry_http=args.allow_registry_http,
        mcp_available_in_session=args.mcp_available_in_session,
        limit=max(1, min(args.limit, 10)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
