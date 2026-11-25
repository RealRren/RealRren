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
