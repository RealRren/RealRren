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

# Merged PRs. The workflow's GITHUB_TOKEN cannot see private repos, so with an
# optional PRS_TOKEN secret (read-only token of the profile owner) we count
# merged PRs across private repos too; otherwise fall back to public PRs.
merged_prs, pr_unit = totals["prs"], "PRs"
PRS_TOKEN = os.environ.get("PRS_TOKEN", "").strip()
if PRS_TOKEN:
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({
                "query": "query($q:String!){search(query:$q,type:ISSUE,first:1){issueCount}}",
                "variables": {"q": f"is:pr is:merged author:{USER}"},
            }).encode(),
            headers={"Authorization": f"bearer {PRS_TOKEN}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            merged_prs = json.load(r)["data"]["search"]["issueCount"]
        pr_unit = "merged PRs"
    except Exception as e:  # keep the card building even if the token is bad
        print("PRS_TOKEN lookup failed:", e)
trophies = [
    ("CONTRIBUTOR", "total", totals["all"], [1, 100, 300, 700, 1500, 3000, 6000, 10000]),
    ("COMMITTER", "commits", totals["commits"], [1, 50, 200, 500, 1000, 2000, 4000, 8000]),
    ("STEALTH OPS", "private", totals["private"], [1, 50, 200, 500, 1000, 2000, 4000, 8000]),
    ("STREAKER", "day streak", longest, [1, 3, 7, 14, 30, 60, 100, 200]),
    ("GRINDER", "active days", len(active), [1, 20, 50, 100, 200, 365, 600, 1000]),
    ("MERGER", pr_unit, merged_prs, [1, 5, 20, 50, 100, 200, 500, 1000]),
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


# ---------------------------------------------------------------------------
# Player HUD (assets/hud.svg): game-style status bars from the same numbers.
import math as _m


def _next_rank_goal(value, steps):
    for need in steps:
        if value < need:
            return need
    return max(value, steps[-1])


level = int(_m.sqrt(totals["all"] / 5))
lvl_lo, lvl_hi = 5 * level ** 2, 5 * (level + 1) ** 2
pr_goal = _next_rank_goal(merged_prs, [1, 5, 20, 50, 100, 200, 500, 1000])
streak_goal = max(longest, 30)
bars = [
    ("HP", "streak", current, streak_goal, f"{current} / {streak_goal} days", "#00ff41", False),
    ("XP", f"to LVL {level+1}", totals["all"] - lvl_lo, lvl_hi - lvl_lo, f"{fmt(totals['all'])} / {fmt(lvl_hi)}", "#00ff41", True),
    ("MP", "merged PRs", merged_prs, pr_goal, f"{merged_prs} / {pr_goal}", "#9dffb0", False),
]

HW, HH = 820, 210
BX, BW = 250, 440
parts = []
# pixel R avatar
R = ["111110", "110011", "110011", "111110", "111100", "110110", "110011"]
px = 16
for r, row in enumerate(R):
    for c, ch in enumerate(row):
        if ch == "1":
            parts.append(f'<rect x="{62+c*px}" y="{50+r*px}" width="{px-3}" height="{px-3}" fill="#00ff41"/>')
avatar = (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur="1.6s" '
          f'repeatCount="indefinite" calcMode="discrete"/>{"".join(parts)}</g>')
rows = []
for i, (tag, label, val, goal, txt, col, striped) in enumerate(bars):
    y = 62 + i * 42
    w = max(4, round(BW * min(val / goal, 1))) if goal else BW
    fill = 'url(#stripe)' if striped else col
    rows.append(
        f'<text class="tag" x="{BX-14}" y="{y+13}" text-anchor="end">{tag}</text>'
        f'<rect x="{BX}" y="{y}" width="{BW}" height="16" fill="none" stroke="#00ff41" stroke-width="1.5"/>'
        f'<rect x="{BX+3}" y="{y+3}" width="{w-6}" height="10" fill="{fill}">'
        f'<animate attributeName="width" from="0" to="{w-6}" dur="{1.4+0.4*i:.1f}s" begin="{0.3*i:.1f}s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/>'
        f'</rect>'
        f'<text class="lbl" x="{BX}" y="{y-5}">{label}</text>'
        f'<text class="num" x="{BX+BW}" y="{y-5}" text-anchor="end">{txt}</text>'
    )
popups = "".join(
    f'<text class="pop" x="{BX+BW+30}" y="150" opacity="0">{t}'
    f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.15;.7;1" dur="2.4s" begin="{1.2+2.4*i:.1f}s;pop{i}.end+{2.4*(len(bars)-1):.1f}s" id="pop{i}"/>'
    f'<animate attributeName="y" values="150;110" dur="2.4s" begin="{1.2+2.4*i:.1f}s;pop{i}.end+{2.4*(len(bars)-1):.1f}s"/></text>'
    for i, t in enumerate([f"+{fmt(last30)} XP", f"{current}d streak", f"+{merged_prs} MP"]))

hud = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{HW}" height="{HH}" viewBox="0 0 {HW} {HH}">
<defs><pattern id="stripe" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="8" height="10" fill="#00ff41"/>
<animateTransform attributeName="patternTransform" type="translate" from="0 0" to="10 0" dur=".6s" repeatCount="indefinite"/></pattern></defs>
<style>
.h{{font:bold 15px 'Courier New',monospace;fill:#00ff41}}
.tag{{font:bold 15px 'Courier New',monospace;fill:#00ff41}}
.lbl{{font:12px 'Courier New',monospace;fill:#3f8f50}}
.num{{font:bold 12px 'Courier New',monospace;fill:#9dffb0}}
.pop{{font:bold 14px 'Courier New',monospace;fill:#9dffb0}}
.s{{font:11px 'Courier New',monospace;fill:#3f8f50}}
</style>
<rect x="0.75" y="0.75" width="{HW-1.5}" height="{HH-1.5}" rx="8" fill="#000" stroke="#00ff41" stroke-width="1.5"/>
<rect x="44" y="34" width="132" height="148" fill="none" stroke="#00ff41" stroke-opacity=".5"/>
{avatar}
<text class="h" x="110" y="26" text-anchor="middle">PLAYER 1</text>
<text class="s" x="110" y="200" text-anchor="middle">RealRren</text>
<text class="h" x="{BX}" y="30">CLASS: GAMES · MODS · APPS · WEB</text>
<text class="h" x="{BX+BW}" y="30" text-anchor="end">LVL {level}<animate attributeName="opacity" values="1;0;1" dur="1s" calcMode="discrete" repeatCount="indefinite"/></text>
{''.join(rows)}
{popups}
<text class="s" x="{HW-20}" y="{HH-12}" text-anchor="end">updated {today:%Y-%m-%d}</text>
</svg>"""
with open("assets/hud.svg", "w", encoding="utf-8") as f:
    f.write(hud)
print("hud: LVL", level, [(b[0], b[2], b[3]) for b in bars])


# ---------------------------------------------------------------------------
# Activity graph (assets/activity.svg): last 31 days, drawn in-repo so it does
# not depend on an outside graph service.
span = dates[-31:]
vals = [days[d] for d in span]
AW, AH = 820, 300
L_, R_, T_, B_ = 56, 24, 58, 50
pw, ph = AW - L_ - R_, AH - T_ - B_
top = max(vals) or 1
step = 10 ** max(0, len(str(top)) - 1)
ymax = ((top + step - 1) // step) * step
if ymax / step <= 2:
    step = step // 2 or 1
pts = [(L_ + i * pw / (len(vals) - 1), T_ + ph - v / ymax * ph) for i, v in enumerate(vals)]
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
area = f"M{L_},{T_+ph} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{L_+pw},{T_+ph} Z"
seg = sum(((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2) ** .5 for i in range(len(pts)-1))
grid = []
for k in range(0, ymax + 1, step):
    y = T_ + ph - k / ymax * ph
    grid.append(f'<line x1="{L_}" x2="{L_+pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="#00ff41" stroke-opacity=".12"/>'
                f'<text class="ax" x="{L_-10}" y="{y+4:.1f}" text-anchor="end">{k}</text>')
for i in range(0, len(span), 5):
    x = pts[i][0]
    anc = "start" if i == 0 else "end" if i == len(span) - 1 else "middle"
    grid.append(f'<text class="ax" x="{x:.1f}" y="{T_+ph+22}" text-anchor="{anc}">{dt.date.fromisoformat(span[i]):%b %d}</text>')
peak_i = max(range(len(vals)), key=lambda i: vals[i])
dots = "".join(
    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.5 if i == peak_i else 2.6}" fill="{"#fff" if i == peak_i else "#9dffb0"}">'
    f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{(0.15 + 1.8 * i / len(pts)) / (0.35 + 1.8 * i / len(pts)):.3f};1" dur="{0.35 + 1.8 * i / len(pts):.2f}s" begin="0s" fill="freeze"/></circle>'
    for i, (x, y) in enumerate(pts))
px_, py_ = pts[peak_i]
peak_lbl = (f'<text class="pk" x="{min(max(px_, L_+60), L_+pw-60):.1f}" y="{py_-12:.1f}" text-anchor="middle">'
            f'peak {vals[peak_i]}<animate attributeName="opacity" values="0;0;1" keyTimes="0;.84;1" dur="2.5s" begin="0s" fill="freeze"/></text>')
act = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{AW}" height="{AH}" viewBox="0 0 {AW} {AH}">
<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00ff41" stop-opacity=".35"/><stop offset="1" stop-color="#00ff41" stop-opacity="0"/></linearGradient>
<clipPath id="reveal"><rect x="{L_}" y="0" width="{pw}" height="{AH}"><animate attributeName="width" from="0" to="{pw}" dur="1.9s" begin="0s" fill="freeze"/></rect></clipPath></defs>
<style>
.t{{font:bold 15px 'Courier New',monospace;fill:#00ff41}}
.ax{{font:11px 'Courier New',monospace;fill:#3f8f50}}
.pk{{font:bold 12px 'Courier New',monospace;fill:#fff}}
.s{{font:11px 'Courier New',monospace;fill:#3f8f50}}
</style>
<rect x="0.75" y="0.75" width="{AW-1.5}" height="{AH-1.5}" rx="8" fill="#000" stroke="#00ff41" stroke-width="1.5"/>
<text class="t" x="24" y="32">root@realrren:~$ ./activity --last 31d</text>
<text class="s" x="{AW-24}" y="32" text-anchor="end">{fmt(sum(vals))} contributions</text>
{''.join(grid)}
<g clip-path="url(#reveal)"><path d="{area}" fill="url(#ag)"/></g>
<polyline points="{line}" fill="none" stroke="#00ff41" stroke-width="2.5" stroke-linejoin="round" stroke-dasharray="{seg:.0f}" stroke-dashoffset="0">
<animate attributeName="stroke-dashoffset" from="{seg:.0f}" to="0" dur="1.9s" begin="0s" fill="freeze"/></polyline>
{dots}{peak_lbl}
<text class="s" x="{AW-24}" y="{AH-12}" text-anchor="end">updated {today:%Y-%m-%d}</text>
</svg>"""
with open("assets/activity.svg", "w", encoding="utf-8") as f:
    f.write(act)
print("activity: 31d total", sum(vals), "peak", vals[peak_i])
