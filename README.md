# Smart Video Splitter

A Codex skill that divides a silent or visual-first video into consecutive clips. It detects visual scene changes near evenly spaced target times, then falls back to exact equal-time boundaries when no natural cut is available.

## Typical use

For a one-minute product video, the default command creates three sequential clips of approximately 20 seconds each:

```bash
python3 scripts/smart_split.py input.mp4 --parts 3 --mode smart --output-dir output
```

The result contains:

```text
output/
├── part_01.mp4
├── part_02.mp4
├── part_03.mp4
└── split_report.json
```

## Modes

- `smart`: selects scene changes near equal-duration targets.
- `exact`: splits at mathematically equal time points.

## Requirements

- Python 3.9+
- FFmpeg and FFprobe available on `PATH`
- No Python packages are required

## Options

```text
--parts N                 Number of clips; default 3
--mode smart|exact        Split mode; default smart
--scene-threshold 0.30    Scene-change sensitivity
--search-window 6         Seconds around each target to search
--copy-audio              Preserve an existing audio track
--output-dir PATH         Output directory
```

For a continuous shot with no detectable visual transitions, `smart` mode automatically uses equal-time boundaries.

## Install as a Codex skill

Place the repository folder in your Codex skills directory, or install it from GitHub using the Codex Skill Installer.

## Test

```bash
python3 -m unittest discover -s tests -v
```

