"""Draw the profile README's static cards (light and dark SVG) and the avatar.

Black and white, to match maller.com.au. Standard library only; the avatar
PNG is rendered from avatar.svg with rsvg-convert if it's installed.

    python3 scripts/cards.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from html import escape

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

THEMES = {
    "dark": {"bg": "#000000", "panel": "#0E0E10", "line": "#26262B", "ink": "#FFFFFF",
             "muted": "#A1A1AA", "faint": "#8A8A93", "button": "#FFFFFF", "button_ink": "#000000"},
    "light": {"bg": "#FFFFFF", "panel": "#F6F6F7", "line": "#E4E4E7", "ink": "#000000",
              "muted": "#52525B", "faint": "#63636B", "button": "#000000", "button_ink": "#FFFFFF"},
}
SANS = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace"
W, P = 880, 40

NAME = "Oliver Maller"
TAGLINE = "Smart home, network and homelab tools, built in Melbourne and shared on GitHub."
ABOUT = ("I build the software that ties homes together: alarm panels, phone systems, blinds, "
         "fireplaces and KNX lighting, all controlled locally from Home Assistant and Apple Home, "
         "with no cloud in the middle.")

PROJECTS = [
    ("ha-protege-wx", "Home Assistant integration", "Protege WX for Home Assistant",
     "Arm, disarm and unlock doors on an ICT Protege WX, and see who did what, about once a "
     "second. Works through the controller's own web interface, so no Automation licence is "
     "needed. Comes with its own alarm card and works in Apple Home."),
    ("ha-nec-pbx", "Home Assistant integration", "NEC phone systems for Home Assistant",
     "Who called, which room answered and what was missed, read from an NEC SL2100 or SV9100's "
     "own call log over the network. No CTI licence, cloud or extra software on the phone system."),
    ("ha-escea-fireplace", "Home Assistant integration", "Escea Fireplace for Home Assistant",
     "Escea gas fireplaces, both the Ethernet models and the newer Wi-Fi ones: on and off, "
     "temperature, Boost and Flame effect, the fire's own timers and its diagnostics. Built so "
     "it can never re-light a fire someone turned off."),
    ("aok-blind-bridge", "ESP32 firmware", "A-OK Blind Bridge",
     "Local control of 433 MHz A-OK blind motors (sold as Motolux and others) with an ESP32 and "
     "a CC1101 radio, about A$15 of parts. Learns your remote, follows it, and adds positions, "
     "scenes and schedules. Install it from your browser."),
    ("joyhome-knx-kernel", "Linux kernel", "JoyHome KNX kernel",
     "A current Linux 6.18 LTS kernel for the JoyHome KNX home server (Rockchip RK3566), which "
     "only shipped with a 2022 kernel. Includes the early hardware watchdog that stops ready-made "
     "kernels from booting it, and rebuilds itself every month."),
]


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return lines


def svg_open(w: int, h: int, label: str, t: dict) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="{t["bg"]}" stroke="{t["line"]}"/>',
    ]


def monogram(x: float, y: float, size: float, fill: str, ink: str) -> str:
    r = size * 56 / 240
    fs = size * 104 / 240
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{r:.1f}" fill="{fill}"/>'
            f'<text x="{x+size/2:.1f}" y="{y+size*0.648:.1f}" text-anchor="middle" font-family="{SANS}" '
            f'font-weight="700" font-size="{fs:.1f}" letter-spacing="{-fs/26:.1f}" fill="{ink}">OM</text>')


def hero(theme: str) -> str:
    t = THEMES[theme]
    about = wrap(ABOUT, 84)
    tag = wrap(TAGLINE, 54)
    H = 268 + len(about) * 26 + (len(tag) - 1) * 34
    out = svg_open(W, H, f"{NAME}. {TAGLINE} {ABOUT}", t)
    out.append(monogram(P, P, 64, t["button"], t["button_ink"]))
    out.append(f'<text x="{P+84}" y="{P+28}" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{t["faint"]}">GITHUB.COM/OLLIEMALLER</text>')
    out.append(f'<text x="{P+84}" y="{P+58}" font-family="{SANS}" font-size="30" font-weight="700" letter-spacing="-0.8" fill="{t["ink"]}">{NAME}</text>')
    y = P + 124
    for line in tag:
        out.append(f'<text x="{P}" y="{y}" font-family="{SANS}" font-size="26" font-weight="650" letter-spacing="-0.6" fill="{t["ink"]}">{escape(line)}</text>')
        y += 34
    y += 10
    for line in about:
        out.append(f'<text x="{P}" y="{y}" font-family="{SANS}" font-size="17" fill="{t["muted"]}">{escape(line)}</text>')
        y += 26
    y += 18
    out.append(f'<line x1="{P}" y1="{y}" x2="{W-P}" y2="{y}" stroke="{t["line"]}"/>')
    out.append(f'<text x="{P}" y="{y+34}" font-family="{MONO}" font-size="13" letter-spacing="1" fill="{t["ink"]}">maller.com.au</text>')
    out.append(f'<text x="{W-P}" y="{y+34}" text-anchor="end" font-family="{MONO}" font-size="13" letter-spacing="1" fill="{t["muted"]}">Melbourne, Australia</text>')
    out.append("</svg>")
    return "\n".join(out)


def heading(theme: str, label: str, title: str, sub: str) -> str:
    t = THEMES[theme]
    H = 120
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">']
    out.append(f'<text x="2" y="40" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{t["faint"]}">{escape(label.upper())}</text>')
    out.append(f'<text x="0" y="78" font-family="{SANS}" font-size="32" font-weight="700" letter-spacing="-0.9" fill="{t["ink"]}">{escape(title)}</text>')
    out.append(f'<text x="1" y="106" font-family="{SANS}" font-size="16" fill="{t["muted"]}">{escape(sub)}</text>')
    out.append("</svg>")
    return "\n".join(out)


ICONS = os.path.join(OUT, "icons")


def icon(repo: str, x: float, y: float, size: float, theme: str) -> str:
    """The project's icon (same as maller.com.au), nested as an inline SVG."""
    path = os.path.join(ICONS, f"{repo}.svg")
    if not os.path.exists(path):
        path = os.path.join(ICONS, "default.svg")
    with open(path, encoding="utf-8") as f:
        svg = f.read().strip()
    svg = re.sub(r"^<svg\b[^>]*>", f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 256 256">', svg)
    ring = ""
    if theme == "dark":
        # A black tile on a black card needs an edge to be seen.
        r = size * 56 / 256
        o = size * 8 / 256
        ring = (f'<rect x="{x+o:.1f}" y="{y+o:.1f}" width="{size-2*o:.1f}" height="{size-2*o:.1f}" '
                f'rx="{r:.1f}" fill="none" stroke="{THEMES[theme]["line"]}" stroke-width="2"/>')
    return svg + ring


def project(theme: str, idx: int, repo: str, kind: str, title: str, blurb: str) -> str:
    t = THEMES[theme]
    lines = wrap(blurb, 84)
    H = 132 + len(lines) * 24
    X = P + 80
    out = svg_open(W, H, f"{title}. {kind}. {blurb}", t)
    out.append(icon(repo, P - 4, P - 4, 64, theme))
    out.append(f'<text x="{X}" y="{P+12}" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{t["faint"]}">{idx:02d}  ·  {escape(kind.upper())}</text>')
    out.append(f'<text x="{W-P}" y="{P+12}" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{t["muted"]}">{escape(repo)}  ↗</text>')
    out.append(f'<text x="{X}" y="{P+48}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.5" fill="{t["ink"]}">{escape(title)}</text>')
    y = P + 86
    for line in lines:
        out.append(f'<text x="{X}" y="{y}" font-family="{SANS}" font-size="15.5" fill="{t["muted"]}">{escape(line)}</text>')
        y += 24
    out.append("</svg>")
    return "\n".join(out)


def avatar() -> str:
    # Full-bleed square: GitHub crops avatars to a circle, so no rounded corners here.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">'
            f'<rect width="1024" height="1024" fill="#000"/>'
            f'<text x="512" y="660" text-anchor="middle" font-family="Inter" font-weight="700" '
            f'font-size="400" letter-spacing="-16" fill="#fff">OM</text></svg>')


def write(name: str, text: str) -> None:
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(text + "\n")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        write(f"hero-{theme}.svg", hero(theme))
        write(f"projects-{theme}.svg", heading(theme, "Projects", "Things I've built",
              "Open source, MIT licensed, and running in my own homes before anyone else's."))
        for i, p in enumerate(PROJECTS, 1):
            write(f"project-{p[0]}-{theme}.svg", project(theme, i, *p))
    write("avatar.svg", avatar())
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-w", "1024", "-h", "1024", "-o",
                        os.path.join(OUT, "avatar.png"), os.path.join(OUT, "avatar.svg")], check=True)


if __name__ == "__main__":
    main()
