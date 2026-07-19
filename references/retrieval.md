# Retrieval And Decision Protocol

Use `scripts/search_motionsites.py` only when a normalized task, creative reference, or external candidate is useful. The helper reads the bundled dataset and never installs anything.

## Formal Interface

Treat `decision_task` schema `3.0` as the sole formal task protocol. Old top-level aliases such as `mode`, `react_bits_needed`, `external_effect_queries`, and `top_cases` are removed.

Read these fields first:

- `task_mode`: permission boundary
- `upgrade_track`: `standard` or `experimental`
- `prototype_required` and `prototype_gate`: whether full integration is blocked
- `implementation_permissions`: prototype, integration, installation, dependency, and verification permissions
- `creative_reference_needed`: whether MotionSites should run
- `motionsites_candidates`: one to three reference records when needed
- `creative_mechanism`: one synthesized implementation mechanism, not a style summary
- `component_opportunities` and `candidate_requests`: unresolved component needs
- `budget_guardrails` and `verification_plan`: phase cost and evidence limits

## MotionSites Mechanism Contract

Each selected record must expose inferred mechanism evidence:

- trigger or control source
- key state changes
- spatial or layout relationship
- implementation primitives
- provenance and inference label

Synthesize one `creative_mechanism` containing:

- mechanism name and target surface
- source records and concrete behavior borrowed from each
- trigger
- at least three key states
- spatial transformation
- implementation primitives compatible with known project facts
- same-viewport five-second difference target
- mobile and reduced-motion fallback

Reject output that contains only adjectives such as premium, editorial, cinematic, asymmetric, polished, or dynamic without describing what changes and how it is controlled.

Use one to three cases. Prefer original or archived public evidence. Generated or locked metadata may support atmosphere but cannot be presented as original prompt text.

## Track Routing

### Standard

Do not query MotionSites or React Bits merely because the page is a marketing page. Query them only for an explicit creative direction or a confirmed expressive gap. Current components and foundation UI remain the normal path.

### Experimental

Query MotionSites once and retrieve at most three cases. Generate one mechanism before external component retrieval. Search React Bits only if a reusable candidate can implement that mechanism more efficiently than current primitives or custom work.

Before prototype approval, keep `full_integration`, `install_components`, and `add_dependencies` false. Existing project code may be changed only for the isolated prototype surface when permission mode is `implementation`.

## Component Retrieval

Use this handoff:

```text
decision_task
→ candidate_requests
→ visible MCP or read-only CLI/Registry
→ component_retrieval.py
→ component_candidates
→ component_decision.py
→ adoption_decisions and visual_equivalence_fallbacks
```

Fallback order: visible MCP → shadcn CLI `search`/`view` → public Registry metadata → unresolved. Never run `shadcn add` during retrieval.

Keep `configured`, `available_in_session`, and `verified_by_call` separate. Registry identity, files, and dependencies do not prove accessibility, performance, license compatibility, responsive behavior, or maintenance quality; leave those values `unknown` until evidenced.

For a confirmed non-React target, skip React Bits retrieval and preserve the incompatibility reason.

## Visual-Equivalence Rule

For expressive categories in the experimental track, a rejected or deferred external candidate cannot end the creative path. The decision result must contain either:

- a viable `custom_build` winner for the same category, or
- a `visual_equivalence_fallback` describing a custom mechanism at equivalent ambition and requiring human confirmation before any downgrade.

Foundation or ordinary layout polish is not an equivalent fallback for a rejected signature visual mechanism.

## Cost And Side Effects

- Run at most one MotionSites pass per phase.
- Default to three results; allow one or two when sufficient.
- Inspect only minimal stack files before external queries.
- Do not write target files, create `components.json`, install packages, or claim adoption during retrieval.
- Report actual retrieval attempts, restart requirement, unresolved requests, and side effects without repeating long source inventories.
