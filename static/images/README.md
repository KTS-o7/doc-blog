# static/images — required assets

Two files are needed here that are currently missing (both return 404):

## favicon.png
- Used as the browser tab icon
- Recommended: 64×64px or 32×32px PNG
- Referenced in hugo.toml: `favicon = "images/favicon.png"`

## share.webp
- Used as the Open Graph / Twitter Card image when sharing links
- Required dimensions: **1200×630px** (16:9 ratio)
- Recommended: your name + blog title on a dark background
- Referenced in hugo.toml: `images = ["images/share.webp"]`

Until these are added, OG previews on Twitter/LinkedIn/Slack will have no image.
