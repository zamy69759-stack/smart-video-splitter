---
name: smart-video-splitter
description: Split a video into consecutive approximately equal clips using speech pauses when audio exists and visual scene changes when it does not. Use for spoken, silent, product, demonstration, or visual-first videos that must be divided without cutting at arbitrary moments. Do not use for highlight compilations or alternative edits of the same footage.
---

# Smart Video Splitter

Divide one source video into consecutive, non-overlapping clips while preserving the full source. Automatically adapt the analysis to videos with or without audio.

## Requirements

- The runtime must provide `python3`, `ffmpeg`, and `ffprobe` on `PATH`.
- The source must be a local video file.
- No Python packages are required.

## Workflow

1. Confirm the source path and requested number of clips. Default to 3 clips.
2. Use `auto` unless the user requests another mode:
   - With audio: identify speech pauses near equal targets, then fall back to scene changes.
   - Without audio: identify visual scene changes.
   - With no natural boundary: use the equal-duration target.
3. Run:

   ```bash
   python3 scripts/smart_split.py INPUT --parts 3 --mode auto --output-dir OUTPUT_DIR
   ```

4. Read `split_report.json`. Verify every clip exists, boundaries are consecutive, the first begins at 0, the last ends at the source duration, and source audio was preserved unless the user requested silent output.
5. Return all clips and report actual durations and boundary sources.

## Modes and options

- `auto` (default): speech pauses, then scene changes, then equal fallback.
- `audio`: speech pauses only; requires an audio stream.
- `visual`: scene changes only.
- `exact`: mathematically equal points.
- `--search-window 6`: search radius around each equal target.
- `--minimum-silence 0.30`: shortest pause accepted as a possible boundary.
- `--silence-db -35`: silence threshold; lower for quiet recordings, higher for noisy ones.
- `--scene-threshold 0.30`: visual change sensitivity.
- `--audio-output auto|keep|drop`: preserve source audio automatically by default.

## Boundaries

- Speech handling is pause-aware, not semantic transcription. It reduces mid-sentence cuts but does not understand spoken meaning.
- This skill creates sequential parts, not highlight reels.
- Continuous speech and a continuous shot may force an equal-time cut.
- Never overwrite the source. Use a separate output directory.

