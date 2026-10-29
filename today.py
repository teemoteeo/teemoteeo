"""Render dark_mode.svg and light_mode.svg: a neofetch-style card with live GitHub stats.

Run daily by .github/workflows/build.yml. Locally: GH_TOKEN=$(gh auth token) uv run --with pillow today.py
"""
import json
import os
import urllib.request
from io import BytesIO
from datetime import date, datetime, timezone
from html import escape

from PIL import Image, ImageEnhance

USER = "teemoteeo"
BIRTH = date(2003, 1, 9)
WIDTH = 57  # characters in the info column

AVATAR = f"https://github.com/{USER}.png?size=460"
CROP = (150, 40, 450, 430)  # chair, jacket, face of the current avatar; change it with the picture
COLS, ROWS = 64, 40
RAMP = ":-=+*#%@"  # brighter pixel, denser char

THEMES = {
    "dark_mode.svg": dict(bg="#0e0d10", fg="#f0ecdd", key="#c8f06e", value="#f0ecdd", dots="#4a4852", lift=0.6),
    "light_mode.svg": dict(bg="#f6f5f0", fg="#1a191e", key="#4f7a12", value="#1a191e", dots="#b5b3ad", lift=1),
}


def art():
    with urllib.request.urlopen(AVATAR) as r:
        im = Image.open(BytesIO(r.read())).convert("RGB").crop(CROP)
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.4)).enhance(1.2)
    im = im.resize((COLS, ROWS), Image.LANCZOS)
    return [[im.getpixel((x, y)) for x in range(COLS)] for y in range(ROWS)]


def art_svg(pixels, lift):
    out = []
    for y, row in enumerate(pixels):
        spans = []
        for r, g, b in row:
            c = RAMP[min(len(RAMP) - 1, int((0.299 * r + 0.587 * g + 0.114 * b) / 256 * len(RAMP)))]
            # lift darks so the jacket and chair still read on the dark background
            r, g, b = (int(255 * (v / 255) ** lift) for v in (r, g, b))
            spans.append(f'<tspan fill="#{r:02x}{g:02x}{b:02x}">{c}</tspan>')
        out.append(f'<tspan x="20" y="{24 + y * 12.5}">{"".join(spans)}</tspan>')
    return "\n".join(out)


def uptime(today):
    y, m, d = today.year - BIRTH.year, today.month - BIRTH.month, today.day - BIRTH.day
    if d < 0:
        m -= 1
        prev = date(today.year, today.month, 1).toordinal() - 1
        d += date.fromordinal(prev).day
    if m < 0:
        y -= 1
        m += 12
    return f"{y} years, {m} months, {d} days"


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]


def stats():
    u = gql(f"""{{ user(login: "{USER}") {{
        createdAt
        followers {{ totalCount }}
        repositories(ownerAffiliations: OWNER, first: 100) {{ totalCount nodes {{ stargazerCount }} }}
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST]) {{ totalCount }}
    }} }}""")
    first = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).year
    years = range(first, datetime.now(timezone.utc).year + 1)
    # GitHub caps a contributionsCollection at one year, so ask for each year in one query
    c = gql(f'{{ user(login: "{USER}") {{ '
            + " ".join(f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
                       f"{{ totalCommitContributions restrictedContributionsCount }}" for y in years)
            + " } }")
    return {
        "repos": u["repositories"]["totalCount"],
        "contrib": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "commits": sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in c.values()),
    }


def rows(s, today):
    return [
        ("head", "timoteo@costantini-scala"),
        ("OS", "macOS, Linux"),
        ("Uptime", uptime(today)),
        ("Host", "42 Firenze, Common Core"),
        ("Kernel", "Freelance Software Developer"),
        ("IDE", "Neovim (Kanagawa Dragon)"),
        ("Shell", "zsh, cmux"),
        None,
        ("Languages.Programming", "C, Python, JavaScript, Swift"),
        ("Languages.Computer", "HTML, CSS, SQL, JSON"),
        ("Languages.Real", "Italian, English, French"),
        None,
        ("Hobbies.Software", "Local LLMs, MLX, RAG"),
        ("Hobbies.Other", "Basketball, chess, hip-hop"),
        ("Past.Fashion", "Model for Valentino, Zegna, Prada"),
        ("Past.Food", "Fine dining, Armani Paris"),
        ("head", "Contact"),
        ("Email", "timoteocostantiniscala@gmail.com"),
        ("LinkedIn", "timoteo-costantini-scala"),
        ("Instagram", "teemoteeo"),
        ("Web", "teemoteeo.github.io/timoteo-site"),
        ("head", "GitHub Stats"),
        ("Repos", f"{s['repos']} {{Contributed: {s['contrib']}}} | Stars: {s['stars']}"),
        ("Commits", f"{s['commits']:,} | Followers: {s['followers']}"),
    ]


def line(row):
    if row is None:
        return '<tspan class="cc">. </tspan>'
    k, v = row
    if k == "head":
        return f'<tspan class="value">{escape(v)}</tspan> <tspan class="cc">{"-" * (WIDTH - len(v) - 1)}</tspan>'
    keys = '<tspan class="cc">.</tspan>'.join(f'<tspan class="key">{p}</tspan>' for p in k.split("."))
    dots = "." * max(1, WIDTH - 2 - len(k) - 3 - len(v))
    return f'<tspan class="cc">. </tspan>{keys}:<tspan class="cc"> {dots} </tspan><tspan class="value">{escape(v)}</tspan>'


def svg(t, info, pixels):
    text = "\n".join(f'<tspan x="430" y="{34 + i * 20}">{line(r)}</tspan>' for i, r in enumerate(info))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="985" height="530" font-size="16" font-family="'JetBrains Mono',SFMono-Regular,Menlo,Consolas,monospace">
<style>
.key {{fill: {t['key']};}} .value {{fill: {t['value']};}} .cc {{fill: {t['dots']};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985" height="530" rx="15" fill="{t['bg']}"/>
<text font-size="10" font-weight="bold">
{art_svg(pixels, t['lift'])}
</text>
<text fill="{t['fg']}">
{text}
</text>
</svg>
"""


if __name__ == "__main__":
    assert uptime(date(2026, 10, 29)) == "23 years, 9 months, 20 days"
    assert uptime(date(2027, 1, 8)) == "23 years, 11 months, 30 days"
    info, pixels = rows(stats(), date.today()), art()
    for name, theme in THEMES.items():
        with open(name, "w") as f:
            f.write(svg(theme, info, pixels))
