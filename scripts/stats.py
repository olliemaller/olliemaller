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


QUOTES = [
    ("A program that produces incorrect results twice as fast is infinitely slower.", "John Ousterhout"),
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The best way to predict the future is to invent it.", "Alan Kay"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("Any sufficiently advanced technology is indistinguishable from magic.", "Arthur C. Clarke"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("It's not a bug, it's an undocumented feature.", "Anonymous"),
    ("The most dangerous phrase in the language is: we've always done it this way.", "Grace Hopper"),
    ("Debugging is twice as hard as writing the code in the first place.", "Brian Kernighan"),
]
JOKES = [
    ("Why do network engineers make great comedians?", "Their timing is always under 20 ms."),
    ("Why did the access point go to therapy?", "Too many unresolved connection issues."),
    ("What's a homelabber's favourite exercise?", "Rack pulls."),
    ("Why did the smart home break up with the router?", "It felt the connection was one-sided."),
    ("How many sysadmins does it take to change a light bulb?", "None. It works on my machine."),
    ("Why did the functional programmer get thrown out of school?", "Because he refused to take classes."),
    ("Why don't packets ever get lonely?", "They always travel in a stream."),
    ("What did the switch say to the patch cable?", "You complete me, port 24."),
    ("Why was the VLAN so calm?", "It kept everything separated."),
    ("Why do programmers prefer dark mode?", "Because light attracts bugs."),
    ("Why did the DNS server go on holiday?", "It needed to resolve some issues."),
    ("What's an alarm installer's favourite music?", "Anything with a good entry delay."),
]


def _wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return lines


def render_fun(day: dt.date, theme: str) -> str:
    t = THEMES[theme]
    n = day.toordinal()
    quote, author = QUOTES[n % len(QUOTES)]
    question, answer = JOKES[(n // 3) % len(JOKES)]
    W, P, half = 880, 32, 440
    q_lines = _wrap(f"“{quote}”", 38)
    j_lines = _wrap(question, 40)
    a_lines = _wrap(answer, 40)
    body_h = max(len(q_lines) * 26 + 34, (len(j_lines) + len(a_lines)) * 24 + 22)
    H = 76 + body_h + 34
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Quote and joke of the day">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'<line x1="{half}" y1="28" x2="{half}" y2="{H-28}" stroke="{t["line"]}"/>',
        f'<text x="{P}" y="44" font-family="{MONO}" font-size="12" font-weight="500" letter-spacing="2.2" fill="{t["accent"]}">QUOTE OF THE DAY</text>',
        f'<text x="{half+P}" y="44" font-family="{MONO}" font-size="12" font-weight="500" letter-spacing="2.2" fill="{t["accent"]}">JOKE OF THE DAY</text>',
    ]
    y = 80
    for line in q_lines:
        out.append(f'<text x="{P}" y="{y}" font-family="{SANS}" font-size="18" font-weight="600" letter-spacing="-0.2" fill="{t["ink"]}">{escape(line)}</text>')
        y += 26
    out.append(f'<text x="{P}" y="{y+8}" font-family="{SANS}" font-size="14" fill="{t["muted"]}">{escape(author)}</text>')
    y = 80
    for line in j_lines:
        out.append(f'<text x="{half+P}" y="{y}" font-family="{SANS}" font-size="16" font-weight="600" fill="{t["ink"]}">{escape(line)}</text>')
        y += 24
    y += 10
    for line in a_lines:
        out.append(f'<text x="{half+P}" y="{y}" font-family="{SANS}" font-size="16" fill="{t["accent"]}">{escape(line)}</text>')
        y += 24
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    data = json.load(open(os.environ["STATS_FIXTURE"])) if os.environ.get("STATS_FIXTURE") else fetch()
    s = summarise(data)
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"stats-{theme}.svg"), "w") as f:
            f.write(render(s, theme))
        with open(os.path.join(OUT, f"fun-{theme}.svg"), "w") as f:
            f.write(render_fun(dt.date.today(), theme))
    print(json.dumps({k: (str(v) if k == "updated" else v) for k, v in s.items()}))


if __name__ == "__main__":
    main()
