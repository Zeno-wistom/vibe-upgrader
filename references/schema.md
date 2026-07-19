# Schema And Provenance

## Data Source

Use only `assets/enriched_cleaned_motionsites_prompts.jsonl`.

Do not crawl MotionSites again from this skill. Do not modify the source data.

## Important Original Fields

- `source_record_id`: Stable local record identifier.
- `prompt_id`, `motion_video_id`, `gradient_id`: Source identifiers when available.
- `title`, `subtitle`, `category`, `visual_type`, `tags`: High-value retrieval fields.
- `page_url`: Source page URL.
- `prompt_raw`: Original prompt body when publicly available.
- `prompt_cleaned`: Cleaned prompt text used by the local library.
- `generated_prompt`: Replacement prompt generated from public metadata.
- `generated_prompt_basis`: Public metadata used to create the generated prompt.
- `prompt_origin`: Either `original_public` or `generated_from_public_metadata`.
- `preview_image`, `preview_video`: Public preview resources when available.
- `tool_hint`: Tool clue such as Framer, Cursor, v0, or stack hints.
- `is_premium`, `is_free`, `is_locked`, `access_status`: Access state.
- `notes`: Important provenance comments.

## Source Quality

Use this derived field in all outputs:

- `original_public`: `prompt_origin=original_public` and `prompt_raw` exists.
- `archive_public`: Prompt text was added from a public archive. Mention that current MotionSites access may differ.
- `generated_reference`: Generated from public metadata. Use only as style/reference material.
- `locked_metadata_only`: Locked or premium record without original prompt text. Use only title, category, tags, public preview, and generated metadata reference.

## Hard Rules

- Never present `generated_prompt` as original MotionSites prompt text.
- Never claim access to locked or premium prompt bodies.
- Prefer original public prompts for complete implementation direction.
- Use Background and Gradient records mostly as atmosphere, background, and motion references.

## Decision Task Schema 3.0

The formal runtime interface is `decision_task`. It adds:

- `upgrade_track`
- `prototype_required`
- `prototype_gate`
- phase-specific `implementation_permissions`
- `creative_mechanism`
- `budget_guardrails`
- `verification_plan`

`motionsites_candidates` live inside `decision_task` and contain source metadata plus inferred mechanism evidence. Derived mechanism fields are labeled as inference and never change the provenance of the underlying prompt.

Legacy top-level task aliases are not part of schema 3.0.
