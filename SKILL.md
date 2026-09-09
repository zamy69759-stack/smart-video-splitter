---
name: smart-video-splitter
description: Split a silent or visual-first video into consecutive clips by detecting scene changes near evenly spaced target times. Use when the user wants one video divided into multiple approximately equal clips without relying on speech or audio. Do not use for highlight compilations or three alternative edits of the same footage.
---

# Smart Video Splitter

Divide one source video into consecutive, non-overlapping clips. Prefer natural visual boundaries near equal-duration targets, while preserving the full source from beginning to end.

## Requirements

- The runtime must provide `python3`, `ffmpeg`, and `ffprobe` on `PATH`.
- The source must be a local video file.
- Audio is not used for analysis. Output is silent by default.

## Workflow

1. Confirm the source path and requested number of clips. Default to 3 clips when omitted.
2. Choose a mode:
   - `smart` (default): detect scene changes and choose boundaries nearest the equal-duration targets.
   - `exact`: split only at mathematically equal time points.
3. Run:

   ```bash
   python3 scripts/smart_split.py INPUT --parts 3 --mode smart --output-dir OUTPUT_DIR
   ```

4. Read `split_report.json` in the output directory. Verify that:
   - all requested clips exist;
   - clip boundaries are consecutive and non-overlapping;
   - the first clip begins at 0;
   - the final clip ends at the source duration;
   - total reported duration approximately equals the source duration.
5. Return the clips and report to the user. State actual durations because smart boundaries may not be exactly equal.

## Defaults and decisions

- Use `smart` for product footage, demonstrations, travel footage, and other silent videos.
- The script searches around each equal target for a scene boundary. If none is suitable, it falls back to the exact target.
- Use `--search-window 6` for roughly one-minute videos. Reduce it when equal durations matter more; increase it when visual continuity matters more.
- Use `--scene-threshold 0.30` by default. Lower values detect more visual changes; higher values accept only stronger cuts.
- Use `--copy-audio` only when the user explicitly wants an existing audio track preserved.

## Boundaries

- This skill creates sequential parts, not highlight reels.
- It does not infer narrative meaning from silent footage; it identifies visual transitions and balances duration.
- If the source is one continuous shot, scene detection may find no useful boundary and the result will fall back to equal splitting.
- Never overwrite the source file. Use a separate output directory.

