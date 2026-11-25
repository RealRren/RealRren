"""Builds assets/stats.svg from the GitHub contribution calendar.

The calendar includes private contributions when "Include private
contributions on my profile" is turned on, unlike most stats services.
"""
import datetime as dt
import json
import os
import urllib.request

USER = os.environ["USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        out = json.load(r)
    if "errors" in out:
        raise SystemExit(out["errors"])
    return out["data"]


years = gql(
    "query($u:String!){user(login:$u){createdAt contributionsCollection{contributionYears}}}",
    {"u": USER},
)["user"]
created = years["createdAt"][:10]

YEAR_Q = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
  totalCommitContributions totalPullRequestContributions totalIssueContributions
  totalRepositoryContributions restrictedContributionsCount
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

days = {}
totals = dict(commits=0, prs=0, issues=0, repos=0, private=0, all=0)
for y in years["contributionsCollection"]["contributionYears"]:
    c = gql(YEAR_Q, {"u": USER, "f": f"{y}-01-01T00:00:00Z", "t": f"{y}-12-31T23:59:59Z"})["user"][
        "contributionsCollection"
    ]
    totals["commits"] += c["totalCommitContributions"]
    totals["prs"] += c["totalPullRequestContributions"]
    totals["issues"] += c["totalIssueContributions"]
    totals["repos"] += c["totalRepositoryContributions"]
    totals["private"] += c["restrictedContributionsCount"]
    totals["all"] += c["contributionCalendar"]["totalContributions"]
    for w in c["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[d["date"]] = d["contributionCount"]

today = dt.date.today()
dates = sorted(d for d in days if d <= today.isoformat())

# streaks
longest = run = 0
for d in dates:
    run = run + 1 if days[d] > 0 else 0
    longest = max(longest, run)
current = 0
for d in reversed(dates):
    if days[d] > 0:
        current += 1
    elif d == today.isoformat():
        continue  # today not started yet
    else:
        break

best_day = max(dates, key=lambda d: days[d])
weekday_sum = [0] * 7
for d in dates:
    weekday_sum[dt.date.fromisoformat(d).weekday()] += days[d]
fav_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday_sum.index(max(weekday_sum))]
last30 = sum(days[d] for d in dates[-30:])


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"


active = [d for d in dates if days[d] > 0]
this_year = sum(days[d] for d in dates if d.startswith(str(today.year)))
avg = totals["all"] / max(len(active), 1)

rows = [
    ("TOTAL CONTRIBUTIONS", fmt(totals["all"])),
    ("PRIVATE CONTRIBUTIONS", fmt(totals["private"]) + " \U0001f512"),
    (f"CONTRIBUTIONS IN {today.year}", fmt(this_year)),
    ("LAST 30 DAYS", fmt(last30)),
    ("CURRENT STREAK", f"{current} days \U0001f525"),
    ("LONGEST STREAK", f"{longest} days"),
    ("DAYS ACTIVE", fmt(len(active))),
    ("AVG PER ACTIVE DAY", f"{avg:.1f}"),
    ("BEST DAY", f"{days[best_day]} on {dt.date.fromisoformat(best_day):%b %d %Y}"),
    ("MOST ACTIVE DAY", fav_day),
]

W = 820
row_h = 30
top = 70
H = top + row_h * ((len(rows) + 1) // 2) + 30
cells = []
for i, (k, v) in enumerate(rows):
    col, r = i % 2, i // 2
    x = 30 + col * 400
    y = top + r * row_h
    delay = 0.15 * i
    cells.append(
        f'<g class="row" style="animation-delay:{delay:.2f}s">'
        f'<text class="k" x="{x}" y="{y}">&gt; {k}</text>'
        f'<text class="v" x="{x + 360}" y="{y}" text-anchor="end">{v}</text></g>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
.k{{font:13px 'Courier New',monospace;fill:#9dffb0}}
.v{{font:bold 15px 'Courier New',monospace;fill:#00ff41}}
.h{{font:bold 16px 'Courier New',monospace;fill:#00ff41}}
.s{{font:11px 'Courier New',monospace;fill:#3f8f50}}
.row{{opacity:0;animation:in .4s ease-out forwards}}
@keyframes in{{from{{opacity:0;transform:translateX(-8px)}}to{{opacity:1;transform:none}}}}
</style>
<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="8" fill="#000" stroke="#00ff41" stroke-width="1.5"/>
<text class="h" x="30" y="36">root@realrren:~$ ./stats --include-private</text>
<line x1="30" x2="{W-30}" y1="48" y2="48" stroke="#00ff41" stroke-opacity=".35"/>
{''.join(cells)}
<text class="s" x="{W-30}" y="{H-12}" text-anchor="end">since {created} · updated {today:%Y-%m-%d}</text>
</svg>"""

os.makedirs("assets", exist_ok=True)
with open("assets/stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("\n".join(f"{k}: {v}" for k, v in rows))


# ---------------------------------------------------------------------------
# Trophies card (assets/trophies.svg) built from the same data, so the profile
# does not depend on an outside trophy service.
RANKS = ["SSS", "SS", "S", "AAA", "AA", "A", "B", "C"]


def rank(value, steps):
    """steps: thresholds for C..SSS (ascending, 8 values)."""
    got = None
    for name, need in zip(reversed(RANKS), steps):
        if value >= need:
            got = name
    return got or "?"


years_on = (today - dt.date.fromisoformat(created)).days / 365.25
trophies = [
    ("CONTRIBUTOR", "total", totals["all"], [1, 100, 300, 700, 1500, 3000, 6000, 10000]),
    ("COMMITTER", "commits", totals["commits"], [1, 50, 200, 500, 1000, 2000, 4000, 8000]),
    ("STEALTH OPS", "private", totals["private"], [1, 50, 200, 500, 1000, 2000, 4000, 8000]),
    ("STREAKER", "day streak", longest, [1, 3, 7, 14, 30, 60, 100, 200]),
    ("GRINDER", "active days", len(active), [1, 20, 50, 100, 200, 365, 600, 1000]),
    ("MERGER", "PRs", totals["prs"], [1, 5, 20, 50, 100, 200, 500, 1000]),
    ("VETERAN", "years", round(years_on, 1), [0, 0.5, 1, 2, 3, 5, 7, 10]),
]

TW, TH, GAP = 110, 132, 8
TW_ALL = len(trophies) * TW + (len(trophies) - 1) * GAP
cup = ("M-14 -22 h28 v10 a14 14 0 0 1 -28 0 z M-14 -18 h-7 a7 7 0 0 0 7 9 "
       "M14 -18 h7 a7 7 0 0 1 -7 9 M-3 2 h6 v7 h-6 z M-10 9 h20 v4 h-20 z")
items = []
for i, (title, unit, val, steps) in enumerate(trophies):
    r = rank(val, steps)
    x = i * (TW + GAP)
    lit = r != "?"
    col = "#00ff41" if lit else "#1f5f2c"
    glow = ' filter="url(#g)"' if r in ("SSS", "SS", "S") else ""
    shown = fmt(val) if isinstance(val, int) else f"{val}"
    items.append(
        f'<g class="t" style="animation-delay:{0.12*i:.2f}s" transform="translate({x},0)">'
        f'<rect x="0.75" y="0.75" width="{TW-1.5}" height="{TH-1.5}" rx="6" fill="#000" stroke="{col}" stroke-opacity=".6"/>'
        f'<text class="r" x="{TW/2}" y="22" text-anchor="middle" fill="{col}">{r}</text>'
        f'<g transform="translate({TW/2},62)"><path d="{cup}" fill="none" stroke="{col}" stroke-width="2"{glow}/></g>'
        f'<text class="n" x="{TW/2}" y="98" text-anchor="middle">{title}</text>'
        f'<text class="u" x="{TW/2}" y="116" text-anchor="middle">{shown} {unit}</text></g>'
    )

tsvg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{TW_ALL}" height="{TH}" viewBox="0 0 {TW_ALL} {TH}">
<defs><filter id="g" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<style>
.r{{font:bold 15px 'Courier New',monospace}}
.n{{font:bold 11px 'Courier New',monospace;fill:#00ff41}}
.u{{font:10px 'Courier New',monospace;fill:#9dffb0}}
.t{{opacity:0;animation:up .45s ease-out forwards}}
@keyframes up{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1}}}}
</style>
{''.join(items)}
</svg>"""
with open("assets/trophies.svg", "w", encoding="utf-8") as f:
    f.write(tsvg)
print("trophies:", ", ".join(f"{t[0]}={rank(t[2], t[3])}" for t in trophies))
