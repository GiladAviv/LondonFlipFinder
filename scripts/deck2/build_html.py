# -*- coding: utf-8 -*-
"""Render deck_content.py as a single self-contained HTML reading version."""
from __future__ import annotations
import base64, html, io, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_content import APPENDIX, MAIN  # noqa: E402

OUT = Path("/tmp/claude-30353/-home-dsi-giladaviv-london-flip-finder/"
           "d7cb2e50-ef4d-49c1-b52b-42e1ab3a2af6/scratchpad/london_flip_finder.html")

_cache: dict[str, str] = {}


def data_uri(rel: str) -> str:
    if rel in _cache:
        return _cache[rel]
    im = Image.open(ROOT / rel).convert("RGB")
    w, h = im.size
    k = min(1.0, 1600 / w)
    im = im.resize((round(w * k), round(h * k)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=90, method=6)
    uri = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    _cache[rel] = uri
    return uri


def dims(rel: str) -> tuple[int, int]:
    w, h = Image.open(ROOT / rel).size
    k = min(1.0, 1600 / w)
    return round(w * k), round(h * k)


def esc(t: str) -> str:
    return html.escape(t, quote=False)


def emph(t: str) -> str:
    """**x** -> highlighted value."""
    out, parts = [], re.split(r"\*\*(.+?)\*\*", t)
    for i, part in enumerate(parts):
        out.append(f'<b class="v">{esc(part)}</b>' if i % 2 else esc(part))
    return "".join(out)


PHASES = [("Setup", "§1–3", "What are we working with?"),
          ("Data", "§4–7", "Four sources into one table"),
          ("Exploration", "§8", "What moves price?"),
          ("Features", "§9–10", "What may the model see?"),
          ("Models", "§11–13", "What wins, against what loss?"),
          ("Decision", "§14–15", "How good is it really?"),
          ("Assurance", "§16–18", "What is asserted, what is wrong?")]


def render(spec, n):
    lay = spec["layout"]
    p = []
    if lay == "title":
        p.append(f'<p class="sub">{esc(spec["subtitle"])}</p>')
        if spec.get("authors"):
            p.append(f'<p class="who">{esc(spec["authors"])}</p>')
        if spec.get("course"):
            p.append(f'<p class="course">{esc(spec["course"])}</p>')
        p.append('<ul class="meta">' + "".join(
            f"<li>{esc(x.strip())}</li>" for x in spec["meta"].split("·")) + "</ul>")
    if lay == "diagram":
        p.append('<ol class="phases">' + "".join(
            f'<li><span class="pn">{i}</span><span class="ph">{esc(a)}</span>'
            f'<span class="ps">{esc(b)}</span><span class="pq">{esc(c)}</span></li>'
            for i, (a, b, c) in enumerate(PHASES, 1)) + "</ol>")
        p.append('<p class="rule-line">One rule throughout: use only what a buyer '
                 "knew on the transaction date.</p>")
    if lay == "joins":
        rows = "".join(
            f'<li><span class="js">{esc(a)}</span><code>{esc(b)}</code>'
            + ('<span class="lag">lagged</span>' if c else "") + "</li>"
            for a, b, c in spec["joins"])
        p.append('<div class="jg"><p class="spine">Price history'
                 '<span>418,201 sales &middot; the spine</span></p>'
                 f'<ul class="joinlist">{rows}</ul>'
                 '<p class="spine out">Master table<span>59,946 rows &times; 37 columns'
                 "</span></p></div>")
    if spec.get("figure"):
        w, h = dims(spec["figure"])
        p.append(f'<figure><img src="{data_uri(spec["figure"])}" width="{w}" height="{h}" '
                 f'alt="{esc(spec["title"])}" loading="lazy"></figure>')
    if spec.get("code"):
        p.append('<pre><code>' + "\n".join(emph(c) for c in spec["code"]) + "</code></pre>")
    if spec.get("table"):
        t = spec["table"]
        head = "".join(f"<th>{esc(h)}</th>" for h in t["headers"])
        def cell(c):
            cls = ' class="mark"' if "\u2190" in c else ""
            return "<td" + cls + ">" + esc(c) + "</td>"
        body = "".join("<tr>" + "".join(cell(c) for c in r) + "</tr>" for r in t["rows"])
        p.append(f'<div class="tw"><table><thead><tr>{head}</tr></thead>'
                 f"<tbody>{body}</tbody></table></div>")
    if spec.get("bullets"):
        p.append("<ul>" + "".join(f"<li>{emph(b)}</li>" for b in spec["bullets"]) + "</ul>")
    p.append(f'<details><summary>Speaker notes</summary><p>{esc(spec["notes"])}</p></details>')
    kick = spec.get("kicker", "Title")
    return (f'<section id="s{n}"><p class="eyebrow"><span>{esc(kick)}</span>'
            f'<span class="num">{n}</span></p>'
            f'<h2>{esc(spec["title"])}</h2>{"".join(p)}</section>')


specs = MAIN + APPENDIX
body = []
toc = []
for n, spec in enumerate(specs, 1):
    if n == len(MAIN) + 1:
        body.append('<div class="divider" id="appendix"><span>Appendix · backup slides'
                    "</span></div>")
        toc.append('<li class="tsplit">Appendix</li>')
    body.append(render(spec, n))
    label = spec["title"] if spec["layout"] != "title" else "London Flip Finder"
    toc.append(f'<li><a href="#s{n}"><span class="tn">{n}</span>{esc(label)}</a></li>')

CSS = """
:root{
  --ground:#fafbfc; --surface:#ffffff; --ink:#16202b; --muted:#5a6675;
  --accent:#2a78d6; --deep:#104281; --rule:#dee4ea; --panel:#f2f6fb;
  --warm:#c2521f; --shadow:0 1px 2px rgba(16,66,129,.06);
  --band-bg:#104281; --band-fg:#ffffff;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --ground:#0d1218; --surface:#151d26; --ink:#e4eaf1; --muted:#93a1b1;
  --accent:#5c9ff2; --deep:#9cc4f5; --rule:#253140; --panel:#1a232e;
  --warm:#f08a5d; --shadow:none; --band-bg:#1d3a5f; --band-fg:#eaf1f8;
}}
:root[data-theme="dark"]{
  --ground:#0d1218; --surface:#151d26; --ink:#e4eaf1; --muted:#93a1b1;
  --accent:#5c9ff2; --deep:#9cc4f5; --rule:#253140; --panel:#1a232e;
  --warm:#f08a5d; --shadow:none; --band-bg:#1d3a5f; --band-fg:#eaf1f8;
}
*{box-sizing:border-box}
body{background:var(--ground); color:var(--ink);
  font-family:"Source Sans 3",ui-sans-serif,system-ui,-apple-system,sans-serif;
  font-size:17px; line-height:1.55; -webkit-text-size-adjust:100%;}
.wrap{max-width:38rem; margin:0 auto; padding:0 1.15rem 5rem;}

header.top{position:sticky; top:0; z-index:20; background:var(--ground);
  border-bottom:1px solid var(--rule); margin:0 -1.15rem; padding:.5rem 1.15rem .45rem;}
.bar{display:flex; align-items:center; gap:.6rem;}
.bar b{font-family:"Source Serif 4",Georgia,serif; font-size:.95rem; color:var(--deep);
  font-weight:600; letter-spacing:-.01em; white-space:nowrap;}
.bar .spacer{flex:1}
.bar button{font:inherit; font-size:.78rem; color:var(--muted); background:var(--panel);
  border:1px solid var(--rule); border-radius:99px; padding:.2rem .68rem; cursor:pointer;}
.bar button[aria-expanded="true"]{color:var(--surface); background:var(--accent);
  border-color:var(--accent);}
.bar button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);
  outline-offset:2px;}
#prog{height:2px; background:var(--accent); width:0; margin:.45rem -1.15rem -.45rem;
  transition:width .12s linear;}

.hero{padding:2.4rem 0 1.6rem; border-bottom:1px solid var(--rule);}
.hero h1{font-family:"Source Serif 4",Georgia,serif; font-weight:600; font-size:2.15rem;
  line-height:1.1; letter-spacing:-.02em; color:var(--deep); margin:0 0 .7rem;
  text-wrap:balance;}
.hero p{color:var(--muted); margin:0 0 1.1rem; font-size:1.02rem;}
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(7.2rem,1fr)); gap:.5rem;
  list-style:none; padding:0; margin:0;}
.stats li{background:var(--surface); border:1px solid var(--rule); border-radius:7px;
  padding:.55rem .7rem; font-family:"JetBrains Mono",ui-monospace,monospace;
  font-size:.74rem; line-height:1.35; color:var(--muted);}

.toc{margin:1.4rem 0 0;}
.toc>summary{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.74rem;
  letter-spacing:.09em; text-transform:uppercase; color:var(--muted); cursor:pointer;
  padding:.55rem 0; list-style:none;}
.toc>summary::-webkit-details-marker{display:none}
.toc>summary::before{content:"▸ "; color:var(--accent)}
.toc[open]>summary::before{content:"▾ "}
.toc ol{list-style:none; margin:.3rem 0 0; padding:0;
  border-left:2px solid var(--rule);}
.toc li.tsplit{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.68rem;
  letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  padding:.7rem 0 .3rem .85rem;}
.toc a{display:flex; gap:.6rem; text-decoration:none; color:var(--ink);
  padding:.3rem 0 .3rem .85rem; font-size:.92rem; line-height:1.35;}
.toc a:hover{color:var(--accent)}
.tn{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.72rem; color:var(--muted);
  min-width:1.5rem; padding-top:.16rem; font-variant-numeric:tabular-nums;}

section{padding:2.1rem 0 1.7rem; border-bottom:1px solid var(--rule);}
.eyebrow{display:flex; align-items:baseline; gap:.7rem; margin:0 0 .55rem;
  font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.7rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--accent);}
.eyebrow .num{margin-left:auto; color:var(--muted); font-variant-numeric:tabular-nums;}
section h2{font-family:"Source Serif 4",Georgia,serif; font-weight:600; font-size:1.42rem;
  line-height:1.24; letter-spacing:-.012em; color:var(--deep); margin:0 0 1rem;
  text-wrap:balance;}
section ul{margin:0; padding:0; list-style:none;
  display:flex; flex-direction:column; gap:.62rem;}
section ul li{position:relative; padding-left:1.05rem;}
section ul li::before{content:""; position:absolute; left:0; top:.62em; width:.42rem;
  height:1px; background:var(--accent);}
b.v{color:var(--accent); font-weight:600;
  font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.93em;}

figure{margin:0 0 1.05rem; background:#fff; border:1px solid var(--rule); border-radius:8px;
  padding:.5rem; box-shadow:var(--shadow);}
figure img{display:block; width:100%; height:auto; border-radius:3px;}

.tw{overflow-x:auto; margin:0 0 1.05rem; border:1px solid var(--rule); border-radius:8px;
  background:var(--surface); -webkit-overflow-scrolling:touch;}
table{border-collapse:collapse; width:100%; font-size:.84rem;
  font-variant-numeric:tabular-nums;}
th{background:var(--band-bg); color:var(--band-fg); font-weight:600; text-align:right; padding:.5rem .6rem;
  white-space:nowrap; font-size:.78rem;}
th:first-child{text-align:left}
td{padding:.46rem .6rem; text-align:right; border-top:1px solid var(--rule);
  white-space:nowrap; font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.79rem;}
td:first-child{text-align:left; font-family:"Source Sans 3",sans-serif; font-size:.86rem;}
td.mark{color:var(--accent); font-weight:600}
tbody tr:nth-child(odd){background:var(--panel)}

pre{margin:0 0 1.05rem; padding:.85rem .9rem; background:var(--panel);
  border:1px solid var(--rule); border-left:3px solid var(--accent); border-radius:7px;
  overflow-x:auto; -webkit-overflow-scrolling:touch;}
code{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.79rem; line-height:1.7;
  color:var(--ink); white-space:pre;}

section details{margin-top:1.05rem; border-top:1px dashed var(--rule);
  padding-top:.5rem;}
section details summary{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.7rem;
  letter-spacing:.09em; text-transform:uppercase; color:var(--muted); cursor:pointer;
  list-style:none; padding:.2rem 0;}
section details summary::-webkit-details-marker{display:none}
section details summary::before{content:"+ "; color:var(--accent); font-weight:600}
section details[open] summary::before{content:"– "}
section details p{margin:.5rem 0 0; color:var(--muted); font-size:.92rem; line-height:1.6;}

.phases{list-style:none; margin:0 0 1.1rem; padding:0; display:flex; flex-direction:column;
  gap:.42rem; counter-reset:none;}
.phases li{display:grid; grid-template-columns:1.6rem 1fr; gap:.1rem .7rem;
  background:var(--surface); border:1px solid var(--rule); border-radius:7px;
  padding:.55rem .7rem; align-items:baseline;}
.pn{grid-row:1/3; font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.78rem;
  color:var(--accent); font-weight:600;}
.ph{font-weight:600; font-size:.98rem;}
.ps{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.7rem; color:var(--muted);
  margin-left:.45rem;}
.ph,.ps{display:inline}
.pq{grid-column:2; color:var(--muted); font-size:.87rem;}
.rule-line{background:var(--band-bg); color:var(--band-fg); border-radius:7px;
  padding:.65rem .8rem; margin:0 0 1.05rem; font-size:.93rem; font-weight:600;}

.hero .note{font-size:.88rem; color:var(--muted); font-style:italic; margin:-.5rem 0 1.1rem;}
.who{font-size:1rem; margin:0 0 .2rem;}
.course{font-size:.88rem; color:var(--muted); margin:0 0 1rem;}
.jg{margin:0 0 1.05rem;}
.spine{margin:0; background:var(--panel); border:1px solid var(--accent); border-radius:7px;
  padding:.5rem .7rem; font-weight:600; font-size:.95rem; color:var(--deep);
  display:flex; flex-wrap:wrap; gap:.15rem .6rem; align-items:baseline;}
.spine span{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.72rem;
  font-weight:400; color:var(--muted);}
.spine.out{background:var(--band-bg); border-color:var(--band-bg); color:var(--band-fg);}
.spine.out span{color:var(--band-fg); opacity:.8;}
.joinlist{list-style:none; margin:0; padding:.55rem 0 .55rem .95rem;
  border-left:2px solid var(--rule); display:flex; flex-direction:column; gap:.5rem;}
.joinlist li{display:flex; flex-wrap:wrap; gap:.15rem .5rem; align-items:baseline;}
.joinlist li::before{display:none}
.js{font-weight:600; font-size:.93rem;}
.joinlist code{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.74rem;
  color:var(--muted);}
.lag{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.64rem;
  letter-spacing:.09em; text-transform:uppercase; color:var(--accent);
  border:1px solid var(--accent); border-radius:99px; padding:.02rem .42rem;}
.sub{font-size:1.05rem; color:var(--ink); margin:0 0 1rem;}
ul.meta{list-style:none; margin:0 0 1.05rem; padding:0; display:flex;
  flex-direction:row; flex-wrap:wrap; gap:.35rem;}
ul.meta li{padding-left:.6rem}
ul.meta li::before{display:none}
ul.meta li{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.72rem;
  color:var(--muted); background:var(--panel); border:1px solid var(--rule);
  border-radius:99px; padding:.2rem .6rem;}

.divider{margin:0; padding:2.2rem 0 .6rem; text-align:center;}
.divider span{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.7rem;
  letter-spacing:.13em; text-transform:uppercase; color:var(--muted);
  border:1px solid var(--rule); border-radius:99px; padding:.32rem .9rem;
  background:var(--surface);}
footer{padding:2rem 0 0; color:var(--muted); font-size:.82rem;}
footer a{color:var(--accent)}
@media (prefers-reduced-motion:reduce){*{transition:none!important; scroll-behavior:auto!important}}
@media (min-width:34rem){ body{font-size:18px} .hero h1{font-size:2.6rem}
  section h2{font-size:1.62rem} }
"""

JS = """
(function(){
  var p=document.getElementById('prog');
  addEventListener('scroll',function(){
    var h=document.documentElement, m=h.scrollHeight-h.clientHeight;
    p.style.width=(m>0?(h.scrollTop||document.body.scrollTop)/m*100:0)+'%';
  },{passive:true});
  var btn=document.getElementById('notes'),
      all=function(){return document.querySelectorAll('section details')};
  function set(on){
    all().forEach(function(d){d.open=on});
    btn.setAttribute('aria-expanded',on?'true':'false');
    btn.textContent=on?'Notes on':'Notes off';
    try{localStorage.setItem('lff-notes',on?'1':'0')}catch(e){}
  }
  var init=false; try{init=localStorage.getItem('lff-notes')==='1'}catch(e){}
  set(init);
  btn.addEventListener('click',function(){set(btn.getAttribute('aria-expanded')!=='true')});
  document.querySelectorAll('.toc a').forEach(function(a){
    a.addEventListener('click',function(){var d=a.closest('details'); if(d)d.open=false;});
  });
})();
"""

doc = f"""<title>London Flip Finder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="top"><div class="bar"><b>London Flip Finder</b><span class="spacer"></span>
<button id="notes" type="button" aria-expanded="false">Notes off</button></div>
<div id="prog"></div></header>

<div class="hero">
<h1>London Flip Finder</h1>
<p>Finding London homes that sold for less than they were worth &mdash; and putting a number
on how much confidence that claim deserves.</p>
<p class="note">Results are held back until slide&nbsp;32; nothing before slide&nbsp;21
quotes an accuracy figure.</p>
<ul class="stats">
<li>59,946 transactions<br>2008&ndash;2016</li>
<li>Four public sources<br>28 features</li>
<li>14 models<br>chronological split</li>
<li>34 slides + 14 backup<br>~28 min</li>
</ul>
</div>

<details class="toc" id="toc"><summary>All {len(specs)} slides</summary>
<ol>{"".join(toc)}</ol></details>

{"".join(body)}

<footer><p>Reading version of <code>presentation.pptx</code>. Every figure and number comes from
<code>london_flip_finder.ipynb</code>; values from &sect;14.6&ndash;&sect;17 were recovered by
re-executing the notebook&rsquo;s own cells, since its saved run stopped at cell&nbsp;67.
See <code>mapping.md</code> for the slide&rarr;cell map.</p></footer>
</div>
<script>{JS}</script>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(doc, encoding="utf-8")
print(f"wrote {OUT}  {OUT.stat().st_size/1e6:.2f} MB  ({len(specs)} slides)")
