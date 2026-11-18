"""Static site builder for AmbientNoise.Online.

Usage:  python build.py
Reads   index.html (the sound machine) and content/posts/*.md
Writes  site/  -> upload this folder to your web host.
"""
import html, json, re, shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "site"
SITE = "https://ambientnoise.online"
NAME = "Ambient Noise"
TAGLINE = "Free ambient sound machine for sleep, focus and relaxation"
SKYCALM = "https://apps.apple.com/us/app/skycalm-fear-of-flying/id6746972686"
TODAY = date.today().isoformat()
CATS = ["Sleep", "Focus", "Noise Colors", "Wellbeing", "Travel", "Guides"]

esc = lambda s: html.escape(str(s), quote=True)


# ---------- content ----------
def parse_post(path):
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: missing front matter")
    meta, faq = {}, []
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "faq" and "|" in v:
            q, a = v.split("|", 1)
            faq.append((q.strip(), a.strip()))
        else:
            meta[k] = v
    meta["slug"] = path.stem
    meta["faq"] = faq
    meta["md"] = m.group(2).strip()
    meta["url"] = f"/blog/{path.stem}/"
    meta.setdefault("category", "Guides")
    meta["words"] = len(re.findall(r"\w+", meta["md"]))
    meta["minutes"] = max(2, round(meta["words"] / 220))
    return meta


def inline(t):
    t = esc(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: link(m.group(1), html.unescape(m.group(2))), t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def link(text, href):
    ext = href.startswith("http") and not href.startswith(SITE)
    attrs = ' target="_blank" rel="noopener"' if ext else ""
    return f'<a href="{esc(href)}"{attrs}>{text}</a>'


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def md_to_html(md):
    out, toc, para, lst = [], [], [], None

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
            lst = None

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush(); continue
        h = re.match(r"(#{2,4})\s+(.*)", s)
        if h:
            flush()
            lvl, text = len(h.group(1)), h.group(2).strip()
            hid = slugify(text)
            if lvl == 2:
                toc.append((hid, text))
            out.append(f'<h{lvl} id="{hid}">{inline(text)}</h{lvl}>')
            continue
        if s.startswith("> "):
            flush(); out.append(f'<aside class="callout">{inline(s[2:])}</aside>'); continue
        ul, ol = re.match(r"[-*]\s+(.*)", s), re.match(r"\d+[.)]\s+(.*)", s)
        if ul or ol:
            tag = "ul" if ul else "ol"
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
            if lst and lst[0] != tag:
                flush()
            lst = lst or (tag, [])
            lst[1].append((ul or ol).group(1)); continue
        if lst and line.startswith("  "):
            lst[1][-1] += " " + s; continue
        if lst:
            flush()
        para.append(s)
    flush()
    return "\n".join(out), toc


# ---------- shared layout ----------
CSS = """
:root{--bg:#f4f1ea;--bg2:#ebe6db;--card:#fffdf8;--ink:#1f2a2e;--muted:#5d6a6e;--line:#ddd5c6;--accent:#2f6f73;--accent-ink:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1517;--bg2:#151d20;--card:#182226;--ink:#e7ece9;--muted:#97a6a6;--line:#26343a;--accent:#7cc4bd;--accent-ink:#0f1517}}
:root[data-theme="dark"]{--bg:#0f1517;--bg2:#151d20;--card:#182226;--ink:#e7ece9;--muted:#97a6a6;--line:#26343a;--accent:#7cc4bd;--accent-ink:#0f1517}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.7 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
.strip{display:block;text-align:center;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-size:14px;padding:9px 16px;line-height:1.4}
.strip:hover strong{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
header.top{display:flex;align-items:center;justify-content:space-between;padding:18px 0}
.brand{display:flex;gap:10px;align-items:center;font-family:Fraunces,serif;font-weight:600;font-size:20px;text-decoration:none;color:var(--ink)}
.brand svg{color:var(--accent)}
nav a{color:var(--muted);text-decoration:none;margin-left:18px;font-size:14px}
nav a:hover,nav a[aria-current]{color:var(--ink)}
.icon-btn{background:none;border:1px solid var(--line);color:var(--ink);border-radius:999px;width:36px;height:36px;cursor:pointer;margin-left:14px;display:inline-grid;place-items:center}
h1,h2,h3{font-family:Fraunces,serif;font-weight:400;line-height:1.2}
.crumbs{font-size:13px;color:var(--muted);margin:24px 0 8px}
.crumbs a{color:var(--muted)}
.post-head h1{font-size:clamp(32px,5vw,50px);margin:6px 0 14px;max-width:22ch}
.post-head .lede{color:var(--muted);font-size:19px;max-width:60ch;margin:0 0 14px}
.byline{font-size:14px;color:var(--muted)}
.chip{display:inline-block;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);text-decoration:none}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:48px;margin-top:32px}
article{max-width:68ch}
article h2{font-size:28px;margin:40px 0 10px}
article h3{font-size:21px;margin:28px 0 6px}
article li{margin:6px 0}
.callout{background:var(--bg2);border-left:3px solid var(--accent);border-radius:10px;padding:14px 18px;margin:20px 0;font-size:16px}
.side{position:sticky;top:20px;align-self:start;display:flex;flex-direction:column;gap:16px}
.box{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;font-size:14px}
.box h4{margin:0 0 8px;font:600 13px Inter,sans-serif;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.box ol{margin:0;padding-left:18px}.box li{margin:4px 0}.box a{text-decoration:none}
.btn{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:var(--accent-ink);border-radius:999px;padding:10px 18px;font-weight:600;text-decoration:none;font-size:15px}
.trymix{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;margin:36px 0;display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}
.trymix p{margin:0}.trymix small{display:block;color:var(--muted);font-size:13px}
.faq details{border-bottom:1px solid var(--line);padding:12px 0}
.faq summary{cursor:pointer;font-weight:600}
.faq p{margin:8px 0 0;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;text-decoration:none;color:var(--ink);display:flex;flex-direction:column;gap:8px;transition:border-color .2s}
.card:hover{border-color:var(--accent)}
.card h3{margin:0;font-size:21px}
.card p{margin:0;color:var(--muted);font-size:15px;line-height:1.55}
.card .meta{font-size:13px;color:var(--muted);margin-top:auto}
.promo{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between;background:var(--bg2);border-radius:18px;padding:20px 22px;margin:40px 0 0}
.promo p{margin:0;max-width:52ch;font-size:15px}
.store{display:inline-flex;align-items:center;gap:8px;background:var(--ink);color:var(--bg);text-decoration:none;border-radius:12px;padding:9px 16px;font-weight:600;font-size:15px}
.pagehead{padding:36px 0 8px}.pagehead h1{font-size:clamp(34px,5vw,52px);margin:0 0 8px}.pagehead p{color:var(--muted);margin:0;max-width:60ch}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}
.filters a{border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:14px;text-decoration:none;color:var(--ink)}
.filters a:hover{border-color:var(--accent)}
section.cat{margin:36px 0}
.sitemap ul{columns:2 280px;padding-left:18px}.sitemap li{margin:6px 0;break-inside:avoid}
.prose{max-width:68ch}
footer{border-top:1px solid var(--line);margin-top:64px;padding:28px 0 40px;color:var(--muted);font-size:14px}
footer .cols{display:flex;flex-wrap:wrap;gap:12px 24px}
footer a{color:var(--muted)}
@media (max-width:860px){.layout{grid-template-columns:1fr}.side{position:static}nav a.opt{display:none}}
@media (max-width:560px){nav a{margin-left:12px}nav a.opt2{display:none}body{font-size:16px}}
"""

LOGO = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2"/></svg>'
APPLE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.4 12.6c0-2.4 2-3.6 2.1-3.7-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.8-1.6 0-3.1 1-4 2.4-1.7 3-.4 7.3 1.2 9.7.8 1.2 1.8 2.5 3 2.4 1.2 0 1.7-.8 3.1-.8 1.5 0 1.9.8 3.2.8 1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.5-1-2.5-3.8zM14 5.4c.7-.8 1.1-1.9 1-3-1 0-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.9 1.1.1 2.1-.6 2.8-1.4z"/></svg>'

THEME_JS = """<script>
try{var t=localStorage.getItem('an-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}
document.getElementById('theme').onclick=function(){var r=document.documentElement,d=r.dataset.theme?r.dataset.theme==='dark':matchMedia('(prefers-color-scheme:dark)').matches;r.dataset.theme=d?'light':'dark';try{localStorage.setItem('an-theme',r.dataset.theme)}catch(e){}};
</script>"""


def head(title, desc, path, og_type="website", extra_ld=None, robots="index, follow, max-image-preview:large"):
    url = SITE + path
    lds = "".join(f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n' for ld in (extra_ld or []))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{NAME} blog" href="/feed.xml">
<meta name="theme-color" content="#2f6f73">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
{lds}</head>
<body>
<a class="strip" href="{SKYCALM}" target="_blank" rel="noopener"><span>&#9992;</span> Nervous about flying? <strong>Try SkyCalm</strong>, our iPhone app for fear of flying <span aria-hidden="true">&rarr;</span></a>
<div class="wrap">
<header class="top">
  <a class="brand" href="/">{LOGO}{NAME}</a>
  <div><nav><a href="/">Sound machine</a><a href="/blog/"{' aria-current="page"' if path.startswith('/blog') else ''}>Blog</a><a class="opt" href="/about/">About</a><a class="opt2" href="{SKYCALM}" target="_blank" rel="noopener">SkyCalm</a></nav><button class="icon-btn" id="theme" aria-label="Toggle dark mode"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/></svg></button></div>
</header>
"""


def footer():
    return f"""</div>
<footer><div class="wrap"><div class="cols">
<span>&copy; {date.today().year} {NAME}</span>
<a href="/">Sound machine</a><a href="/blog/">Blog</a><a href="/about/">About</a><a href="/privacy/">Privacy</a>
<a href="/sitemap/">Sitemap</a><a href="/feed.xml">RSS</a>
<a href="{SKYCALM}" target="_blank" rel="noopener">SkyCalm for nervous flyers</a>
</div><p>Ambient sound is not a medical treatment. Keep volume low and talk to a doctor about sleep, hearing or anxiety problems.</p></div></footer>
{THEME_JS}
</body></html>"""


def org_ld():
    return {"@type": "Organization", "name": NAME, "url": SITE + "/", "logo": SITE + "/icon-512.png"}


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]}


def card(p):
    return (f'<a class="card" href="{p["url"]}"><span class="chip">{esc(p["category"])}</span>'
            f'<h3>{esc(p["title"])}</h3><p>{esc(p["description"])}</p>'
            f'<span class="meta">{p["minutes"]} min read</span></a>')


def nice_date(d):
    d = date.fromisoformat(d)
    return f"{d:%B} {d.day}, {d.year}"


# ---------- pages ----------
def write(path, text):
    f = OUT / path.lstrip("/")
    if path.endswith("/"):
        f = f / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")


def post_page(p, posts):
    body, toc = md_to_html(p["md"])
    related = [q for q in posts if q["slug"] != p["slug"] and q["category"] == p["category"]]
    related += [q for q in posts if q["slug"] != p["slug"] and q not in related]
    related = related[:3]
    ld = [{
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"], "description": p["description"],
        "datePublished": p["date"], "dateModified": p.get("updated", p["date"]),
        "mainEntityOfPage": SITE + p["url"], "image": SITE + "/og.png",
        "author": org_ld(), "publisher": org_ld(), "keywords": p.get("keyword", ""),
        "articleSection": p["category"], "wordCount": p["words"]},
        crumbs_ld([("Home", "/"), ("Blog", "/blog/"), (p["title"], p["url"])])]
    if p["faq"]:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p["faq"]]})
    mix = p.get("mix", "")
    trymix = (f'<div class="trymix"><p><small>Try this mix</small><strong>{esc(p.get("mixname", "Open the sound machine"))}</strong></p>'
              f'<a class="btn" href="/#mix={esc(mix)}">&#9654; Play it free</a></div>') if mix else ""
    faq = ""
    if p["faq"]:
        faq = '<h2 id="faq">Questions people ask</h2><div class="faq">' + "".join(
            f"<details><summary>{esc(q)}</summary><p>{inline(a)}</p></details>" for q, a in p["faq"]) + "</div>"
    toc_html = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in toc)
    side_mix = f'<div class="box"><h4>Listen while you read</h4><p style="margin:0 0 12px">{esc(p.get("mixname", ""))}</p><a class="btn" href="/#mix={esc(mix)}">&#9654; Play</a></div>' if mix else ""
    html_ = head(f'{p["title"]}', p["description"], p["url"], "article", ld)
    html_ += f"""<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/blog/">Blog</a> / <a href="/blog/category/{slugify(p['category'])}/">{esc(p['category'])}</a></nav>
<div class="post-head"><a class="chip" href="/blog/category/{slugify(p['category'])}/">{esc(p['category'])}</a>
<h1>{esc(p['title'])}</h1><p class="lede">{esc(p['description'])}</p>
<div class="byline">By the {NAME} team &middot; <time datetime="{p['date']}">{nice_date(p['date'])}</time> &middot; {p['minutes']} min read</div></div>
<div class="layout"><article>
{body}
{trymix}
{faq}
<div class="promo"><p><strong>Nervous about flying?</strong> SkyCalm is an iPhone app for people who get anxious on flights.</p><a class="store" href="{SKYCALM}" target="_blank" rel="noopener">{APPLE} App Store</a></div>
</article>
<aside class="side"><div class="box"><h4>Nervous flyer?</h4><p style="margin:0 0 12px">SkyCalm is our iPhone app for people who get anxious about flying.</p><a class="store" href="{SKYCALM}" target="_blank" rel="noopener">{APPLE} App Store</a></div>{side_mix}<div class="box"><h4>On this page</h4><ol>{toc_html}<li><a href="#faq">FAQ</a></li></ol></div></aside></div>
<section style="margin-top:56px"><h2>Keep reading</h2><div class="cards">{''.join(card(q) for q in related)}</div></section>
"""
    write(p["url"], html_ + footer())


def blog_index(posts):
    cats = [c for c in CATS if any(p["category"] == c for p in posts)]
    ld = [{"@context": "https://schema.org", "@type": "Blog", "name": f"{NAME} blog", "url": SITE + "/blog/",
           "publisher": org_ld(), "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": SITE + p["url"], "datePublished": p["date"]} for p in posts]},
          crumbs_ld([("Home", "/"), ("Blog", "/blog/")])]
    h = head(f"Sleep, Focus & Noise Guides | {NAME} Blog", "Guides to white, pink and brown noise, sleep sounds, focus, tinnitus, babies and travel. Practical, research-aware advice from AmbientNoise.Online.", "/blog/", extra_ld=ld)
    h += '<div class="pagehead"><h1>The Ambient Noise blog</h1><p>Plain-English guides to sleeping, focusing and relaxing with sound. Every guide has a mix you can play in one tap.</p></div>'
    h += '<div class="filters">' + "".join(f'<a href="/blog/category/{slugify(c)}/">{esc(c)}</a>' for c in cats) + "</div>"
    h += f'<div class="cards">{"".join(card(p) for p in posts)}</div>'
    write("/blog/", h + footer())
    for c in cats:
        cp = [p for p in posts if p["category"] == c]
        path = f"/blog/category/{slugify(c)}/"
        h = head(f"{c} Guides | {NAME} Blog", f"Articles about {c.lower()} and ambient sound from AmbientNoise.Online: {', '.join(p['title'] for p in cp[:2])} and more.", path,
                 extra_ld=[crumbs_ld([("Home", "/"), ("Blog", "/blog/"), (c, path)])])
        h += f'<nav class="crumbs"><a href="/">Home</a> / <a href="/blog/">Blog</a></nav><div class="pagehead"><h1>{esc(c)}</h1><p>{len(cp)} guides.</p></div>'
        h += '<div class="filters">' + "".join(f'<a href="/blog/category/{slugify(x)}/">{esc(x)}</a>' for x in cats if x != c) + "</div>"
        h += f'<div class="cards">{"".join(card(p) for p in cp)}</div>'
        write(path, h + footer())
    return cats


STATIC = {
    "/about/": ("About Ambient Noise", "AmbientNoise.Online is a free ambient sound machine. Learn how it works, where the sounds come from, and how we write our guides.", """
<div class="pagehead"><h1>About Ambient Noise</h1></div><div class="prose">
<p>AmbientNoise.Online is a free sound machine that runs in your browser. You can layer rain, ocean waves, fire, birds and night sounds over white, pink or brown noise, set a sleep timer, and share your mix as a link. There's no account and nothing to install.</p>
<h2>Where the sounds come from</h2>
<p>White, pink and brown noise are generated live in your browser, so they never run out and never repeat in an obvious way. The nature recordings stream from the <a href="https://archive.org" target="_blank" rel="noopener">Internet Archive</a>, the nonprofit digital library. Each recording belongs to its uploader. The full list of sources is in the footer of the <a href="/">sound machine</a>. You can also search the Archive from the site and add any recording to your mix.</p>
<h2>How we write our guides</h2>
<p>Our <a href="/blog/">blog</a> explains how people use sound for sleep, focus and relaxation. We describe research carefully, say when evidence is limited, and never present ambient sound as a medical treatment. If you have trouble sleeping, hearing problems or anxiety, please talk to a doctor.</p>
<h2>Our flying app</h2>
<p>We also make <a href="SKY" target="_blank" rel="noopener">SkyCalm</a>, an iPhone app for people who are nervous about flying.</p>
<h2>Safety</h2>
<p>Keep the volume low, especially for long listening or for babies. Don't put speakers right next to a baby's ears. If you hear ringing or have trouble hearing, stop listening and see an audiologist or doctor.</p></div>"""),
    "/privacy/": ("Privacy Policy", "AmbientNoise.Online privacy policy: no accounts, no tracking cookies; your mix is saved only in your browser.", """
<div class="pagehead"><h1>Privacy policy</h1><p>Last updated TODAY</p></div><div class="prose">
<p>AmbientNoise.Online does not require an account and does not collect your name, email or other personal details.</p>
<h2>What stays on your device</h2>
<p>Your last mix and your light or dark setting are saved in your browser's local storage so the page remembers them. They never leave your device. Clearing your browser data removes them.</p>
<h2>Third parties</h2>
<ul><li>Nature recordings and search results load from the Internet Archive (archive.org). Their <a href="https://archive.org/about/terms.php" target="_blank" rel="noopener">terms and privacy policy</a> apply to those requests.</li><li>Fonts load from Google Fonts.</li></ul>
<p>If you add analytics or ads later, update this page to describe them.</p></div>"""),
}


def static_pages():
    for path, (title, desc, body) in STATIC.items():
        body = body.replace("SKY", SKYCALM).replace("TODAY", nice_date(TODAY))
        write(path, head(f"{title} | {NAME}", desc, path, extra_ld=[crumbs_ld([("Home", "/"), (title, path)])]) + body + footer())
    nf = head(f"Page not found | {NAME}", "This page doesn't exist.", "/404.html", robots="noindex")
    nf += '<div class="pagehead"><h1>That page isn\'t here.</h1><p>Try the <a href="/">sound machine</a>, the <a href="/blog/">blog</a> or the <a href="/sitemap/">sitemap</a>.</p></div>'
    (OUT / "404.html").write_text(nf + footer(), encoding="utf-8")


def homepage(posts):
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    latest = "".join(
        f'<a class="post" href="{p["url"]}"><span>{esc(p["category"])}</span><b>{esc(p["title"])}</b></a>' for p in posts[:6])
    src = src.replace("<!--LATEST_POSTS-->", latest)
    (OUT / "index.html").write_text(src, encoding="utf-8")


# ---------- machine-readable ----------
def sitemaps(posts, cats):
    urls = [("/", TODAY, "1.0", "weekly"), ("/blog/", posts[0]["date"] if posts else TODAY, "0.9", "weekly")]
    urls += [(p["url"], p.get("updated", p["date"]), "0.8", "monthly") for p in posts]
    urls += [(f"/blog/category/{slugify(c)}/", TODAY, "0.5", "weekly") for c in cats]
    urls += [("/about/", TODAY, "0.4", "yearly"), ("/privacy/", TODAY, "0.2", "yearly"), ("/sitemap/", TODAY, "0.3", "weekly")]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"  <url><loc>{SITE}{u}</loc><lastmod>{d}</lastmod><changefreq>{f}</changefreq><priority>{pr}</priority></url>" for u, d, pr, f in urls]
    xml.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")

    h = head(f"Sitemap | {NAME}", "Every page on AmbientNoise.Online: the free sound machine, all blog guides by category, and site information.", "/sitemap/")
    h += '<div class="pagehead"><h1>Sitemap</h1></div><div class="sitemap">'
    h += '<h2>Main pages</h2><ul><li><a href="/">Ambient sound machine</a></li><li><a href="/blog/">Blog</a></li><li><a href="/about/">About</a></li><li><a href="/privacy/">Privacy policy</a></li><li><a href="/feed.xml">RSS feed</a></li><li><a href="/sitemap.xml">XML sitemap</a></li><li><a href="/llms.txt">llms.txt</a></li></ul>'
    for c in cats:
        h += f'<h2><a href="/blog/category/{slugify(c)}/">{esc(c)}</a></h2><ul>' + "".join(
            f'<li><a href="{p["url"]}">{esc(p["title"])}</a></li>' for p in posts if p["category"] == c) + "</ul>"
    h += "</div>"
    write("/sitemap/", h + footer())


def llms(posts, cats):
    lines = [f"# {NAME} (AmbientNoise.Online)", "",
             f"> {NAME} is a free, browser-based ambient sound machine at {SITE}. Visitors layer white, pink and brown noise "
             "(generated in the browser) with nature recordings streamed from the Internet Archive (rain, thunderstorm, ocean, fireplace, "
             "birds, brook, waterfall, crickets, wind, cafe), set a sleep timer, search archive.org for more sounds, and share mixes as links. "
             "No account or install. The blog explains how to use sound for sleep, focus, babies, tinnitus, travel and relaxation.", "",
             "Key facts:",
             "- Price: free. Platform: any modern web browser, desktop or mobile.",
             f"- Mixes can be shared with URLs like {SITE}/#mix=rain:0.70,brown:0.35 (sound id:volume from 0 to 1).",
             "- Sound ids: white, pink, brown, rain, light, thunder, ocean, fire, birds, dusk, stream, falls, night, wind, cafe.",
             "- Ambient sound is not a medical treatment; the site advises low volume and seeing a doctor for sleep, hearing or anxiety problems.",
             f"- Sister product: SkyCalm, an iPhone app for people who are nervous about flying: {SKYCALM}", "",
             "## Main pages", "",
             f"- [Sound machine]({SITE}/): the free ambient noise mixer with sleep timer",
             f"- [Blog]({SITE}/blog/): all guides",
             f"- [About]({SITE}/about/): how the site works and where the sounds come from",
             f"- [Full text of all guides]({SITE}/llms-full.txt): every article as plain Markdown", ""]
    for c in cats:
        lines += [f"## {c}", ""]
        lines += [f"- [{p['title']}]({SITE}{p['url']}): {p['description']}" for p in posts if p["category"] == c]
        lines.append("")
    lines += ["## Optional", "", f"- [Sitemap]({SITE}/sitemap.xml)", f"- [RSS feed]({SITE}/feed.xml)", f"- [Privacy]({SITE}/privacy/)", ""]
    (OUT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")

    full = [f"# {NAME}: full text of all guides", "", f"Source: {SITE}/blog/", ""]
    for p in posts:
        md = re.sub(r"\]\(/", f"]({SITE}/", p["md"])
        full += ["---", "", f"# {p['title']}", "", f"URL: {SITE}{p['url']}", f"Published: {p['date']}", f"Category: {p['category']}", "", md, ""]
        if p["faq"]:
            full += ["## FAQ", ""] + [f"**{q}** {a}\n" for q, a in p["faq"]]
    (OUT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")


def feed(posts):
    from email.utils import format_datetime
    from datetime import datetime, timezone
    items = "".join(
        f"<item><title>{esc(p['title'])}</title><link>{SITE}{p['url']}</link><guid>{SITE}{p['url']}</guid>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(p['date']).replace(tzinfo=timezone.utc))}</pubDate>"
        f"<category>{esc(p['category'])}</category><description>{esc(p['description'])}</description></item>\n" for p in posts)
    rss = (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           f"<title>{NAME} blog</title><link>{SITE}/blog/</link><description>{TAGLINE}</description><language>en</language>"
           f'<atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>\n{items}</channel></rss>\n')
    (OUT / "feed.xml").write_text(rss, encoding="utf-8")


def misc():
    (OUT / "robots.txt").write_text(
        "# Search engines and AI assistants are welcome.\nUser-agent: *\nAllow: /\n\n"
        f"Sitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "assets/site.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#2f6f73"/>'
           '<path d="M6 16h2M11 11v10M16 7v18M21 12v8M26 15v2" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>')
    (OUT / "favicon.svg").write_text(fav, encoding="utf-8")
    (OUT / "manifest.webmanifest").write_text(json.dumps({
        "name": "Ambient Noise", "short_name": "Ambient Noise", "start_url": "/", "display": "standalone",
        "background_color": "#f4f1ea", "theme_color": "#2f6f73", "description": TAGLINE,
        "icons": [{"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}, {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"}]}, indent=2), encoding="utf-8")
    for f in ("og.png", "icon-512.png"):
        if (ROOT / "static" / f).exists():
            shutil.copy(ROOT / "static" / f, OUT / f)


def main():
    posts = sorted((parse_post(p) for p in (ROOT / "content/posts").glob("*.md")), key=lambda p: p["date"], reverse=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    misc()
    for p in posts:
        post_page(p, posts)
    cats = blog_index(posts)
    static_pages()
    homepage(posts)
    sitemaps(posts, cats)
    llms(posts, cats)
    feed(posts)
    print(f"Built {len(posts)} posts, {len(cats)} categories -> {OUT}")


if __name__ == "__main__":
    main()
