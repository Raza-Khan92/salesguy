"""Builds 'Accez Sales Guide.html' and '.pdf' from assets/guide.src.html.
Run: python3 -I assets/build.py  (from the 'Accez Sales Guide' folder)"""
import re, subprocess, sys, pathlib, html
G = pathlib.Path(__file__).resolve().parent.parent
src = (G / "assets/guide.src.html").read_text()
def dur(p):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True).stdout
    return round(float(out))
errors = []
def card(m):
    stem, title = m.group(1), m.group(2)
    v = G / "videos" / f"{stem}.mp4"; t = G / "assets/thumbs" / f"{stem}.jpg"
    if not v.exists(): errors.append(f"missing video {v.name}")
    if not t.exists(): errors.append(f"missing thumb {t.name}")
    lang = {"ar":"AR","en":"EN"}[stem.rsplit("-",1)[1]]
    d = dur(v) if v.exists() else 0
    return (f'<a class="vid" href="videos/{stem}.mp4"><span class="thumb"><img src="assets/thumbs/{stem}.jpg" alt=""><span class="play"></span></span>'
            f'<span class="vt">{html.escape(title)}<span class="vm">{lang} · {d} seconds</span></span></a>')
out = re.sub(r"\{\{v:([a-z0-9-]+)\|([^}]+)\}\}", card, src)
for ref in re.findall(r'(?:src|href)="((?:assets|videos|Company%20profiles)/[^"#]+)"', out):
    if not (G / ref.replace("%20"," ")).exists(): errors.append(f"missing file {ref}")
text = re.sub(r"<[^>]+>", " ", out)
for bad in ["—","–"," - "]:
    if bad in text: errors.append(f"dash found: {bad!r} near {text[text.find(bad)-40:text.find(bad)+40]!r}")
for a in set(re.findall(r'href="#([^"]+)"', out)):
    if f'id="{a}"' not in out and a != "contact": errors.append(f"broken anchor #{a}")
from html.parser import HTMLParser
class Bal(HTMLParser):
    VOID = {"img","br","meta","link","hr","input"}
    def __init__(s): super().__init__(); s.stack=[]; s.err=[]
    def handle_starttag(s,t,a):
        if t not in s.VOID: s.stack.append(t)
    def handle_endtag(s,t):
        if not s.stack or s.stack[-1]!=t: s.err.append(f"unexpected </{t}> at line {s.getpos()[0]}, open: {s.stack[-3:]}")
        else: s.stack.pop()
bp = Bal(); bp.feed(out)
errors += bp.err[:5]
if bp.stack: errors.append(f"unclosed tags: {bp.stack}")
if errors: print("\n".join(errors)); sys.exit(1)
(G / "Accez Sales Guide.html").write_text(out)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=["--allow-file-access-from-files"]); pg = b.new_page()
    pg.goto((G / "Accez Sales Guide.html").as_uri(), wait_until="networkidle"); pg.evaluate("document.fonts.ready")
    pg.pdf(path=str(G / "Accez Sales Guide.pdf"), format="A4", print_background=True, prefer_css_page_size=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template='<div style="font-size:7pt;color:#4E5D6C;width:100%;padding:0 13mm;display:flex;justify-content:space-between"><span>Accez Sales Guide · Internal</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
    b.close()
# Chrome prints local links as absolute file:///Users/... paths, which break on any other computer.
# Rewrite them as Launch actions with a path relative to the PDF, so they work inside the shared folder.
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, TextStringObject
pdf = G / "Accez Sales Guide.pdf"; r = PdfReader(str(pdf)); w = PdfWriter(clone_from=r)
prefix = G.as_uri() + "/"; fixed = 0; left = 0
for page in w.pages:
    for a in page.get("/Annots") or []:
        o = a.get_object(); A = o.get("/A")
        if A is None or "/URI" not in A: continue
        uri = str(A["/URI"])
        if uri.startswith(prefix):
            from urllib.parse import unquote
            rel = unquote(uri[len(prefix):])
            fs = DictionaryObject({NameObject("/Type"): NameObject("/Filespec"), NameObject("/F"): TextStringObject(rel), NameObject("/UF"): TextStringObject(rel)})
            o[NameObject("/A")] = DictionaryObject({NameObject("/S"): NameObject("/Launch"), NameObject("/F"): fs})
            fixed += 1
        elif uri.startswith("file:"): left += 1
w.write(str(pdf))
if left: print("absolute file links left:", left); sys.exit(1)
print("built; local links made relative:", fixed)
