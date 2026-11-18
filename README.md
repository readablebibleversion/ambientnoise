# AmbientNoise.Online

Free ambient sound machine + SEO blog.

- `index.html` — the sound machine (homepage source)
- `content/posts/*.md` — blog posts
- `static/` — og.png share image and app icon
- `build.py` — generates the site

Build:  python build.py
Deploy: upload everything inside `site/` to the web root of ambientnoise.online,
then submit https://ambientnoise.online/sitemap.xml in Google Search Console and Bing Webmaster Tools.

## Hosting

GitHub Pages. Every push to `main` runs `build.py` and deploys `site/` (see `.github/workflows/deploy.yml`).
So the usual flow is: edit or add a post, then `git add -A && git commit -m "..." && git push`.
