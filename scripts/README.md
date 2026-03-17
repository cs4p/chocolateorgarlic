# WordPress → Hugo Migration Guide

## Overview

This toolset exports your WordPress posts via the WP REST API and writes Hugo-compatible
Markdown files with YAML front matter, preserving:

- Post title, body content (HTML → Markdown)
- Author display name
- Publication date
- Categories and tags
- Featured image URL
- Excerpt (used as Hugo `description`)
- Original WP slug and post ID (for redirect mapping)

---

## Prerequisites

```bash
# Python 3.11+
pip install requests markdownify python-slugify

# Hugo (macOS example — see https://gohugo.io/installation/)
brew install hugo
```

---

## Step 1 — Run the exporter

```bash
# Basic usage (edit --url to match your site)
python export_wp_to_hugo.py \
    --url https://your-wordpress-site.com \
    --output ./content/posts

# Or use environment variables
export WP_URL=https://your-wordpress-site.com
export WP_OUTPUT=./content/posts
python export_wp_to_hugo.py

# Options:
#   --flat          Don't organize into year subdirectories
#   --per-page N    API page size (default 100, max 100)
```

The script will create files organized by year:
```
content/posts/
├── 2019/
│   └── my-first-post.md
├── 2022/
│   └── another-article.md
└── 2024/
    └── latest-post.md
```

### What a generated file looks like

```markdown
---
title: "My Post Title"
date: 2023-04-15T10:30:00
author: "Dan Chandler"
draft: false
categories: ["Technology", "Security"]
tags: ["fedramp", "cloud"]
featured_image: "https://your-site.com/wp-content/uploads/image.jpg"
slug: "my-post-title"
wordpress_id: 1234
description: "A short excerpt from the post..."
---

Post body content here, converted from HTML to Markdown...
```

---

## Step 2 — Create your Hugo site

```bash
hugo new site my-hugo-site
cd my-hugo-site

# Install a theme (example: PaperMod — fast, clean, popular)
git init
git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Copy your exported posts in
cp -r /path/to/content/posts ./content/
```

---

## Step 3 — Configure Hugo

Edit `hugo.toml` (or `config.toml`):

```toml
baseURL = "https://your-new-site.com/"
languageCode = "en-us"
title = "Your Site Title"
theme = "PaperMod"

[params]
  author = "Your Name"
  ShowReadingTime = true
  ShowPostNavLinks = true

[taxonomies]
  category = "categories"
  tag = "tags"
  author = "authors"   # Enables /authors/ pages per author
```

---

## Step 4 — Preview & build

```bash
# Live preview
hugo server

# Production build (output in ./public/)
hugo --minify
```

---

## Step 5 — Handle redirects (optional but recommended)

If you're replacing an existing WordPress site, create a redirect map so old
URLs don't 404. The exporter preserves the `wordpress_id` and `slug` fields
in front matter to help with this.

For Nginx:
```nginx
# Example redirect for a post that moved paths
rewrite ^/2023/04/my-post-title/?$  /posts/2023/my-post-title/  permanent;
```

Or use Hugo's built-in aliases in front matter:
```yaml
aliases:
  - /2023/04/my-post-title/
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| API returns 401 | Your site may require auth. Add `--user admin:application_password` support (see note below) |
| Posts missing | Check `?status=publish` — drafts are excluded by default |
| Garbled characters | Ensure your terminal/editor uses UTF-8 |
| Images not rendering | Featured images are linked, not downloaded. Run `wget` or `curl` to mirror `/wp-content/uploads/` |

### Authenticated export (private sites)

If your WP REST API requires authentication, generate a **WordPress Application Password**
(Users → Profile → Application Passwords) and pass it via:

```python
# Add to requests.get() calls in the script:
auth = ("your_username", "your_application_password")
resp = requests.get(url, params=params, auth=auth, timeout=30)
```

---

## Downloading images locally (optional)

To make your Hugo site fully self-contained, mirror the uploads folder:

```bash
wget \
  --recursive \
  --no-parent \
  --no-host-directories \
  --cut-dirs=1 \
  --accept "jpg,jpeg,png,gif,webp,svg,pdf" \
  -P static/images \
  https://your-wordpress-site.com/wp-content/uploads/
```

Then update image references in your markdown files with:

```python
import re, pathlib

for f in pathlib.Path("content/posts").rglob("*.md"):
    text = f.read_text()
    text = re.sub(
        r'https://your-wordpress-site\.com/wp-content/uploads/',
        '/images/uploads/',
        text
    )
    f.write_text(text)
```
