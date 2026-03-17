# Chocolate or Garlic

A static blog powered by [Hugo](https://gohugo.io/) and the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme. This repository contains the source code, content, and migration scripts for the *Chocolate or Garlic* website.

## Overview

*Chocolate or Garlic* is a blog featuring articles, walking tours, and cultural insights, with a focus on topics related to Israel, education, and social issues. The site was migrated from WordPress to Hugo using custom scripts provided in this repository.

## Requirements

- **Hugo**: [Extended version recommended](https://gohugo.io/installation/) (tested with Hugo 0.120+).
- **Python 3.11+**: Required only for running the WordPress migration scripts.
- **Git**: For theme submodules and version control.

## Project Structure

```text
.
├── archetypes/       # Content templates for new posts
├── assets/           # CSS, JS, and image assets processed by Hugo
├── content/          # Markdown content (blog posts, pages, etc.)
├── data/             # Supplemental data used by Hugo (JSON/YAML/TOML)
├── hugo.toml         # Main site configuration file
├── layouts/          # Custom HTML templates (overriding theme)
├── public/           # Generated static site (production output)
├── scripts/          # Migration and utility scripts (WP to Hugo)
├── static/           # Static assets (images, PDFs, etc.) copied directly
└── themes/           # Git submodules for themes (e.g., PaperMod)
```

## Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/your-username/chocolateorgarlic.git
cd chocolateorgarlic
git submodule update --init --recursive
```

### 2. Local Development
Run the Hugo development server to preview changes live at `http://localhost:1313`:
```bash
hugo server -D
```

### 3. Build for Production
Generate the static site into the `public/` directory:
```bash
hugo --minify
```

## Migration Scripts

The `scripts/` directory contains tools to migrate content from a WordPress site via the WP REST API.

### WordPress to Hugo Exporter
Located at `scripts/export_wp_to_hugo.py`.

**Setup:**
```bash
pip install requests markdownify python-slugify
```

**Usage:**
```bash
python scripts/export_wp_to_hugo.py --url https://your-wordpress-site.com --output ./content/posts
```

**Environment Variables:**
- `WP_URL`: Base URL of the WordPress site.
- `WP_OUTPUT`: Target directory for generated Markdown files.

See [scripts/README.md](scripts/README.md) for detailed migration instructions.

## Testing

Hugo performs basic validation during build time. To check for broken links or template errors, run:
```bash
hugo --gc --printI18nWarnings
```
*TODO: Add automated testing or CI/CD validation steps if applicable.*

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WP_URL` | WordPress API URL for migration | `https://chocolateorgrarlic.com` |
| `WP_OUTPUT` | Migration script output path | `./content/posts` |

## License

*TODO: Add license information (e.g., MIT, CC-BY-SA).*
The PaperMod theme used in this project is licensed under the [MIT License](themes/PaperMod/LICENSE).
