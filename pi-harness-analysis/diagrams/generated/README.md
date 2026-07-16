# Reader Illustrations

This directory is the optional reader-facing raster layer for the Pi report. The prompts are compiled from the same recovered architecture used by `diagrams/story-specs.json`, but generated images are not architectural truth and must never be the only retained figure.

For every generated PNG:

1. Keep the HIR, claims/evidence, story spec, and Mermaid source model.
2. Verify every label, arrow, component count, optional-path style, and boundary against the prompt and story spec.
3. Reject any image that invents a component, changes direction, turns an optional path into a default path, or adds unsupported behavior.
4. Display the PNG as the report figure and link its caption to generated metadata, HIR, and evidence IDs.
5. Record the model, size, quality, prompt file, generation time, and review result in `metadata.json`.

The local generator expects `OPENAI_BASE_URL`/`OPENAI_API_KEY` or `OAI_BASE_URL`/`OAI_API_KEY`. Do not store either credential in this analysis bundle.

Recommended generation settings: `gpt-image-2`, `1536x1024`, `high`, PNG. Generate and review `01-system-overview.txt` first; only batch the remaining prompts after its text and architecture pass inspection.
