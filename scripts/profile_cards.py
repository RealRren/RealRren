"""Static green terminal cards for the profile README (run by hand when the text changes).

Writes assets/whoami.svg and assets/focus.svg.
"""
from html import escape
import textwrap

G, L, DIM = "#00ff41", "#9dffb0", "#3f8f50"
STYLE = f"""<style>
.h{{font:bold 15px 'Courier New',monospace;fill:{G}}}
.p{{font:bold 14px 'Courier New',monospace;fill:{G}}}
.k{{font:13px 'Courier New',monospace;fill:{L}}}
.v{{font:bold 13px 'Courier New',monospace;fill:{G}}}
.d{{font:12px 'Courier New',monospace;fill:{DIM}}}
.c{{font:bold 13px 'Courier New',monospace;fill:#000}}
</style>"""


def fade(i, step=0.06):
    t = step * i
    return (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{t/(t+0.3):.3f};1" '
            f'dur="{t+0.3:.2f}s" fill="freeze"/>')


# --- whoami card ----------------------------------------------------------------
W = 820
rows = []   # (kind, payload)
rows += [("cmd", "whoami"),
         ("kv", ("RealRren", "software developer")),
         ("txt", "building desktop apps, mobile apps, websites, games & Minecraft mods"),
         ("kv", ("role", "Lead @ Arcline Studios")),
         ("kv", ("location", "Sri Lanka 🇱🇰")),
         ("gap", None),
         ("cmd", "cat skills.txt")]
skills = [(10, "Game Dev", "Godot (GDScript) · Unreal Engine (C++)"),
          (9, "Minecraft Mods", "Forge 1.20.1 · Java 17 · server-side AI mods"),
          (9, "Mobile Apps", "React Native · Expo · Supabase"),
          (9, "Desktop Apps", "Tauri (Rust + TS) · Electron"),
          (9, "Web Design", "client websites · HTML/CSS/JS · Cloudflare Pages")]
rows += [("skill", s) for s in skills]
rows += [("gap", None), ("cmd", "ls ./projects")]
projects = [("🔒", "[CLASSIFIED]", "most projects are private & in active development"),
            ("📦", "nexora-engine", "quotes, invoices & estimating for contractors"),
            ("⛏", "adaptive-zombie-survival", "Forge mod: zombies that dig, break & pillar to you"),
            ("🌐", "pyromax-site", "fire engineering consultancy site (launching Dec 2026)")]
rows += [("proj", p) for p in projects]
rows += [("gap", None), ("cmd", "echo $STATUS"), ("status", "currently compiling something big... stay tuned")]

LH, y, out = 22, 40, []
for i, (kind, val) in enumerate(rows):
    if kind == "gap":
        y += 12
        continue
    a = fade(i)
    if kind == "cmd":
        y += 6 if i else 0
        out.append(f'<g>{a}<text class="p" x="30" y="{y}">root@realrren:~$ <tspan fill="{L}">{escape(val)}</tspan></text></g>')
    elif kind == "kv":
        k, v = val
        out.append(f'<g>{a}<text class="k" x="30" y="{y}">&gt; {escape(k)}</text><text class="v" x="200" y="{y}">{escape(v)}</text></g>')
    elif kind == "txt":
        out.append(f'<g>{a}<text class="v" x="200" y="{y}">{escape(val)}</text></g>')
    elif kind == "skill":
        lvl, name, det = val
        bars = "".join(f'<rect x="{46+j*11}" y="{y-11}" width="8" height="12" fill="{G if j < lvl else "none"}" stroke="{G}" stroke-width="1"/>' for j in range(10))
        out.append(f'<g>{a}<text class="k" x="30" y="{y}">&gt;</text>{bars}'
                   f'<text class="v" x="170" y="{y}">{escape(name)}</text><text class="k" x="330" y="{y}">{escape(det)}</text></g>')
    elif kind == "proj":
        ic, name, det = val
        out.append(f'<g>{a}<text class="k" x="30" y="{y}">&gt; {ic}</text><text class="v" x="70" y="{y}">{escape(name)}</text>'
                   f'<text class="k" x="290" y="{y}">{escape(det)}</text></g>')
    elif kind == "status":
        out.append(f'<g>{a}<text class="v" x="30" y="{y}">&gt; {escape(val)}<tspan>_<animate attributeName="opacity" values="1;0;1" dur="1s" calcMode="discrete" repeatCount="indefinite"/></tspan></text></g>')
    y += LH
H = y + 8
who = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
{STYLE}
<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="8" fill="#000" stroke="{G}" stroke-width="1.5"/>
{''.join(out)}
</svg>'''
open("assets/whoami.svg", "w", encoding="utf-8").write(who)

# --- focus areas -------------------------------------------------------------------
areas = [("🎮", "/game_dev", ["Godot · Unreal Engine", "Minecraft Forge", "GDScript · C++ · Java"],
          "gameplay systems, AI, survival & zombie games, Minecraft mods"),
         ("📱", "/mobile_apps", ["React Native · Expo", "TypeScript · Supabase"],
          "cross-platform apps for Android & iOS"),
         ("🖥", "/desktop_apps", ["Tauri · Electron", "Rust · TypeScript · JS"],
          "fast native tools that work online & offline"),
         ("🌐", "/web_design", ["HTML · CSS · JS", "Cloudflare Pages"],
          "fast, responsive websites for businesses")]
BW, GAP, FH = 193, 12, 222
cells = []
for i, (ic, title, lines, sub) in enumerate(areas):
    x = i * (BW + GAP) + 1
    cx = x + BW / 2
    a = fade(i, 0.15)
    tw = len(title) * 8 + 18
    parts = [f'<rect x="{x}" y="1" width="{BW}" height="{FH-2}" rx="8" fill="#000" stroke="{G}" stroke-width="1.5"/>',
             f'<text x="{cx}" y="40" text-anchor="middle" font-size="24">{ic}</text>',
             f'<rect x="{cx-tw/2}" y="54" width="{tw}" height="22" rx="4" fill="{G}"/>',
             f'<text class="c" x="{cx}" y="70" text-anchor="middle">{escape(title)}</text>']
    for j, ln in enumerate(lines):
        parts.append(f'<text class="k" x="{cx}" y="{102+j*20}" text-anchor="middle">{escape(ln)}</text>')
    for j, ln in enumerate(textwrap.wrap(sub, 26)):
        parts.append(f'<text class="d" x="{cx}" y="{176+j*16}" text-anchor="middle">{escape(ln)}</text>')
    cells.append(f'<g>{a}{"".join(parts)}</g>')
FW = 4 * BW + 3 * GAP + 2
focus = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{FW}" height="{FH}" viewBox="0 0 {FW} {FH}">
{STYLE}
{''.join(cells)}
</svg>'''
open("assets/focus.svg", "w", encoding="utf-8").write(focus)
print("whoami", W, H, "focus", FW, FH)
