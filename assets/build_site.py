"""Builds the one-page bilingual site (index.html) from the English and Arabic guide sources.
The page has an English / العربية switch at the top; both languages live in the same file.
Run from the site folder: python3 -I assets/build_site.py  (writes ./index.html)"""
import re, subprocess, sys, pathlib, html
from html.parser import HTMLParser

ROOT = pathlib.Path.cwd()
A = ROOT / "assets"
errors = []

def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout
    return round(float(out))

def render(src, ar):
    def card(m):
        stem, title = m.group(1), m.group(2)
        v = ROOT / "videos" / f"{stem}.mp4"
        if not v.exists(): errors.append(f"missing video {v.name}")
        if not (A / "thumbs" / f"{stem}.jpg").exists(): errors.append(f"missing thumb {stem}")
        code = stem.rsplit("-", 1)[1]; d = dur(v) if v.exists() else 0
        meta = (("صوت عربي" if code == "ar" else "صوت إنجليزي") + f" · {d} ثانية") if ar else (code.upper() + f" · {d} seconds")
        return (f'<a class="vid" href="videos/{stem}.mp4"><span class="thumb"><img src="assets/thumbs/{stem}.jpg" alt="" loading="lazy"><span class="play"></span></span>'
                f'<span class="vt">{html.escape(title)}<span class="vm">{meta}</span></span></a>')
    body = re.search(r'<div class="doc">(.*)</div>\s*</body>', src, re.S).group(1)
    body = re.sub(r"\{\{v:([a-z0-9-]+)\|([^}]+)\}\}", card, body)
    if ar:  # keep ids unique across the two languages
        body = re.sub(r'\bid="([^"]+)"', r'id="ar-\1"', body)
    return body

en = render((A / "guide.src.html").read_text(), False)
ar = render((A / "guide.ar.src.html").read_text(), True)

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accez Sales Guide</title>
<link rel="stylesheet" href="assets/guide.css">
<link rel="stylesheet" href="assets/guide.ar.css">
<style>
  .langbar {{ position: sticky; top: 0; z-index: 10; display: flex; justify-content: center; gap: 6px; padding: 10px 16px;
    background: rgba(233,238,243,0.92); backdrop-filter: blur(6px); border-bottom: 1px solid var(--line); }}
  .langbar button {{ font: 600 14px 'Inter', 'Cairo', sans-serif; padding: 7px 18px; border-radius: 20px; cursor: pointer;
    border: 1px solid var(--navy); background: #fff; color: var(--navy); }}
  .langbar button[lang="ar"] {{ font-family: 'Cairo', sans-serif; }}
  .langbar button[aria-pressed="true"] {{ background: var(--navy); color: #fff; }}
  .langbar button:focus-visible {{ outline: 2px solid var(--navy2); outline-offset: 2px; }}
  [data-lang-pane][hidden] {{ display: none !important; }}
  @media print {{ .langbar {{ display: none; }} }}
</style>
</head>
<body>
<nav class="langbar" aria-label="Language">
  <button type="button" lang="en" data-set-lang="en" aria-pressed="true">English</button>
  <button type="button" lang="ar" data-set-lang="ar" aria-pressed="false">العربية</button>
</nav>
<div class="doc" data-lang-pane="en" lang="en" dir="ltr">{en}</div>
<div class="doc" data-lang-pane="ar" lang="ar" dir="rtl" hidden>{ar}</div>
<script>
(function () {{
  var TITLES = {{ en: "Accez Sales Guide", ar: "دليل مبيعات أكسيز" }};
  function show(lang) {{
    if (lang !== "ar") lang = "en";
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.title = TITLES[lang];
    document.querySelectorAll("[data-lang-pane]").forEach(function (p) {{ p.hidden = p.getAttribute("data-lang-pane") !== lang; }});
    document.querySelectorAll("[data-set-lang]").forEach(function (b) {{ b.setAttribute("aria-pressed", String(b.getAttribute("data-set-lang") === lang)); }});
    try {{ localStorage.setItem("accez-guide-lang", lang); }} catch (e) {{}}
  }}
  document.querySelectorAll("[data-set-lang]").forEach(function (b) {{
    b.addEventListener("click", function () {{ show(b.getAttribute("data-set-lang")); window.scrollTo(0, 0); }});
  }});
  var start = null;
  var q = (location.search.match(/[?&]lang=(en|ar)/) || [])[1] || (location.hash === "#ar" ? "ar" : location.hash === "#en" ? "en" : null);
  if (q) start = q;
  if (!start) {{ try {{ start = localStorage.getItem("accez-guide-lang"); }} catch (e) {{}} }}
  if (!start) start = (navigator.language || "").toLowerCase().indexOf("ar") === 0 ? "ar" : "en";
  show(start);
}})();
</script>
</body>
</html>
'''

for ref in set(re.findall(r'(?:src|href)="((?:assets|videos|Company%20profiles)/[^"#]+)"', page)):
    if not (ROOT / ref.replace("%20", " ")).exists(): errors.append(f"missing file {ref}")
text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", page, flags=re.S)
for bad in ["—", "–", " - "]:
    if bad in text: errors.append(f"dash found: {bad!r}")
class Bal(HTMLParser):
    VOID = {"img", "br", "meta", "link", "hr", "input"}
    def __init__(s): super().__init__(); s.stack = []; s.err = []
    def handle_starttag(s, t, a):
        if t not in s.VOID: s.stack.append(t)
    def handle_endtag(s, t):
        if not s.stack or s.stack[-1] != t: s.err.append(f"unexpected </{t}> line {s.getpos()[0]}")
        else: s.stack.pop()
bp = Bal(); bp.feed(page); errors += bp.err[:5]
if bp.stack: errors.append(f"unclosed: {bp.stack}")
ids = re.findall(r'\bid="([^"]+)"', page)
if len(ids) != len(set(ids)): errors.append("duplicate ids")
if errors: print("\n".join(errors)); sys.exit(1)
(ROOT / "index.html").write_text(page)
print("built index.html (English + Arabic)")
