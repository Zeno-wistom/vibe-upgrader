# Component Decision Framework

## Source Responsibilities

| Source | Primary role | Default priority | Must not decide |
| --- | --- | --- | --- |
| Product and project context | Goals, users, task, content, brand, stack, constraints | Highest | Nothing external may override it |
| Existing project components | Reuse and consistency | First component check | Do not preserve a clearly inadequate component |
| Foundation UI and design systems | Controls, forms, navigation, layout, accessible behavior | Before new expressive libraries for basic UI | Do not set the page's creative direction alone |
| React Bits | Creative visual and dynamic interaction candidates | Query when an expressive reusable solution may fit | Do not become mandatory or bypass adoption checks |
| MotionSites | Creative and visual references | Only when external art-direction reference helps | Do not choose code, dependencies, accessibility, or files |
| Custom implementation | Purpose-built solution when it fits best | After comparison, not automatically last | Do not default to hand-writing everything |

## Candidate Comparison

Compare each plausible option against:

1. problem and page-task fit
2. product-positioning and brand fit
3. stack compatibility and conflict with current assets
4. dependency size and performance cost
5. responsive, touch, and reduced-motion behavior
6. keyboard, focus, semantics, and screen-reader support
7. customization effort and maintenance cost
8. whether its visual ambition matches the selected track and solves the stated problem

Normalize every candidate to the source-neutral protocol implemented in `scripts/component_decision.py`. Keep field-level evidence as `verified_fact`, `reported_fact`, `inference`, or `unknown`; unknown values never inherit a safe or high-fit default.

Supported sources: `existing_project`, `existing_design_system`, `foundation_ui`, `react_bits`, `external_component`, and `custom_build`.

Choose one action and state why: `reuse`, `adapt`, `install`, `custom_build`, `reject`, or `defer`.

## Decision Layers

Apply hard gates before comparison:

- stack compatibility
- availability
- license status
- problem and product-task fit
- design-system consistency
- accessibility risk
- performance cost
- dependency value
- permission to execute changes

A failed gate may reject, defer, require adaptation or degradation, or block execution while still allowing an analysis-mode recommendation. Do not hide gates inside a total score.

In the experimental track, a failed expressive candidate also activates the visual-equivalence rule. Keep the rejection, but do not leave the expressive category empty: select a viable custom candidate or emit a custom fallback mechanism at equivalent ambition. Any reduction in ambition requires a human decision.

For candidates that remain viable, compare in this order:

1. problem and product fit
2. brand fit
3. accessibility, performance, dependency, and maintenance risk
4. evidence quality
5. page-context source preference

Source priority is a final contextual tie-breaker, not a fixed winner. Existing systems receive stronger preference in operational and enterprise pages; React Bits and custom work may lead expressive marketing categories when their fit and risk are better.

The pipeline is:

```text
decision_task
→ candidate_requests
→ MCP/CLI/Registry retrieval or real project inspection
→ component_retrieval.py evidence normalization
→ component_candidates
→ hard gates
→ ordered comparison
→ adoption_decisions
→ visual_equivalence_fallbacks for unresolved experimental categories
```

## Source Routing Examples

- Dense SaaS settings form: inspect current form and layout components, then foundation UI. Skip MotionSites unless a new visual direction is explicitly requested. Query React Bits only for a real expressive feedback or loading opportunity.
- Product marketing homepage: use product goals first. Query MotionSites or React Bits only for an explicit creative gap; when the track is experimental, convert the reference into one mechanism and prototype it before integration.
- Mature enterprise design system: reuse and adapt the system first. Limit external sources to evidence or isolated candidates that can be restyled without fragmenting the system.

## Calibration Scenarios

### SaaS settings page

- Diagnosis: hierarchy, form density, action priority, and operation feedback are the primary problems.
- Query: current components and foundation UI. Do not query MotionSites by default. Query React Bits only if a specific feedback or loading pattern remains unsolved.
- Decision: reuse or adapt form sections, spacing, button hierarchy, validation, toast, and saving state. Reject decorative motion that slows repeated tasks.
- Path: information architecture → current components → foundation UI gap fill → lightweight feedback → accessibility and responsive checks.

### Product marketing homepage

- Diagnosis: weak brand expression, unclear product story, missing hero focus, and low memorability.
- Query: product context, MotionSites art-direction references, foundation navigation and CTA, React Bits expressive candidates, and custom brand treatment.
- Decision: use MotionSites as reference only; shortlist React Bits hero, text, background, image, or carousel candidates; adopt only those that pass brand, performance, mobile, and accessibility checks; custom-build the brand-specific composition.
- Path: product message → track decision → concrete mechanism → isolated prototype when required → human approval → authorized integration.

### Enterprise admin with a mature design system

- Diagnosis: local feedback, empty state, loading, and cross-page consistency issues.
- Query: existing design-system components and usage patterns first. Use foundation sources only for unresolved primitives. Query external creative components narrowly and keep them theme-compatible.
- Decision: reuse or extend the existing system. Reject external components that introduce a second visual language or redundant dependency.
- Path: design-system audit → pattern correction → missing state components → isolated enhancement if justified → consistency and accessibility checks.
