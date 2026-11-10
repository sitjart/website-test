# ELIXIR-UK website – static rebuild (test)

A rebuild of [elixiruknode.org](https://elixiruknode.org) as a static Astro site, keeping the current design.

## How it fits together

- **Pages** are lists of sections in `src/content/pages/*.md`. Each section is one building block (`hero`, `cards`, `latestNews`, `upcomingEvents`, `stat`, `text`, `cta`). To change a page, edit its section list.
- **News and events** are Markdown files in `src/content/news/` and `src/content/events/`, imported once from the WordPress export.
- **People** come from Baserow at build time and are **never stored in this repo**. Only people whose `Website status` is "Consent given" are built. Without a Baserow token the build uses invented sample people.
- **Services and members** are in `src/data/` for now; they will move to Baserow.
- **Design tokens** (colours, fonts, animations) are in `src/styles/global.css`, taken from the live site.

The build runs on every push, every night, and when Baserow sends a `baserow-update` event, then deploys to GitHub Pages.

## Working on it

```sh
npm install
npm run dev      # local preview at http://localhost:4321/website-test/
npm run build    # production build into dist/
```

## Importing from WordPress

```sh
python3 -I tools/import-wordpress.py path/to/export.xml
```

Never commit the export file: it contains personal data.

## Not yet done

- Images are still loaded from the live WordPress site.
- Inner pages (What we do, Join in, Who we are, services, members, projects) are not built yet.
- Search, cookie notice and the mega-menu images from the live site.
