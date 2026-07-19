# Permission Modes And Upgrade Tracks

Keep permission and product ambition independent.

## Permission

- `analysis`: inspect, diagnose, retrieve, and compare without project writes or installation.
- `proposal`: define direction, mechanism, candidate choice, and implementation plan without project writes or installation.
- `implementation`: make explicitly authorized changes. Experimental work is still limited by the prototype gate.

If permission language conflicts, choose the less permissive mode.

## Track

- `standard`: the main value is usability, hierarchy, task completion, content clarity, responsive repair, component consistency, or measured brand polish.
- `experimental`: the main value is visual impact, immersion, digital-art behavior, signature motion, spatial transformation, or non-standard interaction.

Default to `standard`. Choose `experimental` only from explicit ambition or unmistakable task evidence. Ask one question only when the track changes scope materially and the request provides no safe default.

## Prototype Gate

Use these states:

- `not_required`: standard scoped work may proceed under its permission mode.
- `not_started`: an experimental or broad-redesign prototype is required.
- `built`: the isolated prototype exists but has not passed human review.
- `approved`: the user accepted the visual mechanism; authorized integration may proceed.
- `rejected`: do not integrate the mechanism.

Before `approved`, experimental implementation may edit only the isolated prototype surface and the minimum route or fixture needed to expose it. Block full integration, expressive component installation, and new expressive dependencies.

## Examples

- "Fix this settings form hierarchy" → `standard` plus the permission inferred from the verb.
- "Make this portfolio feel like an immersive digital artwork" → `experimental`.
- "Audit why the hero feels generic" → `analysis`; choose `experimental` only if the requested outcome explicitly demands a signature visual experience.
- "The prototype is approved; integrate it" → `experimental`, `implementation`, `approved`.
