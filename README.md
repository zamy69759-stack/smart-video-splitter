# Smart Video Splitter

A Codex skill that divides videos into consecutive clips. It automatically detects whether the source has audio, prefers speech pauses for spoken videos, uses scene changes for silent videos, and falls back to equal-time boundaries when no natural cut is available.

## Typical use

For a one-minute product video, the default command creates three sequential clips of approximately 20 seconds each:

```bash
python3 scripts/smart_split.py input.mp4 --parts 3 --mode auto --output-dir output
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

- `auto`: prefers speech pauses when audio exists, then scene changes.
- `audio`: uses speech pauses only.
- `visual`: uses scene changes only.
- `exact`: splits at mathematically equal time points.

## Requirements

- Python 3.9+
- FFmpeg and FFprobe available on `PATH`
- No Python packages are required

## Options

```text
--parts N                 Number of clips; default 3
--mode auto|audio|visual|exact
--scene-threshold 0.30    Scene-change sensitivity
--search-window 6         Seconds around each target to search
--minimum-silence 0.30    Minimum speech-pause duration
--silence-db -35          Audio silence threshold
--audio-output MODE       auto, keep, or drop; default auto
--output-dir PATH         Output directory
```

Source audio is preserved automatically. Pause analysis does not transcribe or semantically understand speech; it finds natural gaps to reduce mid-sentence cuts. If no usable pause or scene change exists, the script uses equal-time boundaries.

## Install as a Codex skill

Place the repository folder in your Codex skills directory, or install it from GitHub using the Codex Skill Installer.

## Test

```bash
python3 -m unittest discover -s tests -v
```
