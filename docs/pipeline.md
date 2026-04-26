# Pipeline Breakdown

## Goal

Take one gameplay mockup and produce a Godot-ready asset folder.

## Final Pattern

```text
mockup
→ vision analysis
→ asset manifest
→ human approval
→ optional segmentation/reference extraction
→ prompt generation
→ image generation candidates
→ human approval
→ variant generation
→ validation
→ export
```

## What Is Automated?

- Vision analysis can be automated by a multimodal model.
- Manifest creation can be automated, then reviewed.
- Segmentation can be automated by SAM/SAM2.
- Prompt generation can be automated.
- Image generation can be automated via ComfyUI or a hosted API.
- Validation and export should be normal deterministic Python code.

## What Should Stay Human?

Taste decisions: choosing which candidate looks like your game.

## Why the Manifest Matters

The manifest is the source of truth. It determines:

- what gets generated
- target dimensions
- variants
- destination folders
- whether text should be baked into the image

## Important Rule

Do not rely on segmentation as final production art. Use segmentation for references/placeholders. Use generation/refinement for final candidates.
