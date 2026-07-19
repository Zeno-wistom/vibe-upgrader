#!/usr/bin/env python3
"""Build a Vibe Upgrader task and connect optional read-only retrieval.

The helper never calls Codex MCP directly or installs components. When the
caller opts in, it delegates minimal stack inspection and CLI/Registry access
to component_retrieval before handing candidates to the decision engine.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# The installed Skill is immutable at runtime. Set this before importing sibling
# helpers so direct CLI execution cannot create scripts/__pycache__.
sys.dont_write_bytecode = True

from component_decision import build_candidate_requests, load_candidates
from component_retrieval import load_retrieval_attempts, retrieve_components


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
DATA_PATH = ASSETS_DIR / "enriched_cleaned_motionsites_prompts.jsonl"
ALIASES_PATH = ASSETS_DIR / "taxonomy_aliases.json"
REACT_BITS_ALIASES_PATH = ASSETS_DIR / "react_bits_aliases.json"


SOURCE_SCORES = {
    "original_public": 1.0,
    "archive_public": 0.85,
    "generated_reference": 0.45,
    "locked_metadata_only": 0.25,
}


CHINESE_KEYWORDS = {
    "高级",
    "高级感",
    "质感",
    "精致",
    "科技",
    "科技感",
    "未来感",
    "液态玻璃",
    "玻璃拟态",
    "苹果感",
    "动效",
    "动画",
    "丝滑",
    "流畅",
    "交互",
    "强交互",
    "鼠标",
    "鼠标跟随",
    "光标",
    "指针",
    "背景",
    "氛围",
    "光效",
    "首页",
    "首屏",
    "官网",
    "落地页",
    "产品页",
    "作品集",
    "插件",
    "卡片",
    "布局",
    "层次",
    "诊断",
    "普通",
    "惊艳",
    "物体",
    "模型",
    "视觉中心",
}


LIGHT_UPGRADE_TERMS = {
    "tailwind",
    "framer",
    "motion",
    "hover",
    "scroll",
    "reveal",
    "background",
    "gradient",
    "card",
    "spacing",
    "shadow",
    "border",
}


HEAVY_TERMS = {
    "three",
    "three.js",
    "webgl",
    "canvas",
    "particle",
    "particles",
    "gsap",
    "video background",
    "3d",
    "大型视频",
    "粒子",
    "复杂",
}


STRONG_INTERACTION_TERMS = {
    "强交互",
    "交互感",
    "鼠标跟随",
    "鼠标滑动",
    "跟随鼠标",
    "跟着鼠标",
    "光标",
    "指针",
    "磁吸",
    "聚光",
    "特别惊艳",
    "强烈",
    "强视觉",
    "动效拉满",
    "元素跟着",
    "cursor",
    "mouse follow",
    "pointer",
    "spotlight",
    "magnetic",
    "interactive",
}

EXPERIMENTAL_TRACK_TERMS = {
    "实验性",
    "视觉实验",
    "数字艺术",
    "网页艺术",
    "沉浸式",
    "强视觉",
    "视觉冲击",
    "震撼",
    "标志性动效",
    "非标准交互",
    "signature motion",
    "immersive",
    "digital art",
    "experimental visual",
    "visual impact",
}

BROAD_REDESIGN_TERMS = {
    "整站重设计",
    "全面重设计",
    "大范围改版",
    "重做整个网站",
    "full redesign",
    "site-wide redesign",
}

PROTOTYPE_STATUSES = {"not_started", "built", "approved", "rejected"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def text_blob(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif isinstance(value, dict):
            parts.append(json.dumps(value, ensure_ascii=False))
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def compact_terms(text: str) -> set[str]:
    lower = text.lower()
    latin = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_.+-]*", lower)
    chinese_hits = [term for term in CHINESE_KEYWORDS if term in text]
    short_chinese = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    return set(latin + chinese_hits + short_chinese)


def contains_any(text: str, terms: list[str] | set[str] | tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(str(term).lower() in lower for term in terms)


def alias_hits(query: str, aliases: dict[str, Any], group: str) -> set[str]:
    hits: set[str] = set()
    lower = query.lower()
    for key, terms in aliases.get(group, {}).items():
        candidates = [key] + list(terms)
        if any(str(term).lower() in lower for term in candidates):
            hits.add(key)
    return hits


def identify_mode(query: str) -> str:
    q = query.lower()
    if contains_any(q, ["诊断", "为什么普通", "哪里该改", "问题在哪", "质量"]):
        return "diagnose_page_quality"
    if contains_any(q, ["v0", "cursor", "codex", "claude code", "实现 prompt", "提示词", "prompt"]):
        return "implementation_prompt_writer"
    if contains_any(q, ["找", "参考", "风格", "类似", "灵感", "references"]):
        return "find_style_references"
    if contains_any(q, ["从 0", "从零", "新建", "生成一个", "做一个", "create", "build"]):
        return "generate_new_page"
    return "upgrade_existing_page"


def identify_task_mode(query: str) -> str:
    """Infer permission, not deliverable type, from explicit user language."""
    q = query.lower()
    if contains_any(
        q,
        [
            "请修改",
            "帮我修改",
            "直接修改",
            "直接实现",
            "实现这个",
            "落地实现",
            "安装组件",
            "新增依赖",
            "重构 ui",
            "重构页面",
            "完成代码",
            "implement this",
            "build this",
            "change the page",
        ],
    ):
        return "implementation"
    if contains_any(
        q,
        [
            "审计",
            "评价",
            "评估",
            "诊断",
            "找问题",
            "为什么",
            "哪里该改",
            "给建议",
            "review",
            "audit",
            "evaluate",
        ],
    ):
        return "analysis"
    return "proposal"


def identify_upgrade_track(query: str) -> str:
    return "experimental" if contains_any(query, EXPERIMENTAL_TRACK_TERMS) else "standard"


def identify_prototype_status(query: str) -> str:
    if contains_any(query, ["原型已通过", "人工已通过", "原型通过", "prototype approved"]):
        return "approved"
    if contains_any(query, ["原型已拒绝", "否决原型", "prototype rejected"]):
        return "rejected"
    if contains_any(query, ["原型已完成", "原型已经做完", "prototype built"]):
        return "built"
    return "not_started"


def identify_page_type(query: str) -> str:
    q = query.lower()
    mapping = [
        ("settings", ["设置页", "设置页面", "settings", "preferences"]),
        ("enterprise_admin", ["企业后台", "管理后台", "admin", "enterprise console"]),
        ("dashboard", ["dashboard", "仪表盘", "数据看板"]),
        ("marketing_homepage", ["官网首页", "产品官网", "homepage", "marketing site"]),
        ("landing_page", ["landing page", "落地页"]),
        ("product_page", ["产品页", "product page"]),
        ("pricing", ["pricing", "价格页", "套餐页"]),
        ("portfolio", ["作品集", "portfolio"]),
        ("form_flow", ["表单", "form", "注册", "登录"]),
    ]
    for label, terms in mapping:
        if contains_any(q, terms):
            return label
    return "generic_page"


def infer_product_goal(query: str, page_type: str) -> str:
    if page_type in {"settings", "enterprise_admin", "dashboard", "form_flow"}:
        return "Help users understand state and complete repeated tasks efficiently and safely."
    if page_type in {"marketing_homepage", "landing_page", "product_page"}:
        return "Communicate product value quickly, express the brand clearly, and support the primary conversion path."
    if page_type == "portfolio":
        return "Present work and point of view clearly while creating a memorable, usable experience."
    return "Confirm the product goal and page task from repository and user evidence before choosing a solution."


def identify_project_type(query: str) -> str:
    q = query.lower()
    mapping = [
        ("ai_saas", ["ai saas", "saas", "ai 产品", "ai产品", "automation", "workflow", "dashboard"]),
        ("portfolio", ["作品集", "portfolio", "个人网站", "designer", "creator"]),
        ("plugin", ["插件", "plugin", "extension", "add-on"]),
        ("agency", ["agency", "studio", "工作室", "设计机构"]),
        ("ecommerce", ["电商", "ecommerce", "shop", "commerce"]),
        ("fintech", ["fintech", "finance", "bank", "金融"]),
        ("web3", ["web3", "crypto", "nft"]),
        ("health", ["health", "medical", "clinic", "医疗", "健康"]),
        ("travel", ["travel", "旅游", "voyage"]),
        ("media", ["media", "blog", "内容", "视频"]),
    ]
    for label, terms in mapping:
        if contains_any(q, terms):
            return label
    return "generic"


def identify_target_modules(query: str, mode: str) -> list[str]:
    q = query.lower()
    modules: list[str] = []
    mapping = [
        ("hero", ["hero", "首屏", "首页", "头图"]),
        ("landing_page", ["landing", "落地页", "官网", "产品页", "首页"]),
        ("features", ["features", "功能", "卖点"]),
        ("pricing", ["pricing", "价格", "套餐"]),
        ("cta", ["cta", "转化", "call to action"]),
        ("footer", ["footer", "页脚"]),
        ("dashboard", ["dashboard", "仪表盘"]),
        ("background", ["background", "背景", "氛围", "光效"]),
        ("gradient", ["gradient", "渐变"]),
        ("component", ["component", "组件", "卡片", "card"]),
    ]
    for label, terms in mapping:
        if contains_any(q, terms):
            modules.append(label)
    if not modules:
        if mode == "find_style_references":
            modules = ["hero", "landing_page", "background"]
        elif mode == "generate_new_page":
            modules = ["landing_page", "hero"]
        else:
            modules = ["hero", "landing_page"]
    return list(dict.fromkeys(modules))


def diagnose_query(query: str) -> list[str]:
    q = query.lower()
    hints: list[str] = []
    if contains_any(q, ["普通", "高级", "质感", "premium", "polished", "冲击", "惊艳", "首页"]):
        hints.append("visual_impact: low")
    if contains_any(q, ["布局", "层次", "版式", "card", "卡片", "bento"]):
        hints.append("layout_depth: flat")
    if contains_any(q, ["动效", "动画", "丝滑", "motion", "animation", "scroll", "reveal"]):
        hints.append("motion_rhythm: missing")
    if contains_any(q, ["交互", "反馈", "hover", "cursor", "鼠标", "光标", "指针", "点击"]):
        hints.append("interaction_feedback: weak")
    if contains_any(q, ["背景", "氛围", "光效", "gradient", "ambient"]):
        hints.append("background_atmosphere: empty")
    if contains_any(q, ["品牌", "不像", "贴合", "产品官网"]):
        hints.append("brand_fit: acceptable")
    if contains_any(q, ["移动端", "手机", "mobile"]):
        hints.append("mobile_feasibility: caution")
    if contains_any(q, ["简单", "轻量", "不要太复杂", "性能"]):
        hints.append("implementation_risk: medium")
    if not hints:
        hints = ["visual_impact: unknown", "layout_depth: unknown", "motion_rhythm: unknown"]
    return hints


def detect_stack(text: str) -> list[str]:
    q = text.lower()
    stack: list[str] = []
    checks = [
        ("react", ["react", "tsx", "jsx"]),
        ("next", ["next.js", "nextjs", "app/page", "pages/index"]),
        ("vite", ["vite"]),
        ("tailwind", ["tailwind"]),
        ("framer_motion", ["framer motion", "motion/react"]),
        ("gsap", ["gsap"]),
        ("three", ["three", "three.js", "@react-three", "webgl"]),
        ("shadcn", ["shadcn", "components.json"]),
    ]
    for label, terms in checks:
        if contains_any(q, terms):
            stack.append(label)
    return stack


def derive_source_quality(record: dict[str, Any]) -> str:
    notes = str(record.get("notes") or "").lower()
    source = str(record.get("source") or "").lower()
    if record.get("prompt_raw") and ("github archive" in notes or "github_archive" in source):
        return "archive_public"
    if record.get("prompt_origin") == "original_public" and record.get("prompt_raw"):
        return "original_public"
    if record.get("is_locked") and not record.get("prompt_raw"):
        return "locked_metadata_only"
    if record.get("prompt_origin") == "generated_from_public_metadata":
        return "generated_reference"
    return "locked_metadata_only"


def derive_page_module(record: dict[str, Any], blob: str) -> str:
    category = str(record.get("category") or "").lower()
    visual_type = str(record.get("visual_type") or "").lower()
    kind = str(record.get("item_kind") or "").lower()
    if kind == "gradient" or "gradient" in category:
        return "gradient"
    if kind == "motion_video" or "background" in category or "animated background" in visual_type:
        return "background"
    checks = [
        ("hero", ["hero"]),
        ("landing_page", ["landing page", "landing-page", "website"]),
        ("features", ["features", "feature", "benefits"]),
        ("pricing", ["pricing"]),
        ("cta", ["cta"]),
        ("footer", ["footer"]),
        ("about", ["about"]),
        ("portfolio", ["portfolio"]),
        ("dashboard", ["dashboard"]),
        ("form", ["form", "signup", "sign in"]),
        ("component", ["component", "cards", "card", "tabs", "accordion", "slider", "carousel", "loader"]),
    ]
    combined = f"{category} {visual_type} {blob}"
    for label, terms in checks:
        if contains_any(combined, terms):
            return label
    if "saas" in combined or "agency" in combined:
        return "landing_page"
    return "component"


def derive_visual_style(blob: str) -> list[str]:
    styles: list[str] = []
    checks = [
        ("liquid_glass", ["liquid glass", "liquid-glass", "液态玻璃"]),
        ("glassmorphism", ["glass", "glassmorphism", "frosted", "translucent", "玻璃"]),
        ("3d", ["3d", "three.js", "webgl", "spline"]),
        ("cinematic_dark", ["dark", "black", "cinematic", "#0c0c0c", "video"]),
        ("editorial", ["editorial", "magazine", "serif", "archive"]),
        ("neon", ["neon", "glow", "cyber"]),
        ("gradient", ["gradient", "aurora"]),
        ("minimal", ["minimal", "clean", "apple", "white space"]),
        ("brutalist", ["brutalist", "bold", "raw"]),
        ("luxury", ["luxury", "premium", "high-end"]),
        ("naturecore", ["nature", "botanical", "mythic", "organic"]),
        ("retro_futurist", ["retro", "futurist", "vintage"]),
    ]
    for label, terms in checks:
        if contains_any(blob, terms):
            styles.append(label)
    return styles or ["polished_modern"]


def derive_interaction(blob: str) -> list[str]:
    interactions: list[str] = []
    checks = [
        ("hover_transform", ["hover", "mouseenter", "tilt"]),
        ("scroll_reveal", ["scroll", "reveal", "whileinview", "scrolltrigger"]),
        ("carousel", ["carousel", "carousal", "slider"]),
        ("tabs", ["tabs", "tab"]),
        ("accordion", ["accordion"]),
        ("sticky_cards", ["sticky", "pinned"]),
        ("cursor_follow", ["cursor", "pointer follow", "mouse follow"]),
        ("micro_interaction", ["micro", "transition", "feedback", "tap"]),
    ]
    for label, terms in checks:
        if contains_any(blob, terms):
            interactions.append(label)
    return interactions or ["none"]


def derive_motion(record: dict[str, Any], blob: str) -> list[str]:
    motions: list[str] = []
    if record.get("preview_video"):
        motions.append("video_hero")
    if str(record.get("item_kind") or "") == "motion_video" or "animated background" in str(record.get("visual_type") or "").lower():
        motions.append("background_loop")
    checks = [
        ("gradient_motion", ["gradient", "aurora"]),
        ("3d_orbit", ["3d", "orbit", "three.js", "webgl"]),
        ("parallax", ["parallax"]),
        ("text_reveal", ["text reveal", "word reveal", "stagger"]),
        ("card_motion", ["card", "cards", "tilt"]),
        ("transition", ["transition", "animation", "motion"]),
    ]
    for label, terms in checks:
        if contains_any(blob, terms):
            motions.append(label)
    return list(dict.fromkeys(motions)) or ["none"]


def derive_layout(blob: str, page_module: str) -> list[str]:
    layouts: list[str] = []
    checks = [
        ("full_bleed_hero", ["full-screen", "full viewport", "full-viewport", "100vh", "hero"]),
        ("split_hero", ["split", "two-column", "2 column"]),
        ("bento_grid", ["bento"]),
        ("card_grid", ["card grid", "cards", "grid"]),
        ("centered_editorial", ["centered", "editorial"]),
        ("dashboard_shell", ["dashboard", "sidebar"]),
        ("section_stack", ["sections", "section stack", "single-page"]),
        ("carousel_strip", ["carousel", "slider"]),
    ]
    for label, terms in checks:
        if contains_any(blob, terms):
            layouts.append(label)
    if not layouts and page_module == "hero":
        layouts.append("full_bleed_hero")
    if not layouts and page_module == "landing_page":
        layouts.append("section_stack")
    return layouts or ["card_grid"]


def derive_stack(record: dict[str, Any], blob: str) -> list[str]:
    stacks: list[str] = []
    tool_hint = str(record.get("tool_hint") or "").lower()
    checks = [
        ("framer", [tool_hint], ["framer"]),
        ("v0", [tool_hint], ["v0"]),
        ("cursor", [tool_hint], ["cursor"]),
        ("react_tailwind", [blob], ["react", "tailwind"]),
        ("react_framer_motion", [blob], ["framer motion", "motion/react", "motion"]),
        ("react_three", [blob], ["three.js", "@react-three", "react three"]),
        ("gsap", [blob], ["gsap", "scrolltrigger"]),
        ("shadcn", [blob], ["shadcn"]),
        ("html_css_js", [blob], ["<!doctype", "<html", "css", "javascript"]),
    ]
    for label, sources, terms in checks:
        if any(contains_any(source, terms) for source in sources):
            stacks.append(label)
    return list(dict.fromkeys(stacks)) or ["unknown"]


def derive_industry(blob: str) -> str:
    checks = [
        ("ai_saas", ["ai", "saas", "automation", "workflow", "neural", "dashboard"]),
        ("agency", ["agency", "studio", "creative"]),
        ("portfolio", ["portfolio", "creator", "designer"]),
        ("fintech", ["fintech", "finance", "bank", "invoice"]),
        ("ecommerce", ["ecommerce", "shop", "commerce", "product"]),
        ("web3", ["web3", "nft", "crypto"]),
        ("health", ["health", "clinic", "dental", "medical", "bio"]),
        ("travel", ["travel", "voyage"]),
        ("media", ["media", "blog", "video", "email"]),
        ("plugin", ["plugin", "extension"]),
    ]
    for label, terms in checks:
        if contains_any(blob, terms):
            return label
    return "generic"


def derive_complexity(stack: list[str], motion: list[str], blob: str) -> str:
    if contains_any(blob, ["three.js", "webgl", "canvas", "particle", "particles"]) or "react_three" in stack:
        return "high"
    if "gsap" in stack or "video_hero" in motion or "3d_orbit" in motion:
        return "high"
    if "react_framer_motion" in stack or contains_any(blob, ["framer motion", "motion/react", "scroll reveal"]):
        return "medium"
    return "low"


def risk_from_features(complexity: str, motion: list[str], blob: str) -> tuple[str, str]:
    heavy = complexity == "high" or contains_any(blob, HEAVY_TERMS)
    if heavy and ("video_hero" in motion or "3d_orbit" in motion):
        return "high", "high"
    if heavy:
        return "medium", "high"
    if complexity == "medium":
        return "medium", "medium"
    return "low", "low"


def derive_upgrade_dimensions(page_module: str, styles: list[str], interactions: list[str], motions: list[str], layouts: list[str]) -> list[str]:
    dims: list[str] = []
    if page_module in {"hero", "landing_page"} or styles:
        dims.append("visual_impact")
    if any(layout != "card_grid" for layout in layouts):
        dims.append("layout_depth")
    if any(motion != "none" for motion in motions):
        dims.append("motion_rhythm")
    if any(interaction != "none" for interaction in interactions):
        dims.append("interaction_feedback")
    if page_module in {"background", "gradient"} or "gradient" in styles:
        dims.append("background_atmosphere")
    dims.append("brand_fit")
    return list(dict.fromkeys(dims))


def derive_record(record: dict[str, Any]) -> dict[str, Any]:
    blob = text_blob(
        record.get("title"),
        record.get("subtitle"),
        record.get("category"),
        record.get("visual_type"),
        record.get("tags"),
        record.get("tool_hint"),
        record.get("prompt_raw") or "",
        record.get("prompt_cleaned") or "",
        record.get("generated_prompt_basis") or {},
    )
    source_quality = derive_source_quality(record)
    page_module = derive_page_module(record, blob)
    styles = derive_visual_style(blob)
    interactions = derive_interaction(blob)
    motions = derive_motion(record, blob)
    layouts = derive_layout(blob, page_module)
    stack = derive_stack(record, blob)
    industry = derive_industry(blob)
    complexity = derive_complexity(stack, motions, blob)
    mobile_risk, performance_risk = risk_from_features(complexity, motions, blob)
    upgrade_dimensions = derive_upgrade_dimensions(page_module, styles, interactions, motions, layouts)
    vibe_keywords = list(dict.fromkeys(styles + motions + interactions + [industry, page_module]))
    return {
        "blob": blob,
        "terms": compact_terms(blob),
        "source_quality": source_quality,
        "page_module": page_module,
        "visual_style": styles,
        "interaction_pattern": interactions,
        "motion_type": motions,
        "layout_pattern": layouts,
        "implementation_stack": stack,
        "industry_or_domain": industry,
        "complexity": complexity,
        "mobile_risk": mobile_risk,
        "performance_risk": performance_risk,
        "upgrade_dimension": upgrade_dimensions,
        "vibe_keywords": vibe_keywords,
    }


def query_context(
    query: str,
    aliases: dict[str, Any],
    project_facts: str = "",
    task_mode: str | None = None,
    upgrade_track: str | None = None,
    prototype_status: str | None = None,
) -> dict[str, Any]:
    combined = f"{query}\n{project_facts}".strip()
    mode = identify_mode(query)
    permission_mode = task_mode or identify_task_mode(query)
    track = upgrade_track or identify_upgrade_track(query)
    prototype_required = track == "experimental" or contains_any(query, BROAD_REDESIGN_TERMS)
    gate_status = prototype_status or identify_prototype_status(query)
    if gate_status not in PROTOTYPE_STATUSES:
        raise ValueError(f"Unsupported prototype status: {gate_status}")
    if not prototype_required:
        gate_status = "not_required"
    page_type = identify_page_type(combined)
    project_type = identify_project_type(combined)
    target_modules = identify_target_modules(query, mode)
    diagnosis_hints = diagnose_query(query)
    wanted_styles = alias_hits(query, aliases, "vibe_keywords")
    if "glass" in wanted_styles:
        wanted_styles.update({"glassmorphism", "liquid_glass"})
    if "premium" in wanted_styles:
        wanted_styles.update({"luxury", "polished_modern", "editorial"})
    if "tech" in wanted_styles:
        wanted_styles.update({"cinematic_dark", "neon", "3d"})
    if "apple" in wanted_styles:
        wanted_styles.update({"minimal", "editorial"})
    wanted_dimensions: set[str] = set()
    for hint in diagnosis_hints:
        if ":" not in hint:
            continue
        key, value = hint.split(":", 1)
        if value.strip() != "unknown":
            wanted_dimensions.add(key.strip())
    return {
        "query": query,
        "project_facts": project_facts,
        "query_terms": compact_terms(query),
        "mode": mode,
        "task_mode": permission_mode,
        "upgrade_track": track,
        "prototype_required": prototype_required,
        "prototype_status": gate_status,
        "page_type": page_type,
        "product_goal": infer_product_goal(query, page_type),
        "project_type": project_type,
        "target_modules": target_modules,
        "diagnosis_hints": diagnosis_hints,
        "wanted_styles": wanted_styles,
        "wanted_dimensions": wanted_dimensions,
        "project_stack": detect_stack(combined),
        "wants_background": contains_any(query, ["背景", "氛围", "background", "ambient", "gradient", "渐变", "光效"]),
        "wants_motion": contains_any(query, ["动效", "动画", "motion", "animation", "丝滑", "流畅"]),
        "wants_heavy": contains_any(query, ["three", "three.js", "webgl", "3d", "强视觉", "震撼", "复杂", "物体", "模型"]),
        "wants_strong_interaction": contains_any(query, STRONG_INTERACTION_TERMS),
        "wants_creative_reference": contains_any(
            query,
            ["找参考", "视觉参考", "灵感", "找风格", "风格方向", "视觉方向", "构图", "氛围", "品牌表达", "记忆点", "创意", "reference", "inspiration"],
        ),
        "mobile_first": contains_any(query, ["移动端", "手机", "mobile"]),
    }


def ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(1.0, count / total)


def score_record(record: dict[str, Any], derived: dict[str, Any], ctx: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    penalties: list[str] = []
    modules = set(ctx["target_modules"])
    styles = set(derived["visual_style"])
    dimensions = set(derived["upgrade_dimension"])
    query_terms = set(ctx["query_terms"])
    blob_terms = set(derived["terms"])

    module_match = derived["page_module"] in modules
    project_match = derived["industry_or_domain"] in {ctx["project_type"], "generic"} or ctx["project_type"] == "generic"
    intent_match = 0.0
    if module_match:
        intent_match += 0.55
        reasons.append(f"module matches {derived['page_module']}")
    if project_match:
        intent_match += 0.3
        if derived["industry_or_domain"] != "generic":
            reasons.append(f"domain matches {derived['industry_or_domain']}")
    if ctx["mode"] == "find_style_references" and styles & set(ctx["wanted_styles"]):
        intent_match += 0.25
    intent_match = min(1.0, intent_match)

    diagnosis_overlap = dimensions & set(ctx["wanted_dimensions"])
    diagnosis_match = ratio(len(diagnosis_overlap), max(1, len(ctx["wanted_dimensions"])))
    if diagnosis_overlap:
        reasons.append("addresses " + ", ".join(sorted(diagnosis_overlap)))

    taxonomy_hits = 0
    taxonomy_total = 4
    if module_match:
        taxonomy_hits += 1
    if styles & set(ctx["wanted_styles"]):
        taxonomy_hits += 1
        reasons.append("style matches " + ", ".join(sorted(styles & set(ctx["wanted_styles"]))))
    if ctx["wants_motion"] and any(m != "none" for m in derived["motion_type"]):
        taxonomy_hits += 1
        reasons.append("has motion reference")
    if project_match:
        taxonomy_hits += 1
    taxonomy_match = taxonomy_hits / taxonomy_total

    keyword_overlap = query_terms & blob_terms
    keyword_match = ratio(len(keyword_overlap), max(3, len(query_terms)))
    if keyword_overlap:
        reasons.append("keyword overlap: " + ", ".join(sorted(list(keyword_overlap))[:6]))

    raw_text = str(record.get("prompt_raw") or record.get("prompt_cleaned") or "").lower()
    generated_text = str(record.get("generated_prompt") or "").lower()
    raw_hits = sum(1 for term in query_terms if term.lower() in raw_text)
    generated_hits = sum(1 for term in query_terms if term.lower() in generated_text)
    prompt_text_match = min(1.0, (raw_hits * 1.0 + generated_hits * 0.35) / max(3, len(query_terms)))

    source_quality_score = SOURCE_SCORES.get(derived["source_quality"], 0.25)

    media_signal = 0.0
    if record.get("preview_video") and ctx["wants_motion"]:
        media_signal += 0.6
    if record.get("preview_image") and (ctx["wants_background"] or ctx["mode"] == "find_style_references"):
        media_signal += 0.4
    media_signal = min(1.0, media_signal)

    feasibility = 0.8
    if derived["complexity"] == "high" and not ctx["wants_heavy"]:
        feasibility -= 0.35
        penalties.append("heavy effect without explicit heavy-visual request")
    if ctx["mobile_first"] and derived["mobile_risk"] == "high":
        feasibility -= 0.35
        penalties.append("high mobile risk")
    if derived["performance_risk"] == "high" and not ctx["wants_heavy"]:
        feasibility -= 0.2
        penalties.append("high performance risk")
    feasibility = max(0.0, min(1.0, feasibility))

    penalty_value = 0.0
    if derived["page_module"] in {"background", "gradient"} and not ctx["wants_background"] and ctx["mode"] != "find_style_references":
        penalty_value += 0.12
        penalties.append("background-only case is auxiliary")
    if derived["source_quality"] == "locked_metadata_only":
        penalty_value += 0.04
    if derived["source_quality"] == "generated_reference":
        penalty_value += 0.02

    score = (
        0.22 * intent_match
        + 0.18 * diagnosis_match
        + 0.16 * taxonomy_match
        + 0.14 * keyword_match
        + 0.12 * prompt_text_match
        + 0.08 * source_quality_score
        + 0.05 * media_signal
        + 0.05 * feasibility
        - penalty_value
    )
    return max(0.0, score), reasons[:8], penalties


def borrowable_points(derived: dict[str, Any], record: dict[str, Any]) -> list[str]:
    points = [
        f"Use its {derived['page_module']} structure as a reference for the target section.",
        "Borrow the visual style direction: " + ", ".join(derived["visual_style"][:3]) + ".",
    ]
    if any(m != "none" for m in derived["motion_type"]):
        points.append("Borrow the motion rhythm: " + ", ".join(derived["motion_type"][:3]) + ".")
    if any(i != "none" for i in derived["interaction_pattern"]):
        points.append("Borrow the interaction pattern: " + ", ".join(derived["interaction_pattern"][:3]) + ".")
    if record.get("preview_image") or record.get("preview_video"):
        points.append("Use the preview media as visual direction, not as proof of full prompt access.")
    return points[:5]


def mechanism_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    motions = [value for value in candidate.get("motion_type", []) if value != "none"]
    interactions = [value for value in candidate.get("interaction_pattern", []) if value != "none"]
    layouts = list(candidate.get("layout_pattern") or [])
    signals = set(motions + interactions + layouts)
    if {"scroll_reveal", "sticky_cards", "parallax"} & signals:
        trigger = "normalized scroll progress"
    elif "cursor_follow" in signals:
        trigger = "pointer target with frame-by-frame interpolation"
    elif "hover_transform" in signals:
        trigger = "hover or focus state"
    elif "carousel" in signals:
        trigger = "explicit item selection"
    else:
        trigger = "page entry or primary action"

    primitives = ["existing project layout and motion primitives"]
    if "scroll_reveal" in signals or "sticky_cards" in signals:
        primitives.extend(["sticky scene", "normalized progress", "requestAnimationFrame or the existing motion runtime"])
    if "cursor_follow" in signals or "parallax" in signals:
        primitives.extend(["pointer target/current separation", "transform-only observation layer"])
    if "text_reveal" in signals:
        primitives.extend(["clip-path or mask", "staggered transform"])
    if "3d_orbit" in signals:
        primitives.append("CSS 3D or an already-installed 3D runtime")
    if len(primitives) == 1:
        primitives.extend(["CSS grid or positioned composition", "transform, opacity, or clip-path"])

    return {
        "evidence_type": "inference_from_public_record",
        "trigger": trigger,
        "state_changes": [
            "recognizable starting composition",
            "controlled structural transformation using " + ", ".join((motions + interactions)[:3] or ["layout state"]),
            "stable resolved composition that supports the page task",
        ],
        "spatial_relationship": " → ".join(layouts[:3]) if layouts else "preserve content identity while changing its spatial grouping",
        "implementation_primitives": list(dict.fromkeys(primitives)),
    }


def synthesize_mechanism(selected: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any] | None:
    if not selected:
        return None
    evidence = [item["mechanism_evidence"] for item in selected]
    triggers = list(dict.fromkeys(item["trigger"] for item in evidence))
    layouts = list(dict.fromkeys(item["spatial_relationship"] for item in evidence))
    primitives: list[str] = []
    for item in evidence:
        primitives.extend(item["implementation_primitives"])
    if any("scroll" in value for value in triggers):
        name = "scroll-linked spatial transformation"
    elif any("pointer" in value for value in triggers):
        name = "pointer-reactive focal field"
    elif any("selection" in value for value in triggers):
        name = "selection-driven shared composition"
    else:
        name = "stateful composition transformation"
    return {
        "name": name,
        "target_surface": (ctx.get("target_modules") or [ctx.get("page_type", "page")])[0],
        "source_contributions": [
            {
                "source_record_id": item.get("source_record_id"),
                "title": item.get("title"),
                "source_quality": item.get("source_quality"),
                "borrowed_behavior": item["mechanism_evidence"],
            }
            for item in selected
        ],
        "trigger": triggers[0] if len(triggers) == 1 else " + ".join(triggers[:2]),
        "key_states": [
            "State 1: preserve recognizable current content and establish the visual control source.",
            "State 2: reorganize the same assets through " + ", ".join(layouts[:2]) + ".",
            "State 3: resolve into a stable branded composition with the primary task still available.",
        ],
        "spatial_transformation": "Combine " + ", ".join(layouts[:3]) + " into one continuous mechanism rather than separate decorative effects.",
        "implementation_primitives": list(dict.fromkeys(primitives))[:8],
        "five_second_difference_target": "At the same viewport, the prototype must reveal a different spatial system or signature transition within five seconds, not only new spacing, cards, fades, or color polish.",
        "fallback": "Keep the same narrative states on mobile and reduced motion, but shorten depth, travel, and continuous pointer response.",
    }


def avoid_copying(derived: dict[str, Any]) -> list[str]:
    avoid = [
        "Do not copy the full case blindly; adapt the idea to the current brand and content.",
    ]
    if derived["source_quality"] in {"generated_reference", "locked_metadata_only"}:
        avoid.append("Do not present this as an original MotionSites prompt; it is metadata-derived reference material.")
    if derived["complexity"] == "high":
        avoid.append("Avoid shipping the heavy effect unchanged on mobile; provide a simpler fallback.")
    if derived["page_module"] in {"background", "gradient"}:
        avoid.append("Do not use this as a complete page design; use it as background or atmosphere support.")
    return avoid


def diversify(candidates: list[dict[str, Any]], top_k: int, ctx: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    selected: list[dict[str, Any]] = []
    module_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    notes: list[str] = []
    background_limit = 2 if ctx["wants_background"] or ctx["mode"] == "find_style_references" else 1

    for candidate in candidates:
        module = candidate["page_module"]
        primary_style = candidate["visual_style"][0] if candidate["visual_style"] else "unknown"
        if module_counts[module] >= 3:
            continue
        if module in {"background", "gradient"} and module_counts["background_aux"] >= background_limit:
            continue
        if style_counts[primary_style] >= 3 and len(selected) >= 3:
            continue
        selected.append(candidate)
        module_counts[module] += 1
        if module in {"background", "gradient"}:
            module_counts["background_aux"] += 1
        style_counts[primary_style] += 1
        if len(selected) >= top_k:
            break

    if not any(c["source_quality"] in {"original_public", "archive_public"} for c in selected):
        replacement = next((c for c in candidates if c["source_quality"] in {"original_public", "archive_public"}), None)
        if replacement:
            if len(selected) >= top_k:
                selected[-1] = replacement
            else:
                selected.append(replacement)
            notes.append("Inserted one original/archive public prompt case to improve source quality.")

    if module_counts["background_aux"]:
        notes.append("Background/gradient cases are limited so they support the page instead of replacing main layout references.")
    notes.append("Applied module and style diversity so the result is not all hero or all background references.")
    return selected[:top_k], notes


def build_decision_task(ctx: dict[str, Any], react_aliases: dict[str, Any]) -> dict[str, Any]:
    query = ctx["query"]
    lower = query.lower()
    diagnosis = set(ctx["wanted_dimensions"])
    page_type = ctx["page_type"]
    operational_page = page_type in {"settings", "enterprise_admin", "dashboard", "form_flow", "pricing"}
    marketing_page = page_type in {"marketing_homepage", "landing_page", "product_page", "portfolio"}
    mature_design_system = contains_any(
        ctx["project_facts"],
        ["mature design system", "成熟设计系统", "established design system", "complete design system"],
    )

    experimental = ctx["upgrade_track"] == "experimental"
    creative_reference_needed = ctx["wants_creative_reference"] or experimental or (
        "visual_impact" in diagnosis and not operational_page and contains_any(lower, ["创意", "品牌记忆", "视觉方向", "构图"])
    )

    existing_asset_opportunities = [
        "Inspect current design tokens, layout primitives, controls, feedback states, and installed dependencies before external search.",
        "Reuse or adapt an existing component when it is fit for purpose and preserves system consistency.",
    ]
    if operational_page:
        existing_asset_opportunities.append("Check existing form, table, navigation, validation, toast, loading, and empty-state patterns first.")

    component_opportunities: list[dict[str, Any]] = []
    categories: list[str] = []

    def add_opportunity(area: str, problem: str, candidate_categories: list[str], source_bias: list[str]) -> None:
        component_opportunities.append(
            {
                "area": area,
                "problem": problem,
                "candidate_categories": candidate_categories,
                "source_bias": source_bias,
            }
        )
        categories.extend(candidate_categories)

    if operational_page or contains_any(lower, ["表单", "按钮", "导航", "dialog", "select", "dropdown", "tabs"]):
        add_opportunity(
            "foundation_ui",
            "Improve task structure, controls, action priority, and reliable interaction behavior.",
            ["layout", "form", "button", "feedback"],
            ["current_project_components", "foundation_ui"],
        )
    if "layout_depth" in diagnosis or contains_any(lower, ["层级", "层次", "密度", "布局", "信息架构"]):
        add_opportunity(
            "information_architecture",
            "Clarify grouping, hierarchy, density, and scan path.",
            ["layout", "section", "card"],
            ["current_project_components", "foundation_ui", "custom_build"],
        )
    if "interaction_feedback" in diagnosis or contains_any(lower, ["反馈", "loading", "加载", "空状态", "切换", "carousel"]):
        add_opportunity(
            "interaction_feedback",
            "Make state changes and user actions clear.",
            ["feedback", "loading", "empty_state", "content_switching"],
            ["current_project_components", "foundation_ui", "react_bits", "custom_build"],
        )
    if experimental or ("visual_impact" in diagnosis and not operational_page) or contains_any(lower, ["品牌", "hero", "视觉中心", "记忆点", "图像展示"]):
        add_opportunity(
            "expressive_visual",
            "Strengthen product expression, brand memory, or page focus.",
            ["hero", "text", "background", "card_interaction", "image_display", "brand_motion"],
            ["react_bits", "custom_build"],
        )
    if not component_opportunities:
        add_opportunity(
            "general_ui",
            "Confirm the concrete page problem before selecting a reusable solution.",
            ["layout", "feedback"],
            ["current_project_components", "foundation_ui", "custom_build"],
        )

    if mature_design_system:
        for opportunity in component_opportunities:
            opportunity["source_bias"] = [
                source for source in opportunity["source_bias"] if source != "react_bits"
            ]

    react_categories: list[str] = []
    react_queries: list[str] = []

    def add_react_category(category: str, fallback_queries: list[str] | None = None) -> None:
        if category in react_categories:
            return
        react_categories.append(category)
        details = react_aliases.get(category, {})
        react_queries.extend(str(item) for item in details.get("queries", []))
        react_queries.extend(fallback_queries or [])

    for category, details in react_aliases.items():
        aliases = [category] + list(details.get("aliases", []))
        if any(str(alias).lower() in lower for alias in aliases):
            add_react_category(category)

    if experimental or contains_any(lower, ["hero", "品牌", "记忆点", "视觉中心"]):
        add_react_category("text_reveal")
        add_react_category("background_atmosphere")
        add_react_category("card_tilt")
    if contains_any(lower, ["loading", "加载", "等待"]):
        add_react_category("loading", ["animated loading indicator", "branded loading animation"])
    if contains_any(lower, ["carousel", "轮播", "内容切换", "图片展示"]):
        add_react_category("carousel", ["interactive carousel", "image carousel transition"])
    if "interaction_feedback" in diagnosis and not operational_page:
        add_react_category("micro_interaction", ["button card micro interaction", "content transition feedback"])
    if ctx["wants_strong_interaction"]:
        add_react_category("cursor_follow")
        add_react_category("spotlight")
        add_react_category("magnetic")
    if ctx["wants_motion"]:
        add_react_category("scroll_reveal")
    if "liquid_glass" in ctx["wanted_styles"] or "glassmorphism" in ctx["wanted_styles"]:
        add_react_category("liquid_glass")
    if ctx["wants_heavy"] or contains_any(lower, ["物体", "模型", "object", "model", "orb"]):
        add_react_category("object_hero")

    expressive_opportunity = any(
        item["area"] in {"expressive_visual", "interaction_feedback"} for item in component_opportunities
    )
    react_compatible = bool(set(ctx["project_stack"]) & {"react", "next", "vite", "tailwind", "shadcn"})
    stack_unknown = not ctx["project_stack"]
    react_search_recommended = bool(react_categories) and expressive_opportunity and (
        react_compatible or stack_unknown or ctx["task_mode"] != "implementation"
    ) and not mature_design_system

    if react_search_recommended:
        react_reason = "An expressive reusable component may solve a diagnosed problem; discover candidates, then compare before adoption."
    elif mature_design_system and react_categories:
        react_reason = "The mature project design system is the default source; consider an external creative candidate only after a specific unresolved gap is confirmed."
    elif react_categories and not react_compatible and ctx["task_mode"] == "implementation":
        react_reason = "React Bits candidates exist, but the implementation stack is not confirmed compatible; do not install before inspection."
    else:
        react_reason = "Current project assets, information architecture, or foundation UI are the stronger first route for this task."

    foundation_queries: list[str] = []
    if operational_page or "foundation_ui" in {item["area"] for item in component_opportunities}:
        foundation_queries.extend(["form layout and field grouping", "button hierarchy", "validation toast saving state"])
    if marketing_page:
        foundation_queries.append("accessible navigation buttons dialog and content structure")
    if contains_any(lower, ["导航", "navigation", "tabs", "dialog", "select", "dropdown"]):
        foundation_queries.append("accessible navigation dialog select tabs")
    if contains_any(lower, ["loading", "加载", "空状态", "empty state"]):
        foundation_queries.append("accessible loading and empty state")

    motionsites_queries: list[str] = []
    if creative_reference_needed:
        modules = " ".join(ctx["target_modules"][:3])
        styles = " ".join(sorted(ctx["wanted_styles"])[:4])
        motionsites_queries = [value.strip() for value in [f"{ctx['project_type']} {modules} {styles}", query] if value.strip()]

    preferred_sources: list[dict[str, Any]] = [
        {
            "source": "current_project_context",
            "priority": 1,
            "reason": "Controlling source for product, content, brand, stack, and constraints.",
        },
        {
            "source": "current_project_components",
            "priority": 2,
            "reason": "Check reuse and adaptation before adding another component system.",
        },
    ]
    if operational_page or foundation_queries:
        preferred_sources.append(
            {
                "source": "foundation_ui",
                "priority": 3,
                "reason": "Use for reliable controls, layout, feedback, and accessibility primitives.",
            }
        )
    if creative_reference_needed:
        preferred_sources.append(
            {
                "source": "motionsites",
                "priority": 4,
                "reason": "Use only for creative direction, composition, rhythm, atmosphere, and narrative reference.",
            }
        )
    if react_categories and not mature_design_system:
        preferred_sources.append(
            {
                "source": "react_bits",
                "priority": 5,
                "reason": "Discover expressive visual and dynamic interaction candidates; adoption remains conditional.",
            }
        )
    preferred_sources.append(
        {
            "source": "custom_build",
            "priority": 6,
            "reason": "Use when no candidate fits or a small purpose-built solution is clearer and cheaper.",
        }
    )

    can_implement = ctx["task_mode"] == "implementation"
    gate_approved = ctx["prototype_status"] == "approved"
    integration_allowed = can_implement and (not ctx["prototype_required"] or gate_approved)
    prototype_changes_allowed = can_implement and ctx["prototype_required"] and ctx["prototype_status"] in {"not_started", "built"}
    permissions = {
        "inspect_and_query": True,
        "modify_files": can_implement,
        "prototype_changes": prototype_changes_allowed,
        "full_integration": integration_allowed,
        "install_components": integration_allowed,
        "add_dependencies": integration_allowed,
        "run_prototype_verification": prototype_changes_allowed,
        "run_integration_verification": integration_allowed,
        "condition": "Before prototype approval, implementation is limited to one isolated prototype surface." if prototype_changes_allowed else "Full integration requires implementation permission and an approved prototype when the gate applies." if can_implement else "Return analysis or a proposal only; do not change the project.",
    }

    next_actions = [
        "Confirm product goal, page task, and diagnosed issues against repository or supplied visual evidence.",
        "Inspect existing components and dependencies before resolving external candidates.",
    ]
    if creative_reference_needed:
        next_actions.append("Retrieve at most three MotionSites references and synthesize one concrete mechanism with trigger, states, spatial change, primitives, and a five-second target.")
    if foundation_queries:
        next_actions.append("Resolve foundation UI gaps against the current design system and compatible primitives.")
    if react_categories:
        next_actions.append("Resolve React Bits categories to candidates and compare them before adoption.")
    if prototype_changes_allowed:
        next_actions.append("Build one isolated prototype, run minimal runtime checks, then stop for human visual approval.")
    elif integration_allowed:
        next_actions.append("Integrate the approved mechanism and run targeted responsive, accessibility, reduced-motion, performance, and task-flow checks.")
    elif can_implement and ctx["prototype_required"]:
        next_actions.append("Do not integrate or install expressive dependencies until the prototype is approved.")
    else:
        next_actions.append("Stop at the mode-appropriate diagnosis or proposal until implementation is explicitly authorized.")

    decision_task = {
        "schema_version": "3.0",
        "task_mode": ctx["task_mode"],
        "upgrade_track": ctx["upgrade_track"],
        "request_type": ctx["mode"],
        "page_type": page_type,
        "project_type": ctx["project_type"],
        "product_goal": ctx["product_goal"],
        "diagnosed_issues": ctx["diagnosis_hints"],
        "existing_asset_opportunities": existing_asset_opportunities,
        "creative_reference_needed": creative_reference_needed,
        "prototype_required": ctx["prototype_required"],
        "prototype_gate": {
            "status": ctx["prototype_status"],
            "human_decisions": ["approved", "revise_once", "rejected"],
            "full_integration_blocked": ctx["prototype_required"] and not gate_approved,
            "targeted_revision_limit": 1,
        },
        "motionsites_queries": list(dict.fromkeys(motionsites_queries))[:3],
        "component_opportunities": component_opportunities,
        "component_categories": list(dict.fromkeys(categories + react_categories)),
        "preferred_sources": preferred_sources,
        "react_bits_search_recommended": react_search_recommended,
        "react_bits_reason": react_reason,
        "react_bits_queries": list(dict.fromkeys(react_queries))[:12],
        "foundation_ui_queries": list(dict.fromkeys(foundation_queries))[:8],
        "custom_build_candidates": [
            "Brand-specific composition or interaction at equivalent visual ambition when expressive external candidates do not fit.",
            "Small feedback or layout behavior where a new dependency would cost more than a focused implementation.",
        ],
        "adoption_constraints": [
            "Problem, product, and brand fit",
            "Stack compatibility and conflict with existing components",
            "Dependency size, performance, and mobile behavior",
            "Accessibility and reduced-motion behavior",
            "Customization effort, maintenance cost, and spectacle-only risk",
        ],
        "performance_constraints": [
            "Prefer the lowest-cost solution that preserves the intended experience.",
            "Provide mobile and reduced-motion fallbacks for expressive animation.",
            "Do not add heavy 3D, video, particles, or complex timelines without explicit need and evidence.",
        ],
        "accessibility_requirements": [
            "Preserve semantic structure, keyboard access, visible focus, and understandable state feedback.",
            "Verify contrast, labels, error messaging, and motion alternatives for affected interactions.",
        ],
        "implementation_permissions": permissions,
        "creative_mechanism": None,
        "motionsites_candidates": [],
        "budget_guardrails": {
            "plans_per_phase": 1,
            "reference_passes_per_phase": 1,
            "max_references_before_approval": 3,
            "max_prototypes_before_approval": 1,
            "max_viewports_before_approval": 2,
            "reports_per_phase": 1,
            "prototype_soft_token_budget": 180000,
            "prototype_human_checkpoint": 250000,
            "integration_soft_token_budget": 300000,
        },
        "verification_plan": {
            "stage": "prototype_minimum" if prototype_changes_allowed or (ctx["prototype_required"] and not gate_approved) else "integration_targeted" if integration_allowed else "recommendation_only",
            "prototype_checks": ["same-viewport before/after", "one desktop viewport", "one mobile viewport", "build", "console"],
            "post_approval_checks": ["relevant real viewports", "keyboard and focus", "reduced motion", "runtime cost", "original task flow", "regression boundary"],
        },
        "recommended_next_actions": next_actions,
    }
    decision_task["candidate_requests"] = build_candidate_requests(decision_task)
    return decision_task


def search(
    query: str,
    top_k: int = 3,
    project_facts: str = "",
    task_mode: str | None = None,
    component_candidates: list[dict[str, Any]] | None = None,
    raw_retrieval_attempts: list[dict[str, Any]] | None = None,
    target_root: Path | None = None,
    enable_component_cli: bool = False,
    enable_registry_http: bool = False,
    mcp_available_in_session: bool = False,
    upgrade_track: str | None = None,
    prototype_status: str | None = None,
) -> dict[str, Any]:
    aliases = load_json(ALIASES_PATH)
    react_aliases = load_json(REACT_BITS_ALIASES_PATH)
    ctx = query_context(query, aliases, project_facts, task_mode, upgrade_track, prototype_status)
    decision_task = build_decision_task(ctx, react_aliases)
    candidate_result = retrieve_components(
        decision_task,
        SKILL_DIR.parent,
        target_root,
        project_facts,
        raw_retrieval_attempts,
        component_candidates,
        enable_component_cli,
        enable_registry_http,
        mcp_available_in_session,
    )
    decision_task["visual_equivalence_fallbacks"] = candidate_result["visual_equivalence_fallbacks"]

    if not DATA_PATH.exists():
        return {
            "query": query,
            "decision_task": decision_task,
            "candidate_requests": candidate_result["candidate_requests"],
            "component_candidates": candidate_result["component_candidates"],
            "adoption_decisions": candidate_result["adoption_decisions"],
            "category_recommendations": candidate_result["category_recommendations"],
            "visual_equivalence_fallbacks": candidate_result["visual_equivalence_fallbacks"],
            "runtime_capabilities": candidate_result["runtime_capabilities"],
            "target_stack": candidate_result["target_stack"],
            "retrieval_attempts": candidate_result["retrieval_attempts"],
            "fallback_used": candidate_result["fallback_used"],
            "restart_required": candidate_result["restart_required"],
            "side_effects": candidate_result["side_effects"],
            "warnings": [f"Data file not found: {DATA_PATH}"],
            "diversity_notes": [],
        }

    rows = load_jsonl(DATA_PATH)
    candidates: list[dict[str, Any]] = []

    for record in rows:
        derived = derive_record(record)
        score, reasons, penalties = score_record(record, derived, ctx)
        if score <= 0:
            continue
        candidate = {
            "title": record.get("title") or "",
            "source_record_id": record.get("source_record_id") or "",
            "page_module": derived["page_module"],
            "visual_style": derived["visual_style"],
            "motion_type": derived["motion_type"],
            "interaction_pattern": derived["interaction_pattern"],
            "layout_pattern": derived["layout_pattern"],
            "implementation_stack": derived["implementation_stack"],
            "industry_or_domain": derived["industry_or_domain"],
            "complexity": derived["complexity"],
            "mobile_risk": derived["mobile_risk"],
            "performance_risk": derived["performance_risk"],
            "source_quality": derived["source_quality"],
            "prompt_origin": record.get("prompt_origin") or "",
            "access_status": record.get("access_status") or "",
            "score": round(score, 4),
            "match_reasons": reasons,
            "borrowable_points": borrowable_points(derived, record),
            "avoid_copying": avoid_copying(derived),
            "preview_image": record.get("preview_image") or "",
            "preview_video": record.get("preview_video") or "",
            "page_url": record.get("page_url") or "",
            "_penalties": penalties,
        }
        candidate["mechanism_evidence"] = mechanism_evidence(candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected, diversity_notes = diversify(candidates, max(1, min(3, top_k)), ctx)
    for item in selected:
        item.pop("_penalties", None)

    if not decision_task["creative_reference_needed"]:
        selected = []
        diversity_notes = [
            "MotionSites candidates were intentionally omitted because the diagnosed task does not require external creative reference."
        ]

    decision_task["motionsites_candidates"] = selected
    decision_task["creative_mechanism"] = synthesize_mechanism(selected, ctx)
    if decision_task["creative_mechanism"]:
        for fallback in candidate_result["visual_equivalence_fallbacks"]:
            fallback["custom_mechanism"] = decision_task["creative_mechanism"]
    decision_task["visual_equivalence_fallbacks"] = candidate_result["visual_equivalence_fallbacks"]

    warnings: list[str] = []
    if any(c["source_quality"] == "locked_metadata_only" for c in selected):
        warnings.append("Some selected cases are locked metadata only; use them as style references, not original prompts.")
    if any(c["source_quality"] == "generated_reference" for c in selected):
        warnings.append("Some selected cases use generated metadata prompts; do not present them as original MotionSites prompts.")
    if any(c["complexity"] == "high" for c in selected) and not ctx["wants_heavy"]:
        warnings.append("At least one case has high implementation risk; prefer a lightweight adaptation unless the user asks for heavy effects.")
    if decision_task["react_bits_search_recommended"]:
        warnings.append("React Bits entries remain candidates only; MCP/CLI/Registry retrieval never adopts or installs components.")
    if ctx["wants_strong_interaction"]:
        warnings.append("For strong cursor interaction, keep custom cursor state stable on desktop and disable it on touch/mobile.")

    return {
        "query": query,
        "decision_task": decision_task,
        "candidate_requests": candidate_result["candidate_requests"],
        "component_candidates": candidate_result["component_candidates"],
        "adoption_decisions": candidate_result["adoption_decisions"],
        "category_recommendations": candidate_result["category_recommendations"],
        "visual_equivalence_fallbacks": candidate_result["visual_equivalence_fallbacks"],
        "runtime_capabilities": candidate_result["runtime_capabilities"],
        "target_stack": candidate_result["target_stack"],
        "retrieval_attempts": candidate_result["retrieval_attempts"],
        "fallback_used": candidate_result["fallback_used"],
        "restart_required": candidate_result["restart_required"],
        "side_effects": candidate_result["side_effects"],
        "warnings": warnings,
        "diversity_notes": diversity_notes,
    }


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Search the Vibe Upgrader MotionSites case library.")
    parser.add_argument("query", nargs="?", help="User request in Chinese or English. Use '-' to read UTF-8 text from stdin.")
    parser.add_argument("--query-file", help="Read the query from a UTF-8 text file.")
    parser.add_argument("--project-facts", default="", help="Optional plain-text facts from repo inspection, such as stack, entry files, or installed libraries.")
    parser.add_argument(
        "--task-mode",
        choices=["analysis", "proposal", "implementation"],
        help="Override permission-mode inference when the user's authorization is already known.",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Return 1 to 3 cases. Default: 3.")
    parser.add_argument(
        "--upgrade-track",
        choices=["standard", "experimental"],
        help="Override upgrade-track inference when product ambition is already known.",
    )
    parser.add_argument(
        "--prototype-status",
        choices=sorted(PROTOTYPE_STATUSES),
        help="Set the human prototype-gate state. Standard tasks without a gate become not_required.",
    )
    parser.add_argument(
        "--candidates-file",
        help="Optional UTF-8 JSON candidates fixture. Compares supplied candidates without querying or installing anything.",
    )
    parser.add_argument(
        "--retrieval-file",
        help="Optional UTF-8 JSON containing raw MCP, CLI, or Registry results captured by the calling agent.",
    )
    parser.add_argument(
        "--target-root",
        help="Optional target frontend root. Only minimal stack files are inspected before external queries.",
    )
    parser.add_argument(
        "--use-component-cli",
        action="store_true",
        help="Allow read-only shadcn search/view fallback. Never runs add.",
    )
    parser.add_argument(
        "--allow-registry-http",
        action="store_true",
        help="Allow read-only public Registry index fallback after MCP/CLI.",
    )
    parser.add_argument(
        "--mcp-available-in-session",
        action="store_true",
        help="Set only after this Codex session can actually see the shadcn MCP tools.",
    )
    args = parser.parse_args(argv)

    if args.query_file:
        query = Path(args.query_file).read_text(encoding="utf-8").strip()
    elif args.query == "-":
        query = sys.stdin.read().strip()
    elif args.query:
        query = args.query
    else:
        parser.error("query is required unless --query-file is provided")

    component_candidates = load_candidates(Path(args.candidates_file)) if args.candidates_file else None
    raw_retrieval_attempts = load_retrieval_attempts(Path(args.retrieval_file)) if args.retrieval_file else None
    result = search(
        query,
        args.top_k,
        args.project_facts,
        args.task_mode,
        component_candidates,
        raw_retrieval_attempts,
        Path(args.target_root) if args.target_root else None,
        args.use_component_cli,
        args.allow_registry_http,
        args.mcp_available_in_session,
        args.upgrade_track,
        args.prototype_status,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
