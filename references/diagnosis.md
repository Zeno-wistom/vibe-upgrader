# Two-Level Diagnosis

Use repository and visual evidence. Do not claim screenshot findings without inspecting the image or running page.

## Before A Standard Change

Inspect only the affected task, entry point, reusable assets, preserved behavior, and likely failure surface. Diagnose the user or product problem before selecting a component.

## Before An Experimental Prototype

Run a blocker scan, not a full audit:

- confirm the target route or isolated surface
- confirm available assets and implementation stack
- record behavior that must remain untouched
- identify obvious mobile, motion, or dependency constraints that could invalidate the concept
- define the five-second visual difference to test

Do not complete a site-wide accessibility, performance, responsive, or maintainability audit before the visual mechanism is accepted.

## After Prototype Approval

Expand diagnosis only around the approved integration:

- information hierarchy and primary task flow
- affected responsive states and real viewport geometry
- keyboard, focus, semantics, labels, contrast, and reduced motion
- runtime cost, asset weight, animation ownership, and cleanup
- state conflicts, loading boundaries, and regression risk

Constraints may simplify the approved mechanism, but must not silently replace it with a lower-ambition generic treatment. Report any necessary downgrade for user approval.

## Evidence Object

Keep it small and allow `unknown`:

```json
{
  "problem": "evidence-backed product or visual problem",
  "affected_surface": "route or component",
  "preserve": ["behavior or asset"],
  "blocking_constraints": ["only confirmed blockers"],
  "five_second_target": "observable success condition",
  "post_approval_checks": ["targeted integration risks"]
}
```
