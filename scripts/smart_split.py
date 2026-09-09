#!/usr/bin/env python3
"""Split a video near natural speech pauses and visual scene boundaries."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PTS_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")
SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"Missing required command(s): {', '.join(missing)}")


def probe_media(source: Path) -> tuple[float, bool]:
    result = run(["ffprobe", "-v", "error", "-show_entries",
                  "format=duration:stream=codec_type", "-of", "json", str(source)], capture=True)
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    if duration <= 0:
        raise ValueError("Video duration must be greater than zero")
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return duration, has_audio


def detect_scene_times(source: Path, threshold: float) -> list[float]:
    expression = f"select=gt(scene\\,{threshold}),showinfo"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-vf", expression,
         "-an", "-f", "null", "-"], text=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Scene detection failed")
    return sorted({float(m.group(1)) for m in PTS_RE.finditer(result.stderr)})


def detect_speech_pause_times(source: Path, duration: float, noise_db: float,
                              minimum_silence: float) -> list[float]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-vn", "-af",
         f"silencedetect=noise={noise_db}dB:d={minimum_silence}", "-f", "null", "-"],
        text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Audio pause detection failed")

    events: list[tuple[str, float]] = []
    for line in result.stderr.splitlines():
        start = SILENCE_START_RE.search(line)
        end = SILENCE_END_RE.search(line)
        if start:
            events.append(("start", float(start.group(1))))
        if end:
            events.append(("end", float(end.group(1))))

    pauses: list[float] = []
    open_start: float | None = None
    for kind, timestamp in events:
        if kind == "start":
            open_start = timestamp
        elif open_start is not None:
            midpoint = (open_start + timestamp) / 2
            if 0.05 < midpoint < duration - 0.05:
                pauses.append(midpoint)
            open_start = None
    if open_start is not None:
        midpoint = (open_start + duration) / 2
        if midpoint < duration - 0.05:
            pauses.append(midpoint)
    return sorted(set(pauses))


def choose_boundaries(duration: float, parts: int, pause_times: list[float],
                      scene_times: list[float], search_window: float) -> tuple[list[float], list[str]]:
    if parts < 2:
        raise ValueError("parts must be at least 2")
    nominal = duration / parts
    min_clip = min(nominal * 0.55, max(0.25, nominal - search_window))
    boundaries, sources = [0.0], ["start"]
    for index in range(1, parts):
        target = nominal * index
        remaining = parts - index
        lower = max(boundaries[-1] + min_clip, target - search_window)
        upper = min(duration - remaining * min_clip, target + search_window)
        pauses = [t for t in pause_times if lower <= t <= upper]
        scenes = [t for t in scene_times if lower <= t <= upper]
        if pauses:
            chosen, source = min(pauses, key=lambda t: abs(t - target)), "speech_pause"
        elif scenes:
            chosen, source = min(scenes, key=lambda t: abs(t - target)), "scene_change"
        else:
            chosen, source = target, "equal_fallback"
        boundaries.append(chosen)
        sources.append(source)
    boundaries.append(duration)
    sources.append("end")
    return boundaries, sources


def encode_clip(source: Path, output: Path, start: float, end: float, keep_audio: bool) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
               "-ss", f"{start:.6f}", "-t", f"{end-start:.6f}", "-map", "0:v:0",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt",
               "yuv420p", "-movflags", "+faststart"]
    if keep_audio:
        command.extend(["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.append(str(output))
    run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split a video near speech pauses or visual changes.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--parts", type=int, default=3)
    parser.add_argument("--mode", choices=("auto", "audio", "visual", "exact"), default="auto")
    parser.add_argument("--output-dir", type=Path, default=Path("split_output"))
    parser.add_argument("--scene-threshold", type=float, default=0.30)
    parser.add_argument("--search-window", type=float, default=6.0)
    parser.add_argument("--silence-db", type=float, default=-35.0)
    parser.add_argument("--minimum-silence", type=float, default=0.30)
    parser.add_argument("--audio-output", choices=("auto", "keep", "drop"), default="auto")
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
    if args.search_window < 0 or args.minimum_silence < 0:
        raise ValueError("Search window and minimum silence cannot be negative")

    duration, has_audio = probe_media(source)
    if args.mode == "audio" and not has_audio:
        raise ValueError("--mode audio requires a source with an audio stream")
    analyze_audio = has_audio and args.mode in ("auto", "audio")
    analyze_visual = args.mode in ("auto", "visual")
    pauses = detect_speech_pause_times(source, duration, args.silence_db,
                                       args.minimum_silence) if analyze_audio else []
    scenes = detect_scene_times(source, args.scene_threshold) if analyze_visual else []
    window = 0.0 if args.mode == "exact" else args.search_window
    boundaries, sources = choose_boundaries(duration, args.parts, pauses, scenes, window)
    keep_audio = has_audio if args.audio_output == "auto" else args.audio_output == "keep"
    keep_audio = keep_audio and has_audio

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        output = output_dir / f"part_{index:02d}.mp4"
        encode_clip(source, output, start, end, keep_audio)
        clips.append({"part": index, "file": output.name,
                      "start_seconds": round(start, 3), "end_seconds": round(end, 3),
                      "duration_seconds": round(end-start, 3),
                      "end_boundary_source": sources[index]})

    report = {"source": str(source), "source_duration_seconds": round(duration, 3),
              "mode": args.mode, "parts": args.parts, "source_has_audio": has_audio,
              "output_keeps_audio": keep_audio,
              "detected_speech_pause_times_seconds": [round(t, 3) for t in pauses],
              "detected_scene_times_seconds": [round(t, 3) for t in scenes], "clips": clips}
    (output_dir / "split_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError,
            subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

