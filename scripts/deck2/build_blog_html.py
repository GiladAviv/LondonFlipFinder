# -*- coding: utf-8 -*-
"""Convert blog_post.md into a self-contained docs/index.html for GitHub Pages.

Markdown tables -> the pre-rendered table PNGs in figures/blog/ (same images used for the
Medium version, so both publishing paths show identical content). *[FIGURE: ...]* markers ->
the named analysis figure. Everything after the "HOW TO PUBLISH ON MEDIUM" divider is dropped
-- that section is authoring notes, not part of the article.
"""
import html
import re
from pathlib import Path

ROOT = Path("/home/dsi/giladaviv/london_flip_finder")
SRC = ROOT / "blog_post.md"
OUT = ROOT / "docs" / "index.html"

text = SRC.read_text()
text = text.split("\n---\n---\n\n# HOW TO PUBLISH")[0]
# The placeholder repo link on the last line is superseded by the real one in the footer.
text = text.replace(
    "*Code and the full notebook: [github.com/…](https://github.com) · All figures are "
    "original,\ngenerated from the analysis described.*",
    ""
).rstrip()

lines = text.splitlines()
table_n = 0
out = []
i = 0


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r'<a href="\2">\1</a>', s)
    return s


FIGCAP = {
    "c48_leaderboard.png": "Validation leaderboard, all 14 models — identical evaluation rows.",
    "c28_within_borough.png": "Raw crime–price correlation (left) versus the same relationship "
                              "with borough averages subtracted (right).",
    "c60_ablation.png": "Cost, in validation MdAPE, of removing each feature group from the "
                        "shipped recipe.",
    "c73_flip_margins.png": "Left: distribution of margins below the conformal floor. Right: "
                            "actual price against prediction, with the 90%-target floor line.",
}

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    if stripped == "" :
        i += 1
        continue

    if stripped == "---":
        out.append('<hr class="rule">')
        i += 1
        continue

    m = re.match(r"^#\s+(.+)$", stripped)
    if m:
        out.append(f"<h1>{inline(m.group(1))}</h1>")
        i += 1
        continue

    m = re.match(r"^###\s+(.+)$", stripped)
    if m:
        out.append(f'<p class="dek">{inline(m.group(1))}</p>')
        i += 1
        continue

    m = re.match(r"^##\s+(.+)$", stripped)
    if m:
        out.append(f"<h2>{inline(m.group(1))}</h2>")
        i += 1
        continue

    m = re.match(r"^\*\[FIGURE:\s*(\S+)\s*(?:—|-)?\s*(.*?)\]\*$", stripped)
    if m:
        fname = m.group(1)
        cap = FIGCAP.get(fname, inline(m.group(2)))
        out.append(
            f'<figure><img src="assets/img/{fname}" alt="{html.escape(cap)}" loading="lazy">'
            f"<figcaption>{cap}</figcaption></figure>"
        )
        i += 1
        continue

    if stripped.startswith("```"):
        code_lines = []
        i += 1
        while i < len(lines) and not lines[i].strip().startswith("```"):
            code_lines.append(lines[i])
            i += 1
        i += 1  # skip closing fence
        code = html.escape("\n".join(code_lines))
        out.append(f'<pre><code class="lang-python">{code}</code></pre>')
        continue

    if stripped.startswith("|"):
        table_n += 1
        j = i
        while j < len(lines) and lines[j].strip().startswith("|"):
            j += 1
        i = j
        out.append(
            f'<figure class="tbl"><img src="assets/img/table{table_n}.png" '
            f'alt="Table {table_n}" loading="lazy"></figure>'
        )
        continue

    if stripped.startswith(">"):
        quote_lines = []
        j = i
        while j < len(lines) and lines[j].strip().startswith(">"):
            quote_lines.append(lines[j].strip().lstrip(">").strip())
            j += 1
        i = j
        out.append(f"<blockquote><p>{inline(' '.join(quote_lines))}</p></blockquote>")
        continue

    # plain paragraph, possibly wrapped across lines
    para_lines = [stripped]
    j = i + 1
    while j < len(lines) and lines[j].strip() and not re.match(
        r"^(#{1,3}\s|---$|\||\*\[FIGURE:|```|>)", lines[j].strip()
    ):
        para_lines.append(lines[j].strip())
        j += 1
    i = j
    out.append(f"<p>{inline(' '.join(para_lines))}</p>")

body = "\n".join(out)
n_p = body.count("<p>")
print(f"tables replaced: {table_n}  |  paragraphs: {n_p}")

CSS = """
:root{
  --ground:#fafbfc; --surface:#ffffff; --ink:#16202b; --muted:#5a6675;
  --accent:#2a78d6; --deep:#104281; --rule:#dee4ea; --panel:#f2f6fb;
  --band-bg:#104281; --band-fg:#ffffff;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --ground:#0d1218; --surface:#151d26; --ink:#e4eaf1; --muted:#93a1b1;
  --accent:#5c9ff2; --deep:#9cc4f5; --rule:#253140; --panel:#1a232e;
  --band-bg:#1d3a5f; --band-fg:#eaf1f8;
}}
:root[data-theme="dark"]{
  --ground:#0d1218; --surface:#151d26; --ink:#e4eaf1; --muted:#93a1b1;
  --accent:#5c9ff2; --deep:#9cc4f5; --rule:#253140; --panel:#1a232e;
  --band-bg:#1d3a5f; --band-fg:#eaf1f8;
}
*{box-sizing:border-box}
html{background:var(--ground)}
body{background:var(--ground); color:var(--ink); margin:0;
  font-family:"Source Sans 3",ui-sans-serif,system-ui,-apple-system,sans-serif;
  font-size:19px; line-height:1.68;}
.wrap{max-width:42rem; margin:0 auto; padding:3.2rem 1.25rem 5rem;}
.kicker{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.78rem;
  letter-spacing:.12em; text-transform:uppercase; color:var(--accent); margin:0 0 1rem;}
h1{font-family:"Source Serif 4",Georgia,serif; font-weight:600; font-size:2.5rem;
  line-height:1.12; letter-spacing:-.02em; color:var(--deep); margin:0 0 .9rem;
  text-wrap:balance;}
.dek{font-family:"Source Serif 4",Georgia,serif; font-style:italic; font-weight:400;
  font-size:1.28rem; line-height:1.5; color:var(--muted); margin:0 0 1.6rem;
  text-wrap:balance;}
.byline{display:flex; align-items:center; gap:.6rem; margin:0 0 2.2rem; color:var(--muted);
  font-size:.92rem;}
.byline .dot{width:4px; height:4px; border-radius:50%; background:var(--muted);}
h2{font-family:"Source Serif 4",Georgia,serif; font-weight:600; font-size:1.55rem;
  line-height:1.28; letter-spacing:-.01em; color:var(--deep); margin:2.6rem 0 1.1rem;
  text-wrap:balance;}
p{margin:0 0 1.35rem;}
strong{color:var(--ink); font-weight:700;}
:root:not([data-theme="light"]) strong, :root[data-theme="dark"] strong{color:var(--accent)}
em{font-style:italic;}
code{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.85em;
  background:var(--panel); border:1px solid var(--rule); border-radius:4px;
  padding:.08em .35em;}
a{color:var(--accent); text-decoration-color:var(--rule); text-underline-offset:.15em;}
hr.rule{border:none; border-top:1px solid var(--rule); margin:2.6rem 0;}
pre{margin:0 0 1.6rem; padding:1.1rem 1.2rem; background:var(--panel);
  border:1px solid var(--rule); border-left:3px solid var(--accent); border-radius:8px;
  overflow-x:auto; -webkit-overflow-scrolling:touch;}
pre code{background:none; border:none; padding:0; font-size:.86rem; line-height:1.7;
  color:var(--ink); white-space:pre;}
blockquote{margin:0 0 1.6rem; padding:.2rem 0 .2rem 1.2rem; border-left:3px solid var(--accent);
  color:var(--muted); font-size:1.02rem;}
blockquote p{margin:0;}
figure{margin:1.8rem 0 1.9rem;}
figure img{display:block; width:100%; height:auto; border-radius:8px; border:1px solid var(--rule);
  background:#fff;}
figure.tbl img{border-radius:8px;}
figcaption{margin-top:.6rem; font-size:.86rem; color:var(--muted); line-height:1.5;}
.readtime{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.76rem;
  color:var(--muted); letter-spacing:.03em;}
footer{margin-top:3rem; padding-top:1.6rem; border-top:1px solid var(--rule);
  color:var(--muted); font-size:.9rem;}
footer a{color:var(--accent);}
@media (max-width:34rem){ body{font-size:17.5px} h1{font-size:2rem} .dek{font-size:1.12rem}
  h2{font-size:1.32rem} .wrap{padding:2.2rem 1.1rem 3.5rem} }
"""

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your gradient boosting isn't broken — your target is</title>
<meta name="description" content="A linear baseline beat XGBoost and CatBoost on 60,000 London property sales. The fix wasn't a better model — it was the target.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Source+Sans+3:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<p class="kicker">London Flip Finder &middot; Applied Data Science, Bar-Ilan University</p>
{body}
<footer>
<p>Code and the full notebook: <a href="https://github.com/GiladAviv/LondonFlipFinder">github.com/GiladAviv/LondonFlipFinder</a>.
All figures are original, generated from the analysis described. Data: Land Registry price
history (Open Government Licence), Metropolitan Police crime by LSOA (OGL), Bank of England
base rate (OGL), TfL station geodata (OGL), and a Kaggle-hosted price-history export &mdash;
see the repository README for the full source table and licensing notes.</p>
</footer>
</div>
</body>
</html>
"""

OUT.write_text(html_doc)
print(f"wrote {OUT}  ({len(html_doc)/1024:.0f} KB)")
