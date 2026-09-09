#!/usr/bin/env python3
"""Split a video into consecutive clips near natural scene boundaries."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


PTS_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"Missing required command(s): {', '.join(missing)}")


def probe_duration(source: Path) -> float:
    result = run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(source),
        ],
        capture=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError("Video duration must be greater than zero")
    return duration


def detect_scene_times(source: Path, threshold: float) -> list[float]:
    expression = f"select=gt(scene\\,{threshold}),showinfo"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-vf", expression, "-an", "-f", "null", "-"],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Scene detection failed")
    return sorted({float(match.group(1)) for match in PTS_RE.finditer(result.stderr)})


def choose_boundaries(
    duration: float,
    parts: int,
    scene_times: list[float],
    search_window: float,
) -> list[float]:
    if parts < 2:
        raise ValueError("parts must be at least 2")
    nominal = duration / parts
    min_clip = min(nominal * 0.55, max(0.25, nominal - search_window))
    boundaries = [0.0]

    for index in range(1, parts):
        target = nominal * index
        remaining_parts = parts - index
        lower = max(boundaries[-1] + min_clip, target - search_window)
        upper = min(duration - remaining_parts * min_clip, target + search_window)
        candidates = [time for time in scene_times if lower <= time <= upper]
        chosen = min(candidates, key=lambda time: abs(time - target)) if candidates else target
        boundaries.append(chosen)

    boundaries.append(duration)
    return boundaries


def encode_clip(
    source: Path,
    output: Path,
    start: float,
    end: float,
    copy_audio: bool,
) -> None:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-ss", f"{start:.6f}", "-t", f"{end - start:.6f}",
        "-map", "0:v:0", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if copy_audio:
        command.extend(["-map", "0:a?", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.append(str(output))
    run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a video into consecutive clips at scene changes near equal time targets."
    )
    parser.add_argument("input", type=Path, help="Source video path")
    parser.add_argument("--parts", type=int, default=3, help="Number of output clips (default: 3)")
    parser.add_argument("--mode", choices=("smart", "exact"), default="smart")
    parser.add_argument("--output-dir", type=Path, default=Path("split_output"))
    parser.add_argument("--scene-threshold", type=float, default=0.30)
    parser.add_argument("--search-window", type=float, default=6.0)
    parser.add_argument("--copy-audio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_tools()
    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input video not found: {source}")
    if args.parts < 2:
        raise ValueError("--parts must be at least 2")
    if not 0 < args.scene_threshold < 1:
        raise ValueError("--scene-threshold must be between 0 and 1")
    if args.search_window < 0:
        raise ValueError("--search-window cannot be negative")

    duration = probe_duration(source)
    scene_times = detect_scene_times(source, args.scene_threshold) if args.mode == "smart" else []
    boundaries = choose_boundaries(
        duration,
        args.parts,
        scene_times,
        args.search_window if args.mode == "smart" else 0.0,
    )

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        output = output_dir / f"part_{index:02d}.mp4"
        encode_clip(source, output, start, end, args.copy_audio)
        clips.append({
            "part": index,
            "file": output.name,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(end - start, 3),
        })

    report = {
        "source": str(source),
        "source_duration_seconds": round(duration, 3),
        "mode": args.mode,
        "parts": args.parts,
        "scene_threshold": args.scene_threshold if args.mode == "smart" else None,
        "search_window_seconds": args.search_window if args.mode == "smart" else 0,
        "detected_scene_times_seconds": [round(value, 3) for value in scene_times],
        "clips": clips,
    }
    report_path = output_dir / "split_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

