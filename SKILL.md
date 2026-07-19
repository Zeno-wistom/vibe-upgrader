---
name: vibe-upgrader
description: "Upgrade real frontend projects through one of two explicit tracks: standard UI/UX improvement for hierarchy, usability, content, controls, and brand polish; or experimental visual work for immersive, high-impact, signature motion and non-standard interaction. Use only when the user explicitly invokes $vibe-upgrader or explicitly requests its full workflow. Preserve project facts and permission boundaries, prototype experimental mechanisms before integration, and use MotionSites, React Bits, foundation UI, existing assets, or custom work only when their responsibility fits the task."
---

# Vibe Upgrader

Treat the current product, repository, supplied visuals, and user constraints as controlling facts. Optimize for the requested outcome, not for the largest audit or the longest proof trail.

## Route The Task First

Set two independent values before searching or editing:

1. **Permission mode**: `analysis`, `proposal`, or `implementation`.
2. **Upgrade track**:
   - `standard`: improve usability, hierarchy, navigation, forms, content, feedback, responsive behavior, or brand polish.
   - `experimental`: create immersive visual work, digital-art behavior, a signature motion system, strong visual impact, or non-standard interaction.

Default to `standard` when the request does not require an experimental experience. Read `references/modes.md` when either value is ambiguous.

## Follow The Track

### Standard

1. Inspect only the product facts and affected surfaces needed for the request.
2. Diagnose the concrete user or product problem.
3. Reuse current components or foundation UI when they fit.
4. Query MotionSites or expressive components only for a confirmed creative gap.
5. Implement authorized scoped changes directly. Use a prototype only for a broad redesign or unresolved visual direction.
6. Run targeted verification for affected behavior and stop.

### Experimental

1. Inspect only the entry point, existing assets, stack, preserved behavior, and obvious blockers.
2. Retrieve at most three MotionSites references and translate them into one implementable high-leverage mechanism. Do not stop at style adjectives.
3. Compare expressive components only when they can materially accelerate that mechanism. If a React Bits or external candidate is rejected, produce a custom mechanism with equivalent visual ambition or ask the user to accept an explicit downgrade.
4. In `implementation`, build one isolated route, component, or scene. Do not integrate the full site, install a new expressive dependency, or expand the audit before approval.
5. Verify only that the prototype runs: same-viewport before/after evidence, one desktop viewport, one mobile viewport, build, and console.
6. Stop at the human visual gate. Continue to integration only after the user approves the prototype.
7. After approval, integrate deliberately and run relevant responsive, keyboard, reduced-motion, performance, and task-flow regression checks.

Read `references/diagnosis.md` for the two-level diagnosis boundary and `references/real_project_test.md` for the two-track acceptance protocol.

## Keep The Human Gate Real

For experimental work, automated checks prove that the prototype runs; they do not prove that it is visually successful. Require a human result of `approved`, `revise_once`, or `rejected`.

- `not_started` or `built`: block full integration, component installation, and expressive dependency changes.
- `approved`: allow authorized integration and targeted full verification.
- `rejected`: preserve the original product and stop or replace the mechanism only when requested.

One prototype may receive one targeted revision. More iterations require a new user decision.

## Route Sources By Responsibility

1. **Current project**: product, content, brand, stack, existing components, and constraints.
2. **Foundation UI**: reliable controls, navigation, forms, dialogs, layout, and feedback.
3. **MotionSites**: concrete creative mechanisms, composition, rhythm, atmosphere, and narrative reference.
4. **React Bits**: optional implementable expressive candidates, never a required dependency.
5. **Custom build**: the required creative fallback when external expressive candidates do not fit.

Do not query every source. Read `references/retrieval.md` only when a normalized decision task, MotionSites reference, or external candidate is useful. Read `references/component-decision-framework.md` before comparing candidates and `references/react_bits.md` when React Bits is plausible.

## Use The Helpers Deliberately

Generate the sole formal task protocol:

```bash
python -B vibe-upgrader/scripts/search_motionsites.py "request" --project-facts "verified stack and project facts"
```

Use `--upgrade-track standard|experimental`, `--task-mode analysis|proposal|implementation`, and `--prototype-status not_started|built|approved|rejected` when those facts are already known. The result's `decision_task` controls the workflow.

When real component candidates are needed, keep retrieval read-only:

```bash
python -B vibe-upgrader/scripts/component_retrieval.py --decision-task decision-task.json --raw-results captured-results.json --target-root path/to/frontend
python -B vibe-upgrader/scripts/component_decision.py --decision-task decision-task.json --candidates candidates.json
```

Retrieval never runs `add`, installs a component, or approves adoption. Keep `configured`, `available_in_session`, and `verified_by_call` separate. Leave unsupported accessibility, performance, license, responsive, and maintenance claims as `unknown`.

## Preserve Provenance

- Prefer `original_public` or `archive_public` MotionSites evidence.
- Treat generated or locked metadata as reference material, never as an original prompt.
- Label MCP, CLI, Registry, fixture, and project-inspection evidence accurately.
- Never claim that a component was installed or verified unless that action occurred.

Read `references/schema.md` before making source claims and `references/taxonomy.md` only when interpreting derived MotionSites fields.

## Control Cost And Output

Use one plan, one reference pass, one primary mechanism, and one concise report per phase. Reuse evidence already collected in the same phase.

- Prototype soft budget: 180k tokens when telemetry exists; stop at the human gate by 250k.
- Integration soft budget: 300k tokens in a separate approved phase.
- Without telemetry: at most three references, one prototype, two viewports, and one report before approval.

Read `references/output_format.md` before reporting. Do not emit search-command inventories, exhaustive source tables, broad audits, or large screenshot matrices unless the user requests them or they are required by the approved integration risk.
