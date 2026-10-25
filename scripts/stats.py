"""Render the profile's activity card (light and dark SVG) from GitHub data.

Runs in GitHub Actions with GITHUB_TOKEN. Standard library only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "olliemaller")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""

THEMES = {
    "dark": {"card": "#141416", "line": "#26292F", "ink": "#F5F5F7", "muted": "#A9B2C0",
             "faint": "#7D8796", "accent": "#378ADD", "track": "#1B1D21",
             "langs": ["#378ADD", "#185FA5", "#85B7EB", "#0C447C", "#B5D4F4", "#4A5568"]},
    "light": {"card": "#FFFFFF", "line": "#E3E6EA", "ink": "#0A0A0F", "muted": "#4A5568",
              "faint": "#5F6B7A", "accent": "#185FA5", "track": "#EEF1F4",
              "langs": ["#185FA5", "#378ADD", "#85B7EB", "#0C447C", "#B5D4F4", "#A9B2C0"]},
}
SANS = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def fetch() -> dict:
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def summarise(user: dict, today: dt.date | None = None) -> dict:
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = sorted(
        (dt.date.fromisoformat(d["date"]), d["contributionCount"])
        for w in cal["weeks"] for d in w["contributionDays"]
    )
    today = today or days[-1][0]
    days = [d for d in days if d[0] <= today]

    longest = run = 0
    for _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    # Today without a contribution yet doesn't break the streak.
    tail = days[:-1] if days and days[-1][1] == 0 else days
    for _, n in reversed(tail):
        if not n:
            break
        current += 1

    sizes: dict[str, int] = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]
    total = sum(sizes.values()) or 1
    langs = sorted(sizes.items(), key=lambda kv: -kv[1])
    top = [(name, size / total) for name, size in langs[:5]]
    rest = 1 - sum(p for _, p in top)
    if rest > 0.005:
        top.append(("Other", rest))

    return {
        "contributions": cal["totalContributions"],
        "current": current,
        "longest": longest,
        "repos": user["repositories"]["totalCount"],
        "langs": top,
        "updated": today,
    }


def render(s: dict, theme: str) -> str:
    t = THEMES[theme]
    W, H, P = 880, 262, 32
    metrics = [
        (f"{s['contributions']:,}", "Contributions (12 months)"),
        (f"{s['current']}", "Current streak (days)"),
        (f"{s['longest']}", "Longest streak (days)"),
        (f"{s['repos']}", "Repositories"),
    ]
    col = (W - 2 * P) / 4
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub activity for {USER}">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'<text x="{P}" y="44" font-family="{MONO}" font-size="12" font-weight="500" letter-spacing="2.2" fill="{t["accent"]}">ACTIVITY</text>',
        f'<text x="{W-P}" y="44" text-anchor="end" font-family="{MONO}" font-size="11" letter-spacing="1.6" fill="{t["faint"]}">UPDATED {s["updated"].strftime("%d %b %Y").upper()}</text>',
    ]
    for i, (value, label) in enumerate(metrics):
        x = P + i * col
        if i:
            out.append(f'<line x1="{x-14:.1f}" y1="70" x2="{x-14:.1f}" y2="134" stroke="{t["line"]}"/>')
        out.append(f'<text x="{x:.1f}" y="108" font-family="{SANS}" font-size="40" font-weight="700" letter-spacing="-1" fill="{t["ink"]}" style="font-variant-numeric:tabular-nums">{escape(value)}</text>')
        out.append(f'<text x="{x:.1f}" y="132" font-family="{SANS}" font-size="13.5" fill="{t["muted"]}">{escape(label)}</text>')

    out.append(f'<line x1="{P}" y1="158" x2="{W-P}" y2="158" stroke="{t["line"]}"/>')
    out.append(f'<text x="{P}" y="188" font-family="{MONO}" font-size="11" letter-spacing="1.8" fill="{t["faint"]}">LANGUAGES, OWN REPOSITORIES</text>')
    bar_w, x = W - 2 * P, float(P)
    out.append(f'<clipPath id="bar"><rect x="{P}" y="202" width="{bar_w}" height="10" rx="5"/></clipPath>')
    out.append(f'<rect x="{P}" y="202" width="{bar_w}" height="10" rx="5" fill="{t["track"]}"/>')
    out.append('<g clip-path="url(#bar)">')
    for i, (_, pct) in enumerate(s["langs"]):
        w = bar_w * pct
        out.append(f'<rect x="{x:.1f}" y="202" width="{max(w, 2):.1f}" height="10" fill="{t["langs"][i % 6]}"/>')
        x += w
    out.append("</g>")
    lx = float(P)
    for i, (name, pct) in enumerate(s["langs"]):
        label = f"{name} {pct*100:.1f}%" if pct < 0.995 else name
        out.append(f'<circle cx="{lx+5:.1f}" cy="236" r="5" fill="{t["langs"][i % 6]}"/>')
        out.append(f'<text x="{lx+16:.1f}" y="240.5" font-family="{SANS}" font-size="13.5" fill="{t["muted"]}">{escape(label)}</text>')
        lx += 30 + 7.6 * len(label)
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    data = json.load(open(os.environ["STATS_FIXTURE"])) if os.environ.get("STATS_FIXTURE") else fetch()
    s = summarise(data)
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"stats-{theme}.svg"), "w") as f:
            f.write(render(s, theme))
    print(json.dumps({k: (str(v) if k == "updated" else v) for k, v in s.items()}))


if __name__ == "__main__":
    main()
