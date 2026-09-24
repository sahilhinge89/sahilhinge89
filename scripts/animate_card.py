#!/usr/bin/env python3
"""
Injects the gh-ascii profile card animation (fade-in ASCII art, staggered
stats reveal, blinking cursor, and an up/down scanning highlight band) into
a freshly-downloaded gh-ascii SVG card, in place.

Usage: python3 animate_card.py <path-to-svg>
Detects dark vs light theme automatically from the card's background fill.
"""
import re
import sys


def animate(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        content = f.read()

    if "<style>" in content and "asciiFadeIn" in content:
        # Already animated (e.g. script ran twice) - skip to stay idempotent.
        return

    rect_match = re.search(r"<rect[^>]*fill=\"(#[0-9a-fA-F]{3,6})\"[^>]*/>", content)
    bg_fill = rect_match.group(1).lower() if rect_match else "#0d1117"
    is_light = bg_fill in ("#ffffff", "#fff")

    if is_light:
        scan_stops = (
            '<stop offset="0%" stop-color="#0969da" stop-opacity="0"/>'
            '<stop offset="45%" stop-color="#0969da" stop-opacity="0"/>'
            '<stop offset="50%" stop-color="#0969da" stop-opacity="0.35"/>'
            '<stop offset="55%" stop-color="#0969da" stop-opacity="0"/>'
            '<stop offset="100%" stop-color="#0969da" stop-opacity="0"/>'
        )
        blend = "multiply"
        cursor_fill = "#2da44e"
    else:
        scan_stops = (
            '<stop offset="0%" stop-color="#39d353" stop-opacity="0"/>'
            '<stop offset="45%" stop-color="#39d353" stop-opacity="0"/>'
            '<stop offset="50%" stop-color="#7ee787" stop-opacity="0.55"/>'
            '<stop offset="55%" stop-color="#39d353" stop-opacity="0"/>'
            '<stop offset="100%" stop-color="#39d353" stop-opacity="0"/>'
        )
        blend = "screen"
        cursor_fill = "#39d353"

    svg_open = re.search(r"^.*?<rect[^/]*/>\r?\n", content, re.S)
    if not svg_open:
        raise SystemExit(f"Could not locate background rect in {path}; card format may have changed.")
    header = svg_open.group(0)
    rest = content[svg_open.end():]

    # Anchor on the first <text> element whose content contains "@github" —
    # that's the top of the stats panel, regardless of exact coordinates.
    anchor = re.search(r'<text\b[^>]*>(?:(?!</text>).)*?@github', rest, re.S)
    if not anchor:
        raise SystemExit(f"Could not locate stats panel anchor in {path}; card format may have changed.")
    stats_start_idx = anchor.start()
    stats_x_match = re.search(r'x="([\d.]+)"', anchor.group(0))
    stats_x = stats_x_match.group(1) if stats_x_match else "746.4"

    ascii_block = rest[:stats_start_idx]
    tail = rest[stats_start_idx:]
    stats_block = tail.replace("</svg>", "").rstrip("\r\n") + "\n"
    stats_block = re.sub(r"(<text )", r'<text class="stats-row" ', stats_block)

    # width/height for the scan rect and its travel range
    dims = re.search(r'width="([\d.]+)"[^>]*height="([\d.]+)"', header)
    width = dims.group(1) if dims else "1331"
    height = float(dims.group(2)) if dims else 728.0

    style = f"""  <style>
    .ascii-art {{ animation: asciiFadeIn 1.1s ease-out both; }}
    @keyframes asciiFadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}
    .stats-row {{
      opacity: 0;
      animation: rowReveal 0.5s ease-out forwards;
    }}
"""
    for i in range(1, 21):
        style += f'    .stats-row:nth-of-type({i}) {{ animation-delay: {0.7 + i * 0.2:.1f}s; }}\n'
    style += """    @keyframes rowReveal {
      from { opacity: 0; transform: translateX(-6px); }
      to { opacity: 1; transform: translateX(0); }
    }
    .cursor { animation: blink 1s step-end infinite; }
    @keyframes blink {
      0%, 50% { opacity: 1; }
      50.01%, 100% { opacity: 0; }
    }
    .scan-line {
      mix-blend-mode: """ + blend + """;
      animation: scanMove 4.5s ease-in-out infinite alternate;
      pointer-events: none;
    }
    @keyframes scanMove {
      0% { transform: translateY(-140px); }
      100% { transform: translateY(""" + f"{height - 28:.0f}" + """px); }
    }
  </style>
  <defs>
    <linearGradient id="scanGrad" x1="0" y1="0" x2="0" y2="1">
      """ + scan_stops + """
    </linearGradient>
  </defs>
"""

    scan_rect = f'    <rect class="scan-line" x="0" y="-140" width="{width}" height="140" fill="url(#scanGrad)"/>\n'
    cursor_line = (
        f'  <text x="{stats_x}" y="{height - 179:.0f}" fill="{cursor_fill}" '
        'font-family="\'Consolas\', \'Menlo\', \'DejaVu Sans Mono\', monospace" '
        'font-size="16" class="cursor">_</text>\n'
    )

    new_content = (
        header
        + style
        + '  <g class="ascii-art">\n'
        + ascii_block
        + scan_rect
        + "  </g>\n"
        + stats_block
        + cursor_line
        + "</svg>\n"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Animated {path} ({'light' if is_light else 'dark'} theme)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 animate_card.py <path-to-svg>")
    animate(sys.argv[1])
