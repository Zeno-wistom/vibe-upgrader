# Taxonomy

## Derived Fields

### `page_module`

Values: `hero`, `landing_page`, `features`, `pricing`, `cta`, `footer`, `about`, `portfolio`, `dashboard`, `form`, `background`, `gradient`, `component`.

Infer from `item_kind`, `category`, `visual_type`, `title`, and `tags`.

Use this to decide which page area the case can upgrade.

### `visual_style`

Values: `glassmorphism`, `liquid_glass`, `3d`, `cinematic_dark`, `editorial`, `neon`, `gradient`, `minimal`, `brutalist`, `luxury`, `naturecore`, `retro_futurist`, `polished_modern`.

Infer from tags, title, prompt text, and `taxonomy_aliases.json`.

Use this to match requests like premium, liquid glass, Apple-like, cinematic, or tech.

### `interaction_pattern`

Values: `hover_transform`, `scroll_reveal`, `carousel`, `tabs`, `accordion`, `sticky_cards`, `cursor_follow`, `micro_interaction`, `none`.

Use this to upgrade feedback and interaction quality.

### `motion_type`

Values: `background_loop`, `gradient_motion`, `3d_orbit`, `parallax`, `text_reveal`, `card_motion`, `video_hero`, `transition`, `none`.

Use this to decide animation direction and risk.

### `layout_pattern`

Values: `full_bleed_hero`, `split_hero`, `bento_grid`, `card_grid`, `centered_editorial`, `dashboard_shell`, `section_stack`, `carousel_strip`.

Use this to turn references into concrete layout instructions.

### `implementation_stack`

Values: `react_tailwind`, `react_framer_motion`, `react_three`, `gsap`, `shadcn`, `html_css_js`, `framer`, `v0`, `cursor`, `unknown`.

Use this to avoid recommending work that does not fit the user's project.

### `industry_or_domain`

Values: `ai_saas`, `agency`, `portfolio`, `fintech`, `ecommerce`, `web3`, `health`, `travel`, `media`, `plugin`, `generic`.

Use this to avoid brand mismatch.

### Risk Fields

- `complexity`: `low`, `medium`, `high`.
- `mobile_risk`: `low`, `medium`, `high`.
- `performance_risk`: `low`, `medium`, `high`.

Default to lightweight upgrades when risk is high unless the user explicitly asks for strong effects.

## Upgrade Dimensions

Values:

- `visual_impact`
- `layout_depth`
- `motion_rhythm`
- `interaction_feedback`
- `background_atmosphere`
- `brand_fit`
- `content_hierarchy`

Use these to connect diagnosis to retrieval.
