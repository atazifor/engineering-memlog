#!/usr/bin/env python3
"""Render the checked-in demo transcript as a 64-second terminal GIF."""

import argparse
import html
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap


WIDTH = 1280
HEIGHT = 720
DELAY_CENTISECONDS = 800


def parse_frames(transcript: str):
    frames = []
    title = None
    lines = []
    for raw in transcript.splitlines():
        if raw.startswith("=== ") and raw.endswith(" ==="):
            if title is not None:
                frames.append((title, lines))
            title = raw[4:-4]
            lines = []
        elif title is not None and raw.strip():
            lines.append(raw)
    if title is not None:
        frames.append((title, lines))
    return frames


def display_lines(lines):
    rendered = []
    for line in lines:
        wrapped = textwrap.wrap(
            line,
            width=82,
            subsequent_indent="  ",
            replace_whitespace=False,
            drop_whitespace=False,
        ) or [""]
        rendered.extend(wrapped)
    return rendered[:17]


def line_color(line):
    if line.startswith("$"):
        return "#7dd3fc"
    if line.startswith("[skill]"):
        return "#fbbf24"
    if line.startswith("PASS") or line.startswith("OK"):
        return "#86efac"
    if line.startswith("FAIL") or "AssertionError" in line:
        return "#fca5a5"
    if line.startswith("MATCH") or line.startswith("Appended"):
        return "#c4b5fd"
    return "#d1d5db"


def render_svg(title, lines, index, total):
    text_nodes = []
    y = 190
    for line in display_lines(lines):
        text_nodes.append(
            '<text x="80" y="{}" fill="{}" font-family="Menlo, Consolas, monospace" font-size="23">{}</text>'.format(
                y, line_color(line), html.escape(line)
            )
        )
        y += 30
    dots = []
    start_x = WIDTH / 2 - ((total - 1) * 16)
    for dot in range(total):
        fill = "#38bdf8" if dot == index else "#334155"
        dots.append(
            '<circle cx="{}" cy="676" r="6" fill="{}"/>'.format(
                start_x + dot * 32, fill
            )
        )
    return """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="#08111f"/>
<rect x="42" y="38" width="1196" height="620" rx="18" fill="#0f172a" stroke="#334155" stroke-width="2"/>
<circle cx="75" cy="70" r="8" fill="#fb7185"/>
<circle cx="101" cy="70" r="8" fill="#fbbf24"/>
<circle cx="127" cy="70" r="8" fill="#4ade80"/>
<text x="80" y="125" fill="#f8fafc" font-family="Menlo, Consolas, monospace" font-size="30" font-weight="600">{title}</text>
<line x1="80" y1="148" x2="1200" y2="148" stroke="#334155"/>
{text_nodes}
{dots}
</svg>""".format(
        width=WIDTH,
        height=HEIGHT,
        title=html.escape(title),
        text_nodes="\n".join(text_nodes),
        dots="\n".join(dots),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    converter = shutil.which("magick") or shutil.which("convert")
    if converter is None:
        raise SystemExit("ImageMagick (`magick` or `convert`) is required")

    frames = parse_frames(args.transcript.read_text(encoding="utf-8"))
    if len(frames) != 8:
        raise SystemExit("expected 8 transcript frames, found {}".format(len(frames)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="memlog-demo-render-") as directory:
        paths = []
        for index, (title, lines) in enumerate(frames):
            path = Path(directory) / "frame-{:02d}.svg".format(index)
            path.write_text(render_svg(title, lines, index, len(frames)), encoding="utf-8")
            paths.append(str(path))
        subprocess.run(
            [converter, "-delay", str(DELAY_CENTISECONDS), *paths, "-loop", "0", str(args.output)],
            check=True,
        )


if __name__ == "__main__":
    main()
