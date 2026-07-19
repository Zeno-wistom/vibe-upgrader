# React Bits Candidate Source

Treat React Bits as a creative visual and dynamic interaction asset library. Discover candidates broadly; adopt them cautiously.

## Candidate Scope

Consider it for text treatments, animation, backgrounds, hero expression, card interaction, image display, content switching, cursor and mouse feedback, loading, logo animation, carousel, creative navigation, visual focus, and branded motion. This includes ordinary expressive needs, not only liquid glass, mouse-follow, or extreme effects.

Do not use it as the default source for foundational form controls, dialogs, selects, tooltips, or accessibility primitives when the project design system or foundation UI fits better.

## Discovery Versus Adoption

Query React Bits when a diagnosed problem may benefit from an expressive reusable component and the result can inform analysis or planning. Querying does not authorize installation.

Adopt or adapt a candidate only after checking:

- direct fit to the diagnosed problem and page task
- product and brand fit
- framework and styling compatibility
- overlap with current project components
- dependency and runtime cost
- keyboard, focus, screen-reader, and reduced-motion behavior
- mobile and touch fallback
- customization and long-term maintenance cost
- whether the value is more than visual novelty

Reject or use only as inspiration when those checks fail.

## Visual-Equivalence Fallback

Rejecting React Bits is a technical or product decision, not permission to lower the requested visual ambition silently.

For an experimental expressive category:

1. preserve the rejection and its evidence;
2. derive a custom mechanism for the same target, trigger, and visual role using existing project primitives where possible;
3. keep the custom mechanism inside the isolated prototype gate;
4. if equivalent ambition is not feasible, ask the user to approve a specific downgrade.

Do not replace a rejected hero, spatial transition, or signature interaction with generic cards, fades, spacing, or ordinary hover polish and call the gap resolved.

## Source Labels

- `official_registry_component`: verified component from the official React Bits registry.
- `shadcn_mcp_result`: candidate returned by a configured shadcn MCP.
- `third_party_mcp_result`: candidate returned by a third-party MCP; never call it official.
- `manual_reference`: category or search direction that has not been resolved to a verified component.

Never claim installation or verification from a search result alone.

## Runtime Boundary

Use the official free Registry index at `https://reactbits.dev/r/registry.json` through the shadcn MCP/CLI protocol. One shadcn MCP can query both shadcn/ui and React Bits, so do not add a separate third-party React Bits MCP unless it provides a necessary, verified capability the Registry path lacks.

The Codex runtime decides whether MCP is visible. Pass real MCP results to `scripts/component_retrieval.py`; if MCP is unavailable, use read-only shadcn `search`/`view`, then Registry metadata. If none is available, keep the request unresolved; do not invent a candidate.

In analysis and proposal modes, return candidates and any required custom fallback only. In implementation mode, inspect the target first; before experimental prototype approval, do not install or copy an expressive candidate even when general file-edit permission exists.
