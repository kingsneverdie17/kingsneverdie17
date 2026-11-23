"""Render a 3D "site activity" skyline of GitHub contributions (black and yellow theme).

Run in GitHub Actions with GITHUB_TOKEN set, or locally with --data days.json
(a list of [date, count] pairs) to preview.
"""
import json, math, os, sys, urllib.request, datetime as dt

LOGIN = os.environ.get("LOGIN", "kingsneverdie17")
OUT = os.environ.get("OUT", "assets/activity.svg")

Y, K, K2, WH, G = "#ffd400", "#0b0b0b", "#161616", "#f4f1e6", "#8a8a80"
HEAVY = "Impact,'Anton','Oswald','Arial Black','Arial Narrow',sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"


def fetch_days():
    q = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      weeks{contributionDays{date contributionCount}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def shade(c, f):
    return "#" + "".join(f"{round(int(c[i:i + 2], 16) * f):02x}" for i in (1, 3, 5))


def streaks(counts):
    best = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        best = max(best, cur)
    cur = 0
    for c in reversed(counts):
        if c > 0:
            cur += 1
        elif cur or c == 0:
            break
    return best, cur


def render(days):
    days = sorted((str(a), int(b)) for a, b in days)
    first = dt.date.fromisoformat(days[0][0])
    pad = (first.weekday() + 1) % 7  # Sunday = 0
    cells = []
    for i, (date, c) in enumerate(days):
        k = i + pad
        cells.append((k // 7, k % 7, c, date))
    counts = [c for _, c in days]
    total, mx = sum(counts), max(counts + [1])
    best_day = max(days, key=lambda x: x[1])
    longest, current = streaks(counts)

    W, H = 850, 430
    U, V = (12.6, 2.3), (-5.6, 6.0)  # week and weekday directions on screen
    ox, oy = 92, 150
    cell, maxh = 0.82, 118

    def pt(w, d, up=0.0):
        return (ox + w * U[0] + d * V[0], oy + w * U[1] + d * V[1] - up)

    def poly(ps, fill, extra=""):
        return '<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in ps) + f'" fill="{fill}"{extra}/>'

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           "<style>.t{transform-box:fill-box;transform-origin:50% 100%;animation:rise .9s cubic-bezier(.2,.8,.2,1) both}"
           "@keyframes rise{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
           ".bl{animation:bl 1.2s steps(1) infinite}@keyframes bl{50%{opacity:.15}}</style>",
           f'<rect width="{W}" height="{H}" fill="{K}"/>',
           f'<rect width="{W}" height="44" fill="{Y}"/>',
           f'<text x="40" y="28" font-family="{HEAVY}" font-size="22" letter-spacing="2" fill="{K}">SITE ACTIVITY</text>',
           f'<text x="810" y="28" text-anchor="end" font-family="{MONO}" font-size="12" font-weight="700" fill="{K}">EVERY COMMIT IS A FLOOR</text>']

    g = (1 - cell) / 2
    top_light = None
    for w, d, c, date in sorted(cells, key=lambda x: (x[0] + x[1], x[0])):
        a, b = w + g, d + g
        p0, p1, p2, p3 = (a, b), (a + cell, b), (a + cell, b + cell), (a, b + cell)
        if c == 0:
            out.append(poly([pt(*p) for p in (p0, p1, p2, p3)], "#1c1c1a", f' stroke="#262622" stroke-width=".6"'))
            continue
        t = math.sqrt(c / mx)
        h = 5 + t * maxh
        top = mix("#7a6200", Y, t)
        front, right = shade(top, .72), shade(top, .52)
        faces = [
            poly([pt(*p1), pt(*p2), pt(*p2, h), pt(*p1, h)], right),
            poly([pt(*p3), pt(*p2), pt(*p2, h), pt(*p3, h)], front),
            poly([pt(*p, h) for p in (p0, p1, p2, p3)], top),
        ]
        out.append(f'<g class="t" style="animation-delay:{w * .018:.2f}s"><title>{c} on {date}</title>' + "".join(faces) + "</g>")
        if (date, c) == best_day:
            top_light = pt(a + cell / 2, b + cell / 2, h + 7)
    if top_light:
        out.append(f'<line x1="{top_light[0]:.1f}" y1="{top_light[1] + 7:.1f}" x2="{top_light[0]:.1f}" y2="{top_light[1]:.1f}" stroke="{Y}" stroke-width="1.4"/>'
                   f'<circle cx="{top_light[0]:.1f}" cy="{top_light[1]:.1f}" r="3.2" fill="#ff3b30" class="bl"/>')

    # month labels along the front edge
    seen = set()
    for w, d, c, date in cells:
        m = date[:7]
        if d == 0 and m not in seen and date[8:] <= "07":
            seen.add(m)
            x, y = pt(w, 7.9)
            out.append(f'<text x="{x:.0f}" y="{y + 12:.0f}" font-family="{MONO}" font-size="10.5" fill="{G}">'
                       f'{dt.date.fromisoformat(date).strftime("%b").upper()}</text>')

    stats = [(str(total), "CONTRIBUTIONS · 12 MO"), (str(best_day[1]), "BEST DAY"),
             (f"{longest} d", "LONGEST STREAK"), (f"{current} d", "CURRENT STREAK")]
    for i, (v, l) in enumerate(stats):
        x = 40 + i * 195
        out.append(f'<text x="{x}" y="{H - 46}" font-family="{HEAVY}" font-size="30" fill="{Y if i == 0 else WH}">{v}</text>'
                   f'<text x="{x}" y="{H - 24}" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{G}">{l}</text>')
    out.append(f'<line x1="40" y1="{H - 86}" x2="810" y2="{H - 86}" stroke="{G}" stroke-opacity=".3"/>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--data":
        days = json.load(open(sys.argv[2]))
    else:
        days = fetch_days()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(render(days))
    print("wrote", OUT)
