# Output Format

Report only the current phase. Do not repeat project history or evidence already established in the same phase.

## Standard

```text
- Track and permission
- Concrete problem and chosen path
- Changed or proposed surface
- Targeted verification and remaining risk
```

## Experimental Before Approval

```text
- Track, permission, and prototype-gate status
- One high-leverage mechanism
- Reference evidence and the concrete behavior borrowed
- Isolated prototype location
- Same-viewport five-second result
- Minimal runtime checks
- Human decision needed: approve, revise once, or reject
```

Stop after the human decision request. Do not append a full integration plan unless the user asked for one.

## Experimental After Approval

```text
- Approved mechanism and integration boundary
- Main implementation decisions
- Relevant responsive, accessibility, reduced-motion, performance, and regression evidence
- Unverified risks or approved downgrades
```

## Evidence Rules

- For MotionSites, state provenance and the actual mechanism borrowed; omit search-command inventories by default.
- For external components, state source, action, rejection or adoption reason, and custom equivalent fallback when required.
- When retrieval ran, distinguish configured, available in session, verified by call, fallback used, unresolved requests, and side effects.
- Never call retrieval adoption, installation, or verification.
