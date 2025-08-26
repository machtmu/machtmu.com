# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the official website for MACH (TMU's Liquid Rocketry team), built using MkDocs Material for documentation and project showcases. The site documents their liquid propulsion systems, avionics development, and test campaigns including GAR-E engine tests and SPRINT systems.

## Development Commands

### Building and Serving
```bash
# Install dependencies
pip install -r requirements.txt

# Serve locally for development (with live reload)
mkdocs serve

# Build static site for production
mkdocs build

# Deploy to GitHub Pages (if configured)
mkdocs gh-deploy
```

### Development Server
- Local development server runs at `http://127.0.0.1:8000`
- Auto-reloads on file changes in `docs/`, `overrides/`, and `mkdocs.yml`
- Use `mkdocs serve` for all local development work

## Site Architecture

### Content Structure
- **`docs/`** - All markdown content and assets
  - `index.md` - Homepage content (uses custom template)
  - `GAR-E/` - Engine test documentation and videos
  - `SPRINT/` - SPRINT system documentation
  - `avionics/` - PCB modules and electronics documentation
  - `sabre/` - Sabre project documentation
  - `blog/` - Blog posts organized by year/month
  - `resources/` - Technical documents and PDFs
  - `assets/` - Images and videos for the site

### Theme Customization
- **`overrides/index.html`** - Custom homepage template with video backgrounds, parallax effects, and interactive elements
- **`mkdocs.yml`** - Main configuration with Material theme settings, plugins, and navigation
- **Custom CSS** - Embedded in `overrides/index.html` with professional dark theme, consistent spacing system, and responsive design

### Key Features
- Full-screen video hero section with fallback images
- Animated star field background
- Parallax scrolling effects
- Professional dark navy color scheme (#0A0E1A)
- Responsive grid layouts for project showcases
- Integrated blog with RSS feeds
- Git revision dates on pages

## Content Guidelines

### Documentation Structure
- Each major project (GAR-E, SPRINT, avionics) has its own directory
- Test results include thumbnails, videos, and detailed markdown documentation
- Technical resources stored as PDFs in `resources/` directory

### Media Management
- Videos stored in `docs/assets/videos/` (supports .mp4, .mov)
- Images stored in `docs/assets/images/` with organized subdirectories
- Thumbnails named `thmbnl.png` for consistency
- Video backgrounds optimized for web with mobile-specific versions

### Blog Posts
- Located in `docs/blog/posts/YYYY/month/`
- Follow MkDocs blog plugin conventions
- Include proper frontmatter for author and date metadata

## Technical Notes

### MkDocs Configuration
- Uses Material theme with custom directory overrides
- Plugins: git-revision-date-localized, blog, search, RSS, table-reader
- Markdown extensions for math, syntax highlighting, and enhanced formatting
- Social media integration and repository links configured

### Performance Considerations
- Video backgrounds with autoplay and fallback posters
- Parallax effects disabled on mobile for performance
- Optimized star field animation with CSS transforms
- Lazy loading and responsive media queries implemented

### Browser Compatibility
- Fallback mechanisms for video autoplay restrictions
- User interaction triggers for media playback
- Progressive enhancement for JavaScript features
- Mobile-first responsive design approach