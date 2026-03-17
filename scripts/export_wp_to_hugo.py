#!/usr/bin/env python3
"""
WordPress to Hugo Markdown Exporter
Exports all WordPress posts via the WP REST API and writes Hugo-compatible
markdown scripts with front matter preserving author, date, and metadata.

Requirements:
    pip install requests markdownify python-slugify
"""

import os
import re
import sys
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
from markdownify import markdownify as md
from slugify import slugify


# ---------------------------------------------------------------------------
# Configuration — override via CLI args or environment variables
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://chocolateorgrarlic.com"  # No trailing slash
DEFAULT_OUTPUT_DIR = "./content/posts"
DEFAULT_PER_PAGE = 100  # WP REST API max is 100


def get_all_posts(base_url: str, per_page: int = 100) -> list[dict]:
    """Paginate through the WP REST API and collect all published posts."""
    posts = []
    page = 1
    api_base = f"{base_url}/wp-json/wp/v2"

    print(f"Fetching posts from {api_base} ...")

    while True:
        url = f"{api_base}/posts"
        params = {
            "per_page": per_page,
            "page": page,
            "status": "publish",
            "_embed": True,   # Embeds author, featured media, terms inline
        }

        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code == 400:
            # WP returns 400 when page exceeds total — we're done
            break

        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        posts.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        total_posts = int(resp.headers.get("X-WP-Total", len(posts)))

        print(f"  Page {page}/{total_pages} — {len(posts)}/{total_posts} posts fetched")

        if page >= total_pages:
            break

        page += 1
        time.sleep(0.25)   # Be polite to the server

    return posts


def get_categories(base_url: str) -> dict[int, str]:
    """Return a mapping of category ID -> name."""
    url = f"{base_url}/wp-json/wp/v2/categories"
    resp = requests.get(url, params={"per_page": 100}, timeout=30)
    resp.raise_for_status()
    return {cat["id"]: cat["name"] for cat in resp.json()}


def get_tags(base_url: str) -> dict[int, str]:
    """Return a mapping of tag ID -> name."""
    url = f"{base_url}/wp-json/wp/v2/tags"
    all_tags = {}
    page = 1

    while True:
        resp = requests.get(url, params={"per_page": 100, "page": page}, timeout=30)
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for tag in batch:
            all_tags[tag["id"]] = tag["name"]
        if page >= int(resp.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1

    return all_tags


def extract_author(post: dict) -> str:
    """Extract author display name from the embedded _embedded data."""
    if post["author"] == 2:
        return "Jill"
    elif post["author"] == 3:
        return "Naomi"
    elif post["author"] == 4:
        return "Alexandra"
    else:
        try:
            return post["_embedded"]["author"][0]["name"]
        except (KeyError, IndexError, TypeError):
            return "Unknown"


def extract_featured_image(post: dict) -> str | None:
    """Extract the featured image URL if present."""
    try:
        media = post["_embedded"]["wp:featuredmedia"][0]
        return media.get("source_url")
    except (KeyError, IndexError, TypeError):
        return None


def html_to_markdown(html: str) -> str:
    """Convert HTML content to clean Markdown."""
    if not html:
        return ""

    converted = md(
        html,
        heading_style="ATX",          # Use # ## ### style headings
        bullets="-",                   # Use - for unordered lists
        code_language="",              # Don't guess code language
        newline_style="backslash",
        strip=["script", "style"],
    )

    # Clean up excessive blank lines
    converted = re.sub(r"\n{3,}", "\n\n", converted)
    return converted.strip()


def sanitize_filename(title: str, post_id: int) -> str:
    """Create a filesystem-safe filename from the post title."""
    name = slugify(title, max_length=80, word_boundary=True)
    if not name:
        name = f"post-{post_id}"
    return name


def format_front_matter(post: dict, author: str, categories: list[str], tags: list[str], featured_image: str | None) -> str:
    """Build Hugo YAML front matter block."""
    raw_date = post.get("date", "")
    try:
        dt = datetime.fromisoformat(raw_date)
        date_str = dt.strftime("%Y-%m-%dT%H:%M:%S%z") or raw_date
    except ValueError:
        date_str = raw_date

    title = post["title"]["rendered"].replace('"', '\\"')

    lines = [
        "---",
        f'title: "{title}"',
        f"date: {date_str}",
        f'author: "{author}"',
        f"draft: false",
    ]

    if categories:
        cats_yaml = ", ".join(f'"{c}"' for c in categories)
        lines.append(f"categories: [{cats_yaml}]")

    if tags:
        tags_yaml = ", ".join(f'"{t}"' for t in tags)
        lines.append(f"tags: [{tags_yaml}]")

    if featured_image:
        lines.append(f'featured_image: "{featured_image}"')

    # Preserve original WP slug and ID for reference
    lines.append(f'slug: "{post.get("slug", "")}"')
    lines.append(f"wordpress_id: {post['id']}")

    excerpt_raw = post.get("excerpt", {}).get("rendered", "")
    if excerpt_raw:
        excerpt_plain = re.sub(r"<[^>]+>", "", excerpt_raw).strip().replace('"', '\\"')
        if excerpt_plain:
            lines.append(f'description: "{excerpt_plain[:200]}"')

    lines.append("---")
    return "\n".join(lines)


def export_post(
    post: dict,
    output_dir: Path,
    cat_map: dict[int, str],
    tag_map: dict[int, str],
    organize_by_year: bool = True,
) -> Path:
    """Convert a single WP post dict to a Hugo markdown file."""

    author = extract_author(post)
    featured_image = extract_featured_image(post)

    # Resolve categories and tags
    cat_ids = post.get("categories", [])
    tag_ids = post.get("tags", [])
    categories = [cat_map.get(cid, str(cid)) for cid in cat_ids]
    tags = [tag_map.get(tid, str(tid)) for tid in tag_ids]

    # Determine output subdirectory
    raw_date = post.get("date", "")
    try:
        dt = datetime.fromisoformat(raw_date)
        year = str(dt.year)
    except ValueError:
        year = "unknown"

    if organize_by_year:
        post_dir = output_dir / year
    else:
        post_dir = output_dir

    post_dir.mkdir(parents=True, exist_ok=True)

    # Build filename
    title = post["title"]["rendered"]
    filename = sanitize_filename(title, post["id"]) + ".md"
    filepath = post_dir / filename

    # Build file content
    front_matter = format_front_matter(post, author, categories, tags, featured_image)
    body_html = post.get("content", {}).get("rendered", "")
    body_md = html_to_markdown(body_html)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter)
        f.write("\n\n")
        f.write(body_md)
        f.write("\n")

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Export WordPress posts to Hugo-compatible Markdown scripts."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("WP_URL", DEFAULT_BASE_URL),
        help="WordPress site base URL (e.g. https://example.com)",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("WP_OUTPUT", DEFAULT_OUTPUT_DIR),
        help="Output directory for markdown scripts",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Don't organize posts into year subdirectories",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=DEFAULT_PER_PAGE,
        help="Posts per API page (max 100)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target site : {base_url}")
    print(f"Output dir  : {output_dir.resolve()}")
    print()

    # Fetch taxonomy maps first
    print("Fetching categories...")
    cat_map = get_categories(base_url)
    print(f"  {len(cat_map)} categories found")

    print("Fetching tags...")
    tag_map = get_tags(base_url)
    print(f"  {len(tag_map)} tags found")
    print()

    # Fetch all posts
    posts = get_all_posts(base_url, per_page=args.per_page)
    print(f"\nTotal posts to export: {len(posts)}\n")

    # Export each post
    success = 0
    errors = []

    for i, post in enumerate(posts, 1):
        title = post["title"]["rendered"]
        try:
            filepath = export_post(
                post,
                output_dir,
                cat_map,
                tag_map,
                organize_by_year=not args.flat,
            )
            print(f"  [{i:>3}/{len(posts)}] ✓  {filepath.relative_to(output_dir.parent)}")
            success += 1
        except Exception as exc:
            msg = f"  [{i:>3}/{len(posts)}] ✗  '{title[:60]}' — {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    print(f"\n{'='*60}")
    print(f"Export complete: {success} succeeded, {len(errors)} failed")

    if errors:
        print("\nFailed posts:")
        for err in errors:
            print(err)

    print(f"\nNext steps:")
    print(f"  1. cd to your Hugo site root")
    print(f"  2. Copy {output_dir.resolve()} → <hugo-site>/content/posts/")
    print(f"  3. Run: hugo server -D")


if __name__ == "__main__":
    main()
