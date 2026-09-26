#!/usr/bin/env python3
"""Build the animated SVG artwork used by README.md.

Every visual on the profile (hero, section headers, cards, buttons, footer) is
generated here, so to change a project, a roadmap step or a link, edit the
DATA section below and re-run:

    pip install fonttools brotli uharfbuzz
    python3 scripts/build_assets.py

Fonts (Space Grotesk, JetBrains Mono, Inter, Noto Sans Sinhala - SIL OFL) and
tech icons (tandpfun/skill-icons - MIT) are downloaded once into .cache/.
Each SVG embeds only the glyphs it uses as base64 WOFF2, so the artwork looks
identical on every device and never loads anything from the network.
"""

from __future__ import annotations

import base64
import io
import math
import random
import re
import unicodedata
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CACHE = ROOT / ".cache"

# --------------------------------------------------------------------------
# DATA
# --------------------------------------------------------------------------

FIRST, LAST = "Ushan", "Nethsara"
HANDLE = "ushan829"
ROLES = ["Full Stack Developer", "UI/UX Designer", "Creative Developer", "Senior Frontend Engineer"]
TAGLINE = "Building products that make education accessible for everyone."
MARQUEE = [
    "Building products for Sri Lankan students",
    "Crafting premium digital experiences",
    "Always learning something new",
    "Education",
    "Open source",
    "UI/UX research",
]
HERO_CHIPS = [("Next.js", "#E2E8F0"), ("Figma", "#F472B6"), ("TypeScript", "#60A5FA"), ("Supabase", "#34D399")]

ABOUT_WHOAMI = "Ushan Nethsara — Full Stack Developer / UI Designer"
ABOUT_JSON = [
    ("location", '"Sri Lanka"'),
    ("focus", '"Ape Danuma & Educational Platforms"'),
    ("learning", '["Advanced AI Integration", "Cloud Architecture"]'),
    ("interests", '["Education", "Open Source", "UI/UX Research"]'),
    ("mission", '"Make education accessible for everyone"'),
]

TOOLKIT = [
    ("Frontend", "#22D3EE", ["nextjs", "react", "ts", "js", "tailwind", "html", "css", "framer"]),
    ("Backend", "#34D399", ["nodejs", "express", "python", "django"]),
    ("Database", "#FBBF24", ["mongodb", "postgres", "mysql", "prisma"]),
    ("Cloud", "#60A5FA", ["supabase", "docker", "cloudflare", "vercel", "aws", "gcp"]),
    ("Languages", "#F472B6", ["ts", "js", "python", "cpp", "java"]),
    ("Tools", "#A78BFA", ["git", "github", "linux", "vscode", "postman", "bash"]),
    ("Design", "#FB7185", ["figma", "photoshop", "illustrator", "pr", "ae", "xd"]),
]
DAILY_DRIVERS = [("VS Code", "#3B82F6"), ("Linux", "#FBBF24"), ("Brave", "#FB923C"), ("Zsh", "#34D399"), ("npm", "#F87171")]

PROJECTS = [
    {
        "name": "Ape Danuma",
        "desc": "Digital product platform for Sri Lankan students.",
        "stack": ["nextjs", "ts", "tailwind"],
        "stack_label": "Next.js · TypeScript · Tailwind",
        "status": "active",
        "glyph": "letter",
        "accent": ("#F59E0B", "#EC4899"),
    },
    {
        "name": "Educational LMS",
        "desc": "Comprehensive Learning Management System.",
        "stack": ["react", "nodejs", "mongodb"],
        "stack_label": "React · Node.js · MongoDB",
        "status": "progress",
        "glyph": "cap",
        "accent": ("#8B5CF6", "#3B82F6"),
    },
    {
        "name": "Commerce.lk",
        "desc": "Modern e-commerce solution with advanced features.",
        "stack": ["nextjs", "supabase", "vercel"],
        "stack_label": "Next.js · Supabase · Vercel",
        "status": "active",
        "glyph": "bag",
        "accent": ("#06B6D4", "#10B981"),
    },
    {
        "name": "AI Educational Tools",
        "desc": "AI-driven tools to assist student learning paths.",
        "stack": ["python", "react", "docker"],
        "stack_label": "Python · React · Docker",
        "status": "planning",
        "glyph": "spark",
        "accent": ("#EC4899", "#8B5CF6"),
    },
]

ROADMAP = [
    ("Designing the architecture for Ape Danuma", "done"),
    ("Developing core components for LMS Platform", "done"),
    ("Integrating advanced AI models for student assistance", "progress"),
    ("Launching the next phase of Educational Apps", "planning"),
    ("Contributing to open-source UI libraries", "planning"),
]

STATUS = {
    "done": ("Completed", "#34D399"),
    "active": ("Active", "#34D399"),
    "progress": ("In progress", "#FBBF24"),
    "planning": ("Planning", "#94A3B8"),
}

HEADERS = [
    ("about", "About", "Who's behind the pixels", "whoami"),
    ("toolkit", "Toolkit", "Tools of the craft", "stack.config"),
    ("work", "Work", "Featured projects", "selected work"),
    ("now", "Now", "Currently building", "roadmap.md"),
    ("stats", "Stats", "Commit history", "consistency > intensity"),
    ("connect", "Connect", "Let's build together", "say hello"),
]

LINKS = [
    ("website", "Website", "ushan829.github.io", "#22D3EE"),
    ("portfolio", "Portfolio", "github.com/ushan829", "#A78BFA"),
    ("linkedin", "LinkedIn", "in/ushan829", "#3B82F6"),
    ("x", "X", "@ushan829", "#E2E8F0"),
    ("discord", "Discord", "ushan829", "#5865F2"),
    ("email", "Email", "ushan829@gmail.com", "#EA4335"),
]

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

INK = "#F8FAFC"
TEXT = "#E2E8F0"
MUTED = "#94A3B8"
DIM = "#64748B"
FAINT = "#334155"
PINK, VIOLET, BLUE, CYAN = "#F472B6", "#A78BFA", "#60A5FA", "#22D3EE"

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONT_FILES = {
    "SpaceGrotesk": "spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "JetBrainsMono": "jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    "Inter": "inter/Inter%5Bopsz,wght%5D.ttf",
    "NotoSansSinhala": "notosanssinhala/NotoSansSinhala%5Bwdth,wght%5D.ttf",
}
# css family -> (source font, axis location)
FACES = {
    "sg7": ("SpaceGrotesk", {"wght": 700}),
    "sg5": ("SpaceGrotesk", {"wght": 500}),
    "jb4": ("JetBrainsMono", {"wght": 400}),
    "jb6": ("JetBrainsMono", {"wght": 600}),
    "in4": ("Inter", {"wght": 400, "opsz": 14}),
    "in6": ("Inter", {"wght": 600, "opsz": 14}),
    "si6": ("NotoSansSinhala", {"wght": 600, "wdth": 100}),
}
STACKS = {
    "sg7": "sg7,'Space Grotesk',system-ui,sans-serif",
    "sg5": "sg5,'Space Grotesk',system-ui,sans-serif",
    "jb4": "jb4,'JetBrains Mono',ui-monospace,monospace",
    "jb6": "jb6,'JetBrains Mono',ui-monospace,monospace",
    "in4": "in4,Inter,system-ui,sans-serif",
    "in6": "in6,Inter,system-ui,sans-serif",
    "si6": "si6,'Noto Sans Sinhala','Iskoola Pota','Nirmala UI',sans-serif",
}

SKILL_ICONS = "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/"
ICON_FILES = {
    "nextjs": "NextJS-Dark", "react": "React-Dark", "ts": "TypeScript", "js": "JavaScript",
    "tailwind": "TailwindCSS-Dark", "html": "HTML", "css": "CSS", "nodejs": "NodeJS-Dark",
    "express": "ExpressJS-Dark", "python": "Python-Dark", "django": "Django", "mongodb": "MongoDB",
    "postgres": "PostgreSQL-Dark", "mysql": "MySQL-Dark", "prisma": "Prisma",
    "supabase": "Supabase-Dark", "docker": "Docker", "cloudflare": "Cloudflare-Dark",
    "vercel": "Vercel-Dark", "aws": "AWS-Dark", "gcp": "GCP-Dark", "cpp": "CPP", "java": "Java-Dark",
    "git": "Git", "github": "Github-Dark", "linux": "Linux-Dark", "vscode": "VSCode-Dark",
    "postman": "Postman", "bash": "Bash-Dark", "figma": "Figma-Dark", "photoshop": "Photoshop",
    "illustrator": "Illustrator", "pr": "Premiere", "ae": "AfterEffects", "xd": "XD",
    "linkedin": "LinkedIn", "discord": "Discord", "email": "Gmail-Dark",
}
TILE = '<rect width="256" height="256" rx="60" fill="#242938"/>'
# Icons skill-icons doesn't ship, drawn on the same 256px tile.
CUSTOM_ICONS = {
    "framer": TILE + '<path fill="#fff" transform="translate(53 53) scale(6.25)" d="M4 0h16v8h-8zM4 8h8l8 8H4zM4 16h8v8z"/>',
    "x": '<rect width="256" height="256" rx="60" fill="#000"/><path fill="#fff" transform="translate(56 56) scale(6)" '
    'd="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/>',
    "website": TILE + '<g fill="none" stroke="#22D3EE" stroke-width="12" stroke-linecap="round">'
    '<circle cx="128" cy="128" r="72"/><ellipse cx="128" cy="128" rx="30" ry="72"/><path d="M58 128h140M70 92h116M70 164h116"/></g>',
    "portfolio": TILE + '<rect x="62" y="62" width="58" height="58" rx="16" fill="#F472B6"/><rect x="136" y="62" width="58" height="58" rx="16" fill="#A78BFA"/>'
    '<rect x="62" y="136" width="58" height="58" rx="16" fill="#60A5FA"/><rect x="136" y="136" width="58" height="58" rx="16" fill="#22D3EE"/>',
}


def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {url}")
        with urllib.request.urlopen(url) as r:
            dest.write_bytes(r.read())
    return dest


_static: dict[str, bytes] = {}
_hb: dict[str, hb.Font] = {}


def static_font(face: str) -> bytes:
    """A static instance of the face's variable font, cached on disk."""
    if face not in _static:
        path = CACHE / "fonts" / f"{face}.ttf"
        if not path.exists():
            src, loc = FACES[face]
            vf = TTFont(fetch(GOOGLE_FONTS + FONT_FILES[src], CACHE / "fonts" / f"{src}-VF.ttf"))
            instancer.instantiateVariableFont(vf, loc, inplace=True)
            vf.save(path)
        _static[face] = path.read_bytes()
    return _static[face]


def measure(s: str, face: str, size: float, ls: float = 0) -> float:
    """Shaped advance width of s, matching what the browser will lay out."""
    if face not in _hb:
        _hb[face] = hb.Font(hb.Face(hb.Blob(static_font(face))))
    font = _hb[face]
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    adv = sum(p.x_advance for p in buf.glyph_positions)
    return adv / font.face.upem * size + ls * len(s)


def font_face(face: str, chars: str) -> str:
    font = TTFont(io.BytesIO(static_font(face)))
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.hinting = False
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    # Split vowels (e.g. Sinhala ෝ) are shaped from their decomposed parts, so
    # those code points must stay in the cmap too.
    sub.populate(text=chars + unicodedata.normalize("NFD", chars))
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{face};src:url(data:font/woff2;base64,{data}) format('woff2')}}"


def wrap(s: str, face: str, size: float, width: float) -> list[str]:
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if line and measure(trial, face, size) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def wrap_balanced(s: str, face: str, size: float, width: float) -> list[str]:
    """Like wrap(), but narrows the measure while the line count holds (text-wrap: balance)."""
    lines = wrap(s, face, size, width)
    while width > size and len(narrower := wrap(s, face, size, width - 2)) == len(lines):
        lines, width = narrower, width - 2
    return lines


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------


def n(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def icon_symbol(key: str) -> str:
    if key in CUSTOM_ICONS:
        inner = CUSTOM_ICONS[key]
    else:
        raw = fetch(SKILL_ICONS + ICON_FILES[key] + ".svg", CACHE / "icons" / f"{ICON_FILES[key]}.svg").read_text()
        inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", raw.strip(), flags=re.S)
        inner = re.sub(r'id="([^"]+)"', rf'id="{key}-\1"', inner)
        inner = re.sub(r"url\(#([^)]+)\)", rf"url(#{key}-\1)", inner)
        inner = re.sub(r'href="#([^"]+)"', rf'href="#{key}-\1"', inner)
    return f'<symbol id="i-{key}" viewBox="0 0 256 256">{inner}</symbol>'


BASE_CSS = """
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-out infinite}
.blink{animation:blink 1.1s steps(1) infinite}
.tw{animation:tw 4s ease-in-out infinite}
.bob{animation:bob 4s ease-in-out infinite}
@keyframes pulse{0%{transform:scale(1);opacity:.8}100%{transform:scale(3);opacity:0}}
@keyframes blink{50%{opacity:0}}
@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


class Svg:
    def __init__(self, w: float, h: float, title: str):
        self.w, self.h, self.title = w, h, title
        self.defs: list[str] = []
        self.css: list[str] = [BASE_CSS]
        self.body: list[str] = []
        self.icons: set[str] = set()
        self.glyphs: dict[str, set[str]] = {}

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def text(self, x, y, s, face, size, fill=TEXT, anchor="start", ls=0, attrs="") -> str:
        return self.runs(x, y, [(s, fill)], face, size, anchor, ls, attrs)

    def runs(self, x, y, parts, face, size, anchor="start", ls=0, attrs="") -> str:
        self.glyphs.setdefault(face, set()).update("".join(t for t, _ in parts))
        extra = f' text-anchor="{anchor}"' if anchor != "start" else ""
        extra += f' letter-spacing="{n(ls)}"' if ls else ""
        if len(parts) == 1:
            fill = f' fill="{parts[0][1]}"'
            inner = escape(parts[0][0])
        else:
            fill = ""
            inner = "".join(f'<tspan fill="{f}">{escape(t)}</tspan>' for t, f in parts)
        return (
            f'<text x="{n(x)}" y="{n(y)}" font-family="{STACKS[face]}" font-size="{n(size)}"{fill}{extra}'
            f' xml:space="preserve" style="white-space:pre"{attrs}>{inner}</text>'
        )

    def icon(self, key: str, x, y, size, attrs="") -> str:
        self.icons.add(key)
        return f'<use href="#i-{key}" x="{n(x)}" y="{n(y)}" width="{n(size)}" height="{n(size)}"{attrs}/>'

    def render(self) -> str:
        fonts = "".join(font_face(f, "".join(sorted(c))) for f, c in sorted(self.glyphs.items()))
        defs = "".join(self.defs) + "".join(icon_symbol(k) for k in sorted(self.icons))
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(self.w)}" height="{n(self.h)}" '
            f'viewBox="0 0 {n(self.w)} {n(self.h)}" fill="none" role="img" aria-labelledby="title">'
            f'<title id="title">{escape(self.title)}</title>'
            f"<style><![CDATA[{fonts}{''.join(self.css)}]]></style>"
            f"<defs>{defs}</defs>{''.join(self.body)}</svg>\n"
        )

    def save(self, name: str) -> None:
        path = ASSETS / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render())
        print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


def radial(id_: str, color: str, opacity: float, cx=".5", cy=".5", r=".5") -> str:
    return (
        f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
    )


def linear(id_: str, stops: list[tuple[float, str, float]], x1=0, y1=0, x2=1, y2=0, user=False, extra="") -> str:
    units = ' gradientUnits="userSpaceOnUse"' if user else ""
    s = "".join(f'<stop offset="{n(o)}" stop-color="{c}" stop-opacity="{n(a)}"/>' for o, c, a in stops)
    return f'<linearGradient id="{id_}" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}"{units}>{s}{extra}</linearGradient>'


def card_defs(svg: Svg) -> None:
    svg.defs.append(linear("cardbg", [(0, "#0D1326", 1), (1, "#070A14", 1)], 0, 0, 0.3, 1))
    svg.defs.append(linear("edge", [(0, "#FFFFFF", 0.2), (0.45, "#FFFFFF", 0.04), (1, "#FFFFFF", 0.12)], 0, 0, 1, 1))


def card(x, y, w, h, rx=24, stroke="url(#edge)") -> str:
    return (
        f'<rect x="{n(x + 0.75)}" y="{n(y + 0.75)}" width="{n(w - 1.5)}" height="{n(h - 1.5)}" rx="{rx}" '
        f'fill="url(#cardbg)" stroke="{stroke}" stroke-width="1.5"/>'
    )


def stars(rnd: random.Random, count: int, w: float, h: float, avoid=None) -> str:
    out = []
    for _ in range(count):
        x, y = rnd.uniform(12, w - 12), rnd.uniform(12, h - 12)
        if avoid and avoid(x, y):
            continue
        r = rnd.choice([0.6, 0.8, 1, 1.2, 1.6])
        dur, delay = rnd.uniform(2.5, 6), rnd.uniform(0, 6)
        out.append(
            f'<circle cx="{n(x)}" cy="{n(y)}" r="{r}" fill="#fff" class="tw" '
            f'style="animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s"/>'
        )
    return "".join(out)


def pill(svg: Svg, x, y, label, color, face="jb6", size=12, ls=2, h=30, dot=True, anchor="start") -> str:
    tw = measure(label, face, size, ls)
    w = tw + (40 if dot else 26)
    if anchor == "end":
        x -= w
    elif anchor == "middle":
        x -= w / 2
    parts = [
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" fill="{color}" fill-opacity=".1" '
        f'stroke="{color}" stroke-opacity=".35"/>'
    ]
    tx = x + 13
    if dot:
        cy = y + h / 2
        parts.append(f'<circle cx="{n(x + 16)}" cy="{n(cy)}" r="4" fill="{color}" class="pulse"/>')
        parts.append(f'<circle cx="{n(x + 16)}" cy="{n(cy)}" r="4" fill="{color}"/>')
        tx = x + 28
    parts.append(svg.text(tx, y + h / 2 + size * 0.36, label, face, size, color, ls=ls))
    return "".join(parts)


# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------


def build_hero() -> None:
    W, H = 1200, 520
    s = Svg(W, H, f"{FIRST} {LAST} — {' · '.join(ROLES[:3])}")
    rnd = random.Random(829)
    card_defs(s)
    s.defs += [
        f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="28"/></clipPath>',
        radial("a1", "#8B5CF6", 0.55), radial("a2", "#EC4899", 0.4), radial("a3", "#22D3EE", 0.3), radial("a4", "#3B82F6", 0.45),
        '<pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" stroke="#94A3B8" stroke-opacity=".09"/></pattern>',
        '<radialGradient id="fade" cx=".42" cy=".4" r=".7"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
        f'<mask id="gridmask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>',
        # repeating pink→violet→cyan band that slides under the surname
        linear(
            "shine",
            [(i / 9, c, 1) for i, c in enumerate([PINK, VIOLET, CYAN] * 3 + [PINK])],
            0, 0, 1920, 0, user=True,
            extra='<animateTransform attributeName="gradientTransform" type="translate" from="-1280 0" to="-640 0" dur="7s" repeatCount="indefinite"/>',
        ),
        radial("glow", "#8B5CF6", 0.5),
        '<radialGradient id="sphere" cx=".34" cy=".3" r=".8"><stop offset="0" stop-color="#F5D0FE"/><stop offset=".22" stop-color="#A78BFA"/>'
        '<stop offset=".55" stop-color="#5B21B6"/><stop offset=".85" stop-color="#1E1B4B"/><stop offset="1" stop-color="#0B0A24"/></radialGradient>',
        linear("rim", [(0, CYAN, 0.9), (0.5, VIOLET, 0.2), (1, PINK, 0.8)], 0, 0, 1, 1),
        linear("ring1", [(0, CYAN, 0), (0.5, CYAN, 0.8), (1, VIOLET, 0.1)]),
        linear("ring2", [(0, PINK, 0.1), (0.5, VIOLET, 0.7), (1, PINK, 0)]),
        linear("band", [(0, "#fff", 0), (0.5, "#fff", 0.12), (1, "#fff", 0)]),
        '<filter id="soft" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="18"/></filter>',
    ]
    s.css.append("""
.drift{transform-box:fill-box;transform-origin:center;animation:drift 16s ease-in-out infinite alternate}
.breathe{transform-box:fill-box;transform-origin:center;animation:breathe 7s ease-in-out infinite}
.r{opacity:0;animation:role 12s infinite}
.mq{animation:mq 60s linear infinite}
@keyframes drift{0%{transform:translate(0,0) scale(1)}100%{transform:translate(-70px,36px) scale(1.18)}}
@keyframes breathe{0%,100%{transform:scale(1);opacity:.85}50%{transform:scale(1.08);opacity:1}}
@keyframes role{0%{opacity:0;transform:translateY(12px)}4%,21%{opacity:1;transform:translateY(0)}25%,100%{opacity:0;transform:translateY(-12px)}}
@media (prefers-reduced-motion:reduce){.r0{opacity:1}}
""")

    s.add('<g clip-path="url(#clip)">', f'<rect width="{W}" height="{H}" fill="#05070F"/>')
    # aurora
    for cls_delay, (cx, cy, rx, ry, g) in enumerate(
        [(930, 110, 460, 280, "a1"), (1120, 470, 380, 220, "a2"), (180, 520, 460, 220, "a3"), (560, -20, 420, 200, "a4")]
    ):
        s.add(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{g})" class="drift" '
            f'style="animation-delay:-{cls_delay * 4}s;animation-duration:{14 + cls_delay * 3}s"/>'
        )
    s.add(f'<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gridmask)"/>')
    s.add(stars(rnd, 70, W, 460, avoid=lambda x, y: 60 < x < 640 and 120 < y < 440))

    # --- globe -----------------------------------------------------------
    cx, cy, R = 935, 245, 108
    rings = [(190, 44, -16, "ring1", CYAN, 9), (238, 66, 11, "ring2", PINK, 14)]
    s.defs.append(f'<clipPath id="globe"><circle cx="{cx}" cy="{cy}" r="{R}"/></clipPath>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="260" fill="url(#glow)" class="breathe"/>')

    def orbit(rx, ry):
        return f"M{-rx} 0A{rx} {ry} 0 1 0 {rx} 0A{rx} {ry} 0 1 0 {-rx} 0"

    def dot(rx, ry, color, dur, front):
        vis = (
            f'<animate attributeName="opacity" values="1;0" keyTimes="0;.5" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>'
            if front else ""
        )
        return (
            f'<g><circle r="9" fill="{color}" opacity=".25"/><circle r="4" fill="{color}"/>{vis}'
            f'<animateMotion path="{orbit(rx, ry)}" dur="{dur}s" repeatCount="indefinite"/></g>'
        )

    for rx, ry, rot, grad, color, dur in rings:  # back halves + dots travelling behind the sphere
        s.add(
            f'<g transform="translate({cx} {cy}) rotate({rot})"><ellipse rx="{rx}" ry="{ry}" stroke="url(#{grad})" '
            f'stroke-width="1.4" stroke-dasharray="{"none" if grad == "ring1" else "3 7"}"/>{dot(rx, ry, color, dur, False)}</g>'
        )
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#sphere)"/>')
    wire = [f'<g clip-path="url(#globe)" stroke="#EDE9FE" stroke-opacity=".3" stroke-width="1.1">']
    for lat in (-60, -30, 0, 30, 60):
        rad = math.radians(lat)
        wire.append(
            f'<ellipse cx="{cx}" cy="{n(cy - R * math.sin(rad) * 0.96)}" rx="{n(R * math.cos(rad))}" ry="{n(R * math.cos(rad) * 0.2)}"/>'
        )
    for i in range(6):  # meridians whose width oscillates → the globe appears to spin
        wire.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{R}" ry="{R}"><animate attributeName="rx" values="{R};0;{R}" '
            f'keyTimes="0;.5;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" dur="12s" begin="-{i * 2}s" '
            f'repeatCount="indefinite"/></ellipse>'
        )
    wire.append("</g>")
    s.add(*wire)
    s.add(
        f'<circle cx="{cx}" cy="{cy}" r="{R}" stroke="url(#rim)" stroke-width="1.6"/>',
        f'<ellipse cx="{cx - 36}" cy="{cy - 44}" rx="38" ry="22" fill="#fff" opacity=".18" transform="rotate(-30 {cx - 36} {cy - 44})"/>',
    )
    for rx, ry, rot, grad, color, dur in rings:  # front halves drawn over the sphere
        s.add(
            f'<g transform="translate({cx} {cy}) rotate({rot})"><path d="M{-rx} 0A{rx} {ry} 0 0 0 {rx} 0" stroke="url(#{grad})" '
            f'stroke-width="1.6" stroke-dasharray="{"none" if grad == "ring1" else "3 7"}"/>{dot(rx, ry, color, dur, True)}</g>'
        )

    # floating chips around the globe
    for i, ((label, color), (x, y)) in enumerate(zip(HERO_CHIPS, [(740, 118), (1052, 116), (722, 352), (1040, 384)])):
        w = measure(label, "in6", 15) + 42
        s.add(
            f'<g class="bob" style="animation-delay:-{i * 1.1:.1f}s;animation-duration:{4.5 + i * 0.6:.1f}s">'
            f'<rect x="{x}" y="{y}" width="{n(w)}" height="36" rx="18" fill="#0B1022" fill-opacity=".85" stroke="#fff" stroke-opacity=".14"/>'
            f'<circle cx="{x + 18}" cy="{y + 18}" r="4.5" fill="{color}"/>'
            + s.text(x + 30, y + 23.5, label, "in6", 15, TEXT)
            + "</g>"
        )

    # --- left column -------------------------------------------------------
    hello, hi = "ආයුබෝවන්", "Hello there, I'm"
    w1 = measure(hello, "si6", 17)
    w2 = measure(hi, "in4", 16)
    pw = 46 + w1 + 26 + w2 + 20
    s.add(
        f'<rect x="72" y="60" width="{n(pw)}" height="42" rx="21" fill="#0B1022" fill-opacity=".8" stroke="#fff" stroke-opacity=".14"/>',
        f'<circle cx="96" cy="81" r="5" fill="#34D399" class="pulse"/><circle cx="96" cy="81" r="5" fill="#34D399"/>',
        s.text(114, 87, hello, "si6", 17, INK),
        f'<circle cx="{n(114 + w1 + 13)}" cy="81" r="2" fill="{DIM}"/>',
        s.text(114 + w1 + 26, 86.5, hi, "in4", 16, MUTED),
    )
    s.add(
        s.text(1128, 88, "SRI LANKA  ·  7.87°N 80.77°E", "jb4", 13, DIM, anchor="end", ls=2),
        f'<g opacity=".5" filter="url(#soft)">{s.text(66, 318, LAST, "sg7", 112, VIOLET, ls=-3)}</g>',
        s.text(66, 212, FIRST, "sg7", 112, INK, ls=-3),
        s.runs(66, 318, [(LAST, "url(#shine)"), (".", PINK)], "sg7", 112, ls=-3),
    )
    s.add(s.text(72, 384, "❯", "jb6", 26, PINK))
    for i, role in enumerate(ROLES):
        rw = measure(role, "jb4", 26)
        s.add(
            f'<g class="r r{i}" style="animation-delay:{i * 3}s">{s.text(106, 384, role, "jb4", 26, TEXT)}'
            f'<rect x="{n(110 + rw)}" y="362" width="13" height="28" rx="2" fill="{VIOLET}" class="blink"/></g>'
        )
    s.add(s.text(72, 432, TAGLINE, "in4", 19, MUTED))

    # marquee
    item_text = "  •  ".join(m.upper() for m in MARQUEE) + "  •  "
    mw = measure(item_text, "jb4", 13, 3)
    s.css.append(f"@keyframes mq{{to{{transform:translateX(-{n(mw)}px)}}}}")
    s.add(
        f'<rect y="468" width="{W}" height="52" fill="#fff" fill-opacity=".02"/>',
        f'<rect y="468" width="{W}" height="1" fill="url(#band)"/>',
        f'<g class="mq">{s.text(0, 499, item_text * 3, "jb4", 13, DIM, ls=3)}</g>',
    )
    s.add("</g>", f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="28" stroke="url(#edge)" stroke-width="1.5"/>')
    s.save("hero.svg")


# --------------------------------------------------------------------------
# Section headers
# --------------------------------------------------------------------------


def build_headers() -> None:
    # Transparent background: every colour here sits around 4:1 contrast on both
    # GitHub's light (#ffffff) and dark (#0d1117) themes.
    W, H = 1200, 132
    for i, (slug, label, title, comment) in enumerate(HEADERS, 1):
        s = Svg(W, H, f"{i:02d} — {label}: {title}")
        tw = measure(title, "sg7", 52, -1)
        s.defs += [
            linear("lab", [(0, "#EC4899", 1), (1, "#8B5CF6", 1)], 0, 0, 1, 0),
            linear("ttl", [(0, "#A855F7", 1), (0.45, "#6366F1", 1), (1, "#0891B2", 1)], 0, 0, tw, 0, user=True),
            linear("line", [(0, "#A855F7", 0.7), (0.5, "#3B82F6", 0.35), (1, "#3B82F6", 0)], 0, 0, 1, 0),
            linear("spark", [(0, "#EC4899", 0), (0.5, "#EC4899", 1), (1, "#EC4899", 0)], 0, 0, 1, 0),
        ]
        s.add(
            s.text(2, 34, f"{i:02d}  /  {label.upper()}", "jb6", 15, "url(#lab)", ls=4),
            s.text(0, 100, title, "sg7", 52, "url(#ttl)", ls=-1),
            s.text(W, 100, f"// {comment}", "jb4", 16, "#7D8590", anchor="end"),
            f'<rect y="122" width="{W}" height="1.5" rx=".75" fill="url(#line)"/>',
            f'<rect x="-180" y="121.25" width="180" height="3" rx="1.5" fill="url(#spark)">'
            f'<animate attributeName="x" values="-180;{W}" dur="6s" begin="{i * 0.7:.1f}s" repeatCount="indefinite"/></rect>',
        )
        s.save(f"headers/{i:02d}-{slug}.svg")


# --------------------------------------------------------------------------
# About — terminal
# --------------------------------------------------------------------------


def build_about() -> None:
    W, H = 1200, 520
    s = Svg(W, H, f"whoami: {ABOUT_WHOAMI}. " + "; ".join(f"{k}: {v}" for k, v in ABOUT_JSON).replace('"', ""))
    card_defs(s)
    s.defs += [
        f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="24"/></clipPath>',
        radial("g1", "#8B5CF6", 0.35), radial("g2", "#22D3EE", 0.18),
        linear("ring", [(0, PINK, 1), (0.5, VIOLET, 1), (1, CYAN, 0)], 0, 0, 1, 1),
        linear("mono", [(0, PINK, 1), (0.5, VIOLET, 1), (1, CYAN, 1)], 0, 0, 1, 1),
    ]
    s.css.append(
        ".spin{transform-box:fill-box;transform-origin:center;animation:spin 9s linear infinite}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
    )
    s.add(card(0, 0, W, H), '<g clip-path="url(#clip)">')
    s.add(
        f'<circle cx="1040" cy="260" r="300" fill="url(#g1)"/>',
        f'<circle cx="200" cy="520" r="320" fill="url(#g2)"/>',
        f'<rect width="{W}" height="52" fill="#fff" fill-opacity=".03"/>',
        f'<rect y="52" width="{W}" height="1" fill="#fff" fill-opacity=".07"/>',
        '<circle cx="30" cy="26" r="6.5" fill="#FF5F57"/><circle cx="52" cy="26" r="6.5" fill="#FEBC2E"/><circle cx="74" cy="26" r="6.5" fill="#28C840"/>',
        s.text(W / 2, 31, f"{HANDLE}@srilanka: ~/profile", "jb4", 14, DIM, anchor="middle"),
        s.text(W - 28, 31, "zsh", "jb4", 13, FAINT, anchor="end"),
        f'<rect x="880" y="84" width="1" height="400" fill="#fff" fill-opacity=".07"/>',
    )

    # terminal lines: ("cmd", text) are typed out, ("out", runs) appear at once
    key_w = max(len(k) for k, _ in ABOUT_JSON) + 2
    json_lines = [("out", [("{", DIM)])]
    for j, (k, v) in enumerate(ABOUT_JSON):
        comma = "," if j < len(ABOUT_JSON) - 1 else ""
        v_runs = [(tok, DIM if tok in '[],' or tok.isspace() else "#67E8F9") for tok in re.findall(r'"[^"]*"|[\[\],]|\s+', v)]
        json_lines.append(("out", [("  ", DIM), (f'"{k}"'.ljust(key_w), "#C4B5FD"), (": ", DIM), *v_runs, (comma, DIM)]))
    json_lines.append(("out", [("}", DIM)]))
    lines = [("cmd", "whoami"), ("out", [(ABOUT_WHOAMI, TEXT)]), ("cmd", "cat profile.json"), *json_lines, ("cmd", "")]

    x0, y, lh, size = 44, 100, 34, 19
    cw = measure("M", "jb4", size)
    t = 0.5
    for li, (kind, content) in enumerate(lines):
        if kind == "cmd":
            prompt = s.text(x0, y, "❯", "jb6", size, PINK)
            s.add(f'<g opacity="0">{prompt}<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></g>')
            tx = x0 + cw * 2
            if content:
                steps = len(content)
                start, dur = t + 0.35, steps * 0.06
                widths = ";".join(n(cw * k) for k in range(steps + 1))
                s.defs.append(
                    f'<clipPath id="type{li}"><rect x="{n(tx)}" y="{y - 24}" width="0" height="{lh}">'
                    f'<animate attributeName="width" values="{widths}" calcMode="discrete" begin="{start:.2f}s" dur="{dur + 0.06:.2f}s" fill="freeze"/>'
                    f"</rect></clipPath>"
                )
                s.add(f'<g clip-path="url(#type{li})">{s.text(tx, y, content, "jb4", size, TEXT)}</g>')
                xs = ";".join(n(tx + cw * k + 2) for k in range(steps + 1))
                s.add(
                    f'<rect x="{n(tx + 2)}" y="{y - 17}" width="{n(cw - 2)}" height="22" rx="2" fill="{VIOLET}" opacity="0">'
                    f'<set attributeName="opacity" to="1" begin="{t:.2f}s" end="{start + dur + 0.25:.2f}s"/>'
                    f'<animate attributeName="x" values="{xs}" calcMode="discrete" begin="{start:.2f}s" dur="{dur + 0.06:.2f}s" fill="freeze"/></rect>'
                )
                t = start + dur + 0.45
            else:  # final prompt: blinking cursor
                s.add(
                    f'<g opacity="0"><rect x="{n(tx + 2)}" y="{y - 17}" width="{n(cw - 2)}" height="22" rx="2" fill="{VIOLET}" class="blink"/>'
                    f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></g>'
                )
        else:
            s.add(
                f'<g opacity="0">{s.runs(x0 + cw * 2, y, content, "jb4", size)}'
                f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></g>'
            )
            t += 0.08
        y += lh

    # monogram
    mx, my = 1040, 250
    s.add(
        f'<circle cx="{mx}" cy="{my}" r="96" stroke="#fff" stroke-opacity=".06" stroke-width="3"/>',
        f'<circle cx="{mx}" cy="{my}" r="96" stroke="url(#ring)" stroke-width="3" stroke-linecap="round" stroke-dasharray="220 383" class="spin"/>',
        f'<circle cx="{mx}" cy="{my}" r="112" stroke="#fff" stroke-opacity=".05" stroke-dasharray="2 8" class="spin" style="animation-duration:40s;animation-direction:reverse"/>',
        f'<circle cx="{mx}" cy="{my}" r="80" fill="#0B0F22"/>',
        s.text(mx, my + 22, FIRST[0] + LAST[0], "sg7", 62, "url(#mono)", anchor="middle", ls=-2),
        s.text(mx, 404, f"@{HANDLE}", "jb6", 17, TEXT, anchor="middle"),
        f'<circle cx="{mx - 86}" cy="436" r="4" fill="#34D399" class="pulse"/><circle cx="{mx - 86}" cy="436" r="4" fill="#34D399"/>',
        s.text(mx - 74, 440.5, "always learning", "jb4", 14, MUTED),
    )
    s.add("</g>")
    s.save("about.svg")


# --------------------------------------------------------------------------
# Toolkit
# --------------------------------------------------------------------------


def build_toolkit() -> None:
    W, TW, TH, GAP = 1200, 588, 136, 24
    tiles = TOOLKIT + [("Daily drivers", "#94A3B8", None)]
    rows = math.ceil(len(tiles) / 2)
    H = rows * TH + (rows - 1) * GAP
    s = Svg(W, H, "Toolkit — " + "; ".join(f"{c}: {', '.join(i)}" for c, _, i in TOOLKIT) + "; daily drivers: " + ", ".join(d for d, _ in DAILY_DRIVERS))
    card_defs(s)
    for idx, (cat, color, icons) in enumerate(tiles):
        x, y = (idx % 2) * (TW + GAP), (idx // 2) * (TH + GAP)
        s.defs.append(radial(f"t{idx}", color, 0.22))
        s.defs.append(f'<clipPath id="c{idx}"><rect x="{x}" y="{y}" width="{TW}" height="{TH}" rx="22"/></clipPath>')
        s.add(
            card(x, y, TW, TH, 22),
            f'<g clip-path="url(#c{idx})"><circle cx="{x + TW}" cy="{y}" r="220" fill="url(#t{idx})"/></g>',
            f'<rect x="{x + 28}" y="{y + 26}" width="10" height="10" rx="3" fill="{color}" transform="rotate(45 {x + 33} {y + 31})"/>',
            s.text(x + 50, y + 36, cat.upper(), "jb6", 13, TEXT, ls=3),
            s.text(x + TW - 28, y + 36, f"{len(icons or DAILY_DRIVERS):02d}", "jb4", 13, DIM, anchor="end", ls=1),
        )
        if icons:
            for k, key in enumerate(icons):
                s.add(
                    f'<g class="bob" style="animation-delay:-{(idx * 0.4 + k * 0.18):.2f}s">'
                    + s.icon(key, x + 28 + k * 62, y + 60, 50)
                    + "</g>"
                )
        else:
            cx = x + 28
            for k, (label, dot) in enumerate(DAILY_DRIVERS):
                w = measure(label, "in6", 16) + 44
                s.add(
                    f'<g class="bob" style="animation-delay:-{k * 0.18:.2f}s">'
                    f'<rect x="{n(cx)}" y="{y + 64}" width="{n(w)}" height="42" rx="12" fill="#fff" fill-opacity=".04" stroke="#fff" stroke-opacity=".1"/>'
                    f'<circle cx="{n(cx + 20)}" cy="{y + 85}" r="5" fill="{dot}"/>'
                    + s.text(cx + 32, y + 91, label, "in6", 16, TEXT)
                    + "</g>"
                )
                cx += w + 12
    s.save("toolkit.svg")


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------

GLYPHS = {
    "cap": '<path d="M32 14 60 26 32 38 4 26Z" fill="#fff"/><path d="M15 32v11c0 4.5 7.6 8 17 8s17-3.5 17-8V32l-17 7.5z" fill="#fff" fill-opacity=".85"/>'
    '<path d="M56 27.5V41" stroke="#fff" stroke-width="3" stroke-linecap="round"/>',
    "bag": '<path d="M16 24h32l3 28a4 4 0 0 1-4 4.4H17a4 4 0 0 1-4-4.4z" fill="#fff"/><path d="M24 28v-7a8 8 0 0 1 16 0v7" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'
    '<path d="M24 34v1M40 34v1" stroke="#000" stroke-opacity=".25" stroke-width="4" stroke-linecap="round"/>',
    "spark": '<path d="M28 10c1.8 11.5 7.5 17.2 19 19-11.5 1.8-17.2 7.5-19 19-1.8-11.5-7.5-17.2-19-19 11.5-1.8 17.2-7.5 19-19Z" fill="#fff"/>'
    '<path d="M49 8c.8 4.8 3.2 7.2 8 8-4.8.8-7.2 3.2-8 8-.8-4.8-3.2-7.2-8-8 4.8-.8 7.2-3.2 8-8Z" fill="#fff" fill-opacity=".8"/>',
}


def build_projects() -> None:
    W, CW, CH, GAP = 1200, 588, 340, 24
    rows = math.ceil(len(PROJECTS) / 2)
    H = rows * CH + (rows - 1) * GAP
    s = Svg(W, H, "Featured projects — " + "; ".join(f"{p['name']} ({STATUS[p['status']][0]}): {p['desc']}" for p in PROJECTS))
    card_defs(s)
    s.defs.append(linear("sheen", [(0, "#fff", 0), (0.5, "#fff", 0.07), (1, "#fff", 0)]))
    for i, p in enumerate(PROJECTS):
        x, y = (i % 2) * (CW + GAP), (i // 2) * (CH + GAP)
        a, b = p["accent"]
        ccx, ccy = x + CW / 2, y + CH / 2
        s.defs += [
            radial(f"pg{i}", a, 0.3),
            linear(f"pa{i}", [(0, a, 1), (1, b, 1)], 0, 0, 1, 1),
            linear(
                f"pb{i}", [(0, a, 0.9), (0.35, b, 0.05), (0.65, b, 0.05), (1, b, 0.8)], x, y, x + CW, y + CH, user=True,
                extra=f'<animateTransform attributeName="gradientTransform" type="rotate" from="0 {ccx} {ccy}" to="360 {ccx} {ccy}" dur="10s" begin="-{i * 2.5}s" repeatCount="indefinite"/>',
            ),
            f'<clipPath id="pc{i}"><rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="24"/></clipPath>',
        ]
        s.add(card(x, y, CW, CH, 24, stroke=f"url(#pb{i})"), f'<g clip-path="url(#pc{i})">')
        s.add(
            f'<circle cx="{x + CW - 40}" cy="{y + 20}" r="260" fill="url(#pg{i})"/>',
            s.text(x + CW - 24, y + CH - 26, f"{i + 1:02d}", "sg7", 150, "none", anchor="end", ls=-4,
                   attrs=' stroke="#fff" stroke-opacity=".07" stroke-width="1.5"'),
            f'<rect x="{x - 300}" y="{y - 60}" width="160" height="{CH + 120}" fill="url(#sheen)" transform="skewX(-18)">'
            f'<animate attributeName="x" values="{x - 300};{x + CW + 300}" dur="7s" begin="{1 + i * 1.3:.1f}s" repeatCount="indefinite"/></rect>',
            "</g>",
        )
        # icon tile
        ix, iy = x + 32, y + 32
        s.add(f'<rect x="{ix}" y="{iy}" width="64" height="64" rx="18" fill="url(#pa{i})"/>')
        if p["glyph"] == "letter":
            s.add(s.text(ix + 32, iy + 46, "අ", "si6", 38, "#fff", anchor="middle"))
        else:
            s.add(f'<g transform="translate({ix} {iy})">{GLYPHS[p["glyph"]]}</g>')
        label, color = STATUS[p["status"]]
        s.add(pill(s, x + CW - 32, y + 49, label.upper(), color, anchor="end", dot=p["status"] != "planning"))
        s.add(s.text(x + 32, y + 152, p["name"], "sg7", 36, INK, ls=-0.5))
        desc = wrap(p["desc"], "in4", 19, CW - 64)
        for k, line in enumerate(desc):
            s.add(s.text(x + 32, y + 190 + k * 28, line, "in4", 19, MUTED))
        s.add(s.runs(x + 32, y + 190 + len(desc) * 28 + 6, [("stack  ", DIM), (p["stack_label"], "#C4B5FD")], "jb4", 14))
        s.add(f'<rect x="{x + 32}" y="{y + 256}" width="{CW - 64}" height="1" fill="#fff" fill-opacity=".08"/>')
        for k, key in enumerate(p["stack"]):
            s.add(s.icon(key, x + 32 + k * 50, y + 274, 40))
    s.save("projects.svg")


# --------------------------------------------------------------------------
# Roadmap
# --------------------------------------------------------------------------


def build_roadmap() -> None:
    W, H = 1200, 440
    s = Svg(W, H, "Currently building — " + "; ".join(f"{t} ({STATUS[st][0]})" for t, st in ROADMAP))
    card_defs(s)
    done = sum(st == "done" for _, st in ROADMAP)
    s.defs += [
        f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="24"/></clipPath>',
        radial("g1", "#34D399", 0.16), radial("g2", "#FBBF24", 0.14),
        linear("bar", [(0, "#34D399", 1), (1, "#10B981", 1)]),
        linear("flow", [(0, "#34D399", 1), (1, "#FBBF24", 1)]),
        linear("sheen", [(0, "#fff", 0), (0.5, "#fff", 0.55), (1, "#fff", 0)]),
    ]
    s.css.append(
        ".dash{animation:dash 1.2s linear infinite}@keyframes dash{to{stroke-dashoffset:-24}}"
        ".halo{transform-box:fill-box;transform-origin:center;animation:halo 2.4s ease-out infinite}"
        "@keyframes halo{0%{transform:scale(1);opacity:.7}100%{transform:scale(2.1);opacity:0}}"
    )
    s.add(card(0, 0, W, H), '<g clip-path="url(#clip)">', f'<circle cx="240" cy="60" r="360" fill="url(#g1)"/>',
          f'<circle cx="720" cy="380" r="320" fill="url(#g2)"/>', "</g>")
    s.add(s.text(44, 62, "ROADMAP", "jb6", 13, TEXT, ls=4))
    progress = f"{done} / {len(ROADMAP)} SHIPPED"
    bw, bx = 240, W - 44 - 240
    fill_w = bw * done / len(ROADMAP)
    s.add(
        s.text(bx - 20, 62, progress, "jb4", 13, MUTED, anchor="end", ls=2),
        f'<rect x="{bx}" y="52" width="{bw}" height="10" rx="5" fill="#fff" fill-opacity=".07"/>',
        f'<clipPath id="barclip"><rect x="{bx}" y="52" width="{n(fill_w)}" height="10" rx="5"/></clipPath>',
        f'<rect x="{bx}" y="52" width="{n(fill_w)}" height="10" rx="5" fill="url(#bar)"/>',
        f'<g clip-path="url(#barclip)"><rect x="{bx - 60}" y="52" width="60" height="10" fill="url(#sheen)">'
        f'<animate attributeName="x" values="{bx - 60};{n(bx + fill_w)}" dur="2.2s" repeatCount="indefinite"/></rect></g>',
        f'<rect x="44" y="92" width="{W - 88}" height="1" fill="#fff" fill-opacity=".07"/>',
    )

    ly = 206
    xs = [120 + i * 240 for i in range(len(ROADMAP))]
    for i in range(len(ROADMAP) - 1):
        a, b = ROADMAP[i][1], ROADMAP[i + 1][1]
        x1, x2 = xs[i] + 30, xs[i + 1] - 30
        if a == "done" and b == "done":
            s.add(f'<rect x="{x1}" y="{ly - 1.5}" width="{x2 - x1}" height="3" rx="1.5" fill="#34D399"/>')
        elif a == "done":
            s.defs.append(linear(f"seg{i}", [(0, "#34D399", 1), (1, "#FBBF24", 1)], x1, 0, x2, 0, user=True))
            s.add(f'<path d="M{x1} {ly}H{x2}" stroke="url(#seg{i})" stroke-width="3" stroke-dasharray="12 12" stroke-linecap="round" class="dash"/>')
        else:
            s.add(f'<path d="M{x1} {ly}H{x2}" stroke="{FAINT}" stroke-width="2" stroke-dasharray="4 8" stroke-linecap="round"/>')

    for i, ((title, st), x) in enumerate(zip(ROADMAP, xs)):
        label, color = STATUS[st]
        s.add(s.text(x, 150, f"STEP {i + 1:02d}", "jb4", 12, DIM, anchor="middle", ls=3))
        if st == "done":
            s.add(
                f'<circle cx="{x}" cy="{ly}" r="24" fill="#052E1F" stroke="{color}" stroke-width="2"/>',
                f'<path d="M{x - 9} {ly}l6 6 12-12" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
            )
        elif st == "progress":
            s.add(
                f'<circle cx="{x}" cy="{ly}" r="24" fill="{color}" fill-opacity=".25" class="halo"/>',
                f'<circle cx="{x}" cy="{ly}" r="24" fill="#2B1D05" stroke="{color}" stroke-width="2"/>',
                f'<circle cx="{x}" cy="{ly}" r="8" fill="{color}"/>',
            )
        else:
            s.add(
                f'<circle cx="{x}" cy="{ly}" r="24" fill="#0B1022" stroke="#475569" stroke-width="2" stroke-dasharray="4 5"/>',
                f'<circle cx="{x}" cy="{ly}" r="4" fill="#475569"/>',
            )
        lines = wrap_balanced(title, "sg5", 19, 206)
        for k, line in enumerate(lines):
            s.add(s.text(x, 274 + k * 27, line, "sg5", 19, TEXT if st != "planning" else MUTED, anchor="middle"))
        s.add(pill(s, x, 274 + len(lines) * 27 - 4, label.upper(), color, size=11, h=26, dot=False, anchor="middle"))
    s.save("roadmap.svg")


# --------------------------------------------------------------------------
# Connect buttons
# --------------------------------------------------------------------------


def build_connect() -> None:
    W, H = 360, 96
    for key, label, handle, color in LINKS:
        s = Svg(W, H, f"{label} — {handle}")
        s.defs += [
            linear("bg", [(0, "#0D1326", 1), (1, "#070A14", 1)], 0, 0, 0.4, 1),
            linear(
                "edge", [(0, color, 0.9), (0.4, color, 0.08), (0.6, color, 0.08), (1, color, 0.7)], 0, 0, W, H, user=True,
                extra=f'<animateTransform attributeName="gradientTransform" type="rotate" from="0 {W / 2} {H / 2}" to="360 {W / 2} {H / 2}" dur="8s" repeatCount="indefinite"/>',
            ),
            radial("glow", color, 0.22),
        ]
        s.add(
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="{(H - 1.5) / 2}" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.5"/>',
            f'<circle cx="48" cy="48" r="70" fill="url(#glow)"/>',
            s.icon(key, 18, 18, 60),
            s.text(96, 46, label, "sg7", 25, INK, ls=-0.3),
            s.text(96, 72, handle, "jb4", 14, MUTED),
            s.text(W - 34, 57, "↗", "sg5", 24, color, anchor="middle"),
        )
        s.save(f"connect/{key}.svg")


# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------


def build_footer() -> None:
    W, H = 1200, 300
    s = Svg(W, H, f"Thanks for stopping by — crafted by {FIRST} {LAST}")
    rnd = random.Random(2026)
    card_defs(s)
    s.defs += [
        f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="28"/></clipPath>',
        linear("w1", [(0, "#8B5CF6", 0.55), (0.5, "#3B82F6", 0.45), (1, "#22D3EE", 0.55)]),
        linear("w2", [(0, "#EC4899", 0.4), (1, "#8B5CF6", 0.35)]),
        linear("w3", [(0, "#22D3EE", 0.25), (1, "#EC4899", 0.3)]),
        linear("thanks", [(0, PINK, 1), (0.5, VIOLET, 1), (1, CYAN, 1)]),
        radial("g", "#8B5CF6", 0.3),
    ]

    def wave(y0, amp, period):
        d = f"M0 {y0}Q{period / 4} {y0 - amp} {period / 2} {y0}"
        x = period / 2
        while x < W + period:
            x += period / 2
            d += f"T{x} {y0}"
        return d + f"V{H}H0Z"

    layers = [(236, 14, 600, "w3", 26), (250, 18, 400, "w2", 18), (264, 12, 300, "w1", 11)]
    for i, (_, _, period, _, dur) in enumerate(layers):
        s.css.append(f".wv{i}{{animation:wv{i} {dur}s linear infinite}}@keyframes wv{i}{{to{{transform:translateX(-{period}px)}}}}")
    s.add('<g clip-path="url(#clip)">', f'<rect width="{W}" height="{H}" fill="#05070F"/>', f'<ellipse cx="600" cy="300" rx="560" ry="240" fill="url(#g)"/>')
    s.add(stars(rnd, 50, W, 200))
    for i, (y0, amp, period, grad, _) in enumerate(layers):
        s.add(f'<path d="{wave(y0, amp, period)}" fill="url(#{grad})" class="wv{i}"/>')
    s.add(
        s.text(W / 2, 84, "ස්තූතියි", "si6", 28, "url(#thanks)", anchor="middle"),
        s.text(W / 2, 146, "Thanks for stopping by.", "sg7", 54, INK, anchor="middle", ls=-1.5),
        s.text(W / 2, 188, f"Crafted with precision by {FIRST} {LAST}  ·  Sri Lanka", "in4", 18, MUTED, anchor="middle"),
        "</g>",
        f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="28" stroke="url(#edge)" stroke-width="1.5"/>',
    )
    s.save("footer.svg")


if __name__ == "__main__":
    print("Building assets/")
    build_hero()
    build_headers()
    build_about()
    build_toolkit()
    build_projects()
    build_roadmap()
    build_connect()
    build_footer()
