<div align="center">

# Vibe-Upgrader

**Make real frontend projects clearer, smoother, and more memorable.**

An Agent Skill for upgrading UI/UX, visual hierarchy, user flows, interaction feedback, and motion language.

[简体中文](./README.md) · [English](./README.en.md)

![Version](https://img.shields.io/badge/version-1.0.0-11110f?style=flat-square) ![License](https://img.shields.io/badge/license-MIT-c8ff4d?style=flat-square&labelColor=11110f)

[Live Showcase](https://vibe-upgrader-showcase.vercel.app/) · [Real-world AIGC case](https://vibe-upgrader-aigc-case.vercel.app/)

</div>

**Quick navigation:** [Start in three steps](#start-in-three-steps) · [Upgrade capabilities](#what-it-can-upgrade) · [Choose a track](#standard-and-experimental) · [Request template](#3-describe-the-upgrade) · [See real results](#see-real-results)

<table>
  <tr>
    <td width="50%" align="center">
      <a href="https://vibe-upgrader-showcase.vercel.app/">
        <img src="./docs/media/showcase_readme_cover.png?v=20260724" alt="Vibe-Upgrader interactive Showcase">
      </a>
      <br>
      <strong>Interactive Showcase</strong><br>
      <sub>Understand what it upgrades, which track to choose, and how to start</sub>
    </td>
    <td width="50%" align="center">
      <a href="https://vibe-upgrader-aigc-case.vercel.app/">
        <img src="./docs/media/aigc_readme_cover.png" alt="Vibe-Upgrader real-world AIGC case">
      </a>
      <br>
      <strong>Real-world AIGC Case</strong><br>
      <sub>A product upgrade delivered inside existing content, brand, and constraints</sub>
    </td>
  </tr>
</table>

## Understand it in 5 seconds

Vibe-Upgrader is built for **frontend projects that already exist**. It first understands the page, goal, scope, and content that must stay, then chooses the right upgrade track and delivers a verifiable result.

| Your question | Answer |
| --- | --- |
| What is it? | A portable, explicitly invoked Skill that follows the open Agent Skills format, not a website template or component pack. |
| What can it upgrade? | Information hierarchy, user flows, state feedback, motion language, responsive behavior, and brand expression. |
| Which Agents are supported? | Codex, Claude Code, and other clients that implement Agent Skills or can load `SKILL.md`. |
| Will it redesign the whole site? | Standard makes controlled changes in the real product; bolder directions begin as an isolated Experimental prototype. |
| How do I start? | Clone the Skill, invoke `$vibe-upgrader`, and describe the page, scope, preserved content, and acceptance criteria. |

## What it can upgrade

| Capability | Common problem | Delivered result |
| --- | --- | --- |
| Information hierarchy | Everything has similar weight, so users do not know where to look first | A clear reading order across the primary task, key data, and supporting information |
| User flow | Frequent tasks require too many steps or have scattered entry points | Fewer steps, a stronger primary action, and a visible next move |
| State feedback | Clicks have no loading, success, failure, or next-step feedback | A complete state chain from action to processing, completion, and continuation |
| Motion language | Animation decorates the page without explaining change | Motion that clarifies state, spatial relationships, and outcomes |
| Responsive and brand | Density breaks across viewports and the interface feels inconsistent | Unified layout, components, rhythm, and brand expression with multi-viewport verification |

## Start in three steps

### 1. Install it in your Agent's Skills directory

Vibe-Upgrader's core follows the open [Agent Skills specification](https://agentskills.io/specification). Each client uses its own directory:

| Agent | User-level directory | Project-level directory | Explicit invocation |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills/vibe-upgrader` | `.agents/skills/vibe-upgrader` | `$vibe-upgrader` |
| Claude Code | `~/.claude/skills/vibe-upgrader` | `.claude/skills/vibe-upgrader` | `/vibe-upgrader` |

macOS / Linux:

```bash
# Codex
git clone https://github.com/Zeno-wistom/vibe-upgrader.git ~/.agents/skills/vibe-upgrader

# Claude Code
git clone https://github.com/Zeno-wistom/vibe-upgrader.git ~/.claude/skills/vibe-upgrader
```

Windows PowerShell：

```powershell
# Codex
git clone https://github.com/Zeno-wistom/vibe-upgrader.git "$env:USERPROFILE\.agents\skills\vibe-upgrader"

# Claude Code
git clone https://github.com/Zeno-wistom/vibe-upgrader.git "$env:USERPROFILE\.claude\skills\vibe-upgrader"
```

For other clients, use their documented Agent Skills directory and invocation syntax. Format compatibility does not guarantee identical browser, component-retrieval, or filesystem capabilities in every Agent.

### 2. Invoke it explicitly

Codex：

```text
$vibe-upgrader
```

Claude Code：

```text
/vibe-upgrader
```

Installing the Skill does not allow it to intervene in unrelated frontend work. The full workflow starts only when explicitly invoked.
### 3. Describe the upgrade

Use these five fields for a more reliable result. The example below uses Codex; replace the first line with `/vibe-upgrader` in Claude Code:

```text
$vibe-upgrader

Page: the page or area to upgrade
Goal: the task users struggle to complete
Scope: what may change in this iteration
Preserve: content, logic, brand, or components that must stay
Acceptance: how the finished upgrade will be judged
```

For example:

```text
$vibe-upgrader

Page: search, filtering, and bulk actions in the dashboard
Goal: help users find target records and process them faster
Scope: change only the list toolbar and its related feedback
Preserve: the current data model, list, and permission logic
Acceptance: clear desktop and mobile flows, keyboard access, passing build, and a clean console
```

> [!TIP]
> If you are unsure which track to choose, describe the real goal and constraints. Vibe-Upgrader defaults to Standard and enters Experimental only when the task clearly requires a strong visual direction or non-standard interaction.

<details>
<summary><strong>Update an existing installation</strong></summary>

macOS / Linux:

```bash
# Codex
git -C ~/.agents/skills/vibe-upgrader pull --ff-only

# Claude Code
git -C ~/.claude/skills/vibe-upgrader pull --ff-only
```

Windows PowerShell：

```powershell
# Codex
git -C "$env:USERPROFILE\.agents\skills\vibe-upgrader" pull --ff-only

# Claude Code
git -C "$env:USERPROFILE\.claude\skills\vibe-upgrader" pull --ff-only
```

</details>

## Standard and Experimental

| | Standard | Experimental |
| --- | --- | --- |
| Best for | Dashboards, tools, content products, and existing business surfaces | Brand heroes, narrative pages, and non-standard interaction |
| Approach | Preserve the architecture and solve the most important experience problems | Validate one strong mechanism in an isolated environment |
| Delivery | Implement and verify directly inside a controlled scope | Deliver one runnable prototype first |
| Boundary | Stop when the task acceptance criteria are met | Integrate only after an `approved / revise_once / rejected` human gate |

**Selection rule:** use Standard for real product work; use Experimental when the visual direction itself must be proven before integration.

<details>
<summary><strong>View two copy-ready prompts</strong></summary>

### Standard

```text
$vibe-upgrader

Upgrade the search, filtering, and bulk-action area of this dashboard.
Keep the rest of the page stable and do not redesign the whole product.
Verify desktop, mobile, keyboard operation, and the browser console.
```

### Experimental

```text
$vibe-upgrader

Explore a more immersive way to browse this digital archive.
Build one core interaction mechanism in an isolated preview.
Do not integrate it into the production page until I approve it.
```

</details>

## How it works

![Vibe-Upgrader four-step workflow](./docs/media/workflow-overview-en.svg?v=20260724)


The formal `decision_task` 3.0 records permission mode, upgrade track, provenance, component decisions, prototype status, and verification boundaries. It makes the reasoning, implementation scope, and evidence inspectable instead of leaving only a page that looks different.

## See real results

### Interactive Showcase

[Open the live Showcase →](https://vibe-upgrader-showcase.vercel.app/)

The Showcase uses hands-on demonstrations to explain four things:

1. What changes in the same product before and after an upgrade;
2. How information hierarchy, user flow, state feedback, and motion language differ;
3. When to choose Standard or Experimental;
4. How a real request becomes a verifiable delivery.

![Drag to compare the interface before and after the upgrade](./docs/media/showcase_interaction.gif?v=20260724)

<details>
<summary>View desktop and mobile screenshots</summary>

![Showcase desktop](./docs/media/showcase_desktop.png?v=20260724)

![Showcase mobile](./docs/media/showcase_mobile.png?v=20260724)

</details>

### Real-world AIGC case

[Open PINK SIGNALS →](https://vibe-upgrader-aigc-case.vercel.app/)

PINK SIGNALS already had seven finished artworks, an established visual identity, and strict content constraints. Vibe-Upgrader preserved the work and disclosure language while improving portfolio browsing, full-screen detail navigation, visual hierarchy, responsive behavior, and the isolated Signal experience.

All people, scenes, and profile-like material in this case are fictional AIGC-generated content. They do not depict real individuals or real dating profiles.

## Guardrails

- User authorization and verified project facts define the modification scope.
- Standard keeps real business behavior and the existing architecture stable.
- Experimental begins with an isolated prototype and a human visual gate.
- External references and components require provenance, a fit decision, and a fallback.
- Runtime use leaves the installed Skill directory unchanged.
- A passing build proves that the project runs; real reading and human judgment still determine visual quality.

## Repository structure

```text
vibe-upgrader/
├── SKILL.md          # Skill entry point and track routing
├── agents/           # Optional Codex / OpenAI metadata; SKILL.md remains the core entry
├── scripts/          # Decision, retrieval, installation, and search helpers
├── references/       # Protocol, provenance boundaries, and verification guidance
├── assets/           # Redistributable aliases only; local corpus excluded
├── tests/            # Workflow and runtime-write regressions
└── docs/media/       # README media
```

## Requirements and compatibility

- The core layout follows the open [Agent Skills specification](https://agentskills.io/specification), with a standard `SKILL.md` entry point.
- [Codex](https://developers.openai.com/codex/skills) uses `.agents/skills` and supports explicit `$vibe-upgrader` invocation.
- [Claude Code](https://code.claude.com/docs/en/skills) uses `.claude/skills` and supports explicit `/vibe-upgrader` invocation.
- Other clients that implement Agent Skills or can load `SKILL.md` can reuse the core Skill; available tools and invocation syntax remain client-specific.
- The core instructions do not require Node.js. Python **3.10+** is required for optional helper scripts and validation tools.
- Node.js is used only when the user opts into a compatible component CLI or Registry workflow.
## License and third-party boundaries

Vibe-Upgrader's original code and documentation are released under the [MIT License](./LICENSE).

- [MotionSites](https://motionsites.ai/) is an external creative-reference source. The complete local corpus is not included because bulk-redistribution authorization could not be confirmed. Without that optional source, the Skill reports the limitation and continues with component evaluation or a custom fallback.
- [React Bits](https://github.com/DavidHDev/react-bits) is an optional component source. This repository bundles no React Bits component source; React Bits uses its own MIT + Commons Clause terms.
- The Showcase and AIGC case are separate projects with their own dependency and asset-provenance boundaries.

See [CHANGELOG.md](./CHANGELOG.md) and the [v1.0.0 Release](https://github.com/Zeno-wistom/vibe-upgrader/releases/tag/v1.0.0).
