# ELIXIR-UK website (test rebuild)

A static rebuild of [elixiruknode.org](https://elixiruknode.org) with Jekyll. Live test: https://sitjart.github.io/website-test/

## How a build works

Every push, every night and every Baserow change runs three steps. **If any step finds a problem, nothing is published**, and the problem is listed in the Actions run summary.

| Step | What it does | Stops the build when |
|---|---|---|
| 1. `tools/prepare.py` | Reads the content files, the directory records and the people. Checks every field, builds the knowledge graph, resizes images and writes what each page shows into `_data/gen/`. | A content file is wrong: missing title, a date that isn't a date, an unknown event format… |
| 2. `jekyll build` | Turns the templates and that data into pages. Liquid runs in **strict mode**. | A template uses a value that doesn't exist (named with file and line). |
| 3. `tools/finish.py` | Adds the base path to links, builds the search index and checks every internal link and image. | A link made by a template is broken. Broken links inside text written in the CMS are listed as warnings. |

The templates contain no logic beyond "print this, repeat that". Anything that needs working out (who leads a Club, which stories belong to an organisation, upcoming or past) happens in Python, in `tools/sitebuild/`.

## Where things live

| What | Where | Edited in |
|---|---|---|
| News and stories | `collections/_news/*.md` | the CMS |
| Events | `collections/_events/*.md` | the CMS |
| Content pages (What we do, Join in …) | `collections/_webpages/*.md` | the CMS |
| Services, members, projects, communities, collaborators, thematic areas | `_data/directory/*.json` | Baserow (later) |
| People | fetched at build time; **never stored in this repository** | Baserow / WordPress |
| Menus, footer, home page text, service labels | `_data/*.json` | GitHub |
| Page templates | `_layouts/`, `_includes/`, `index.html`, `about.html`, `*/index.html` | GitHub |
| Styles | `_sass/` – one file per component, and one per page (applies only to that page) | GitHub |
| Scripts | `assets/js/` – one file per component or page | GitHub |

Front matter of a story or event (the block between `---` lines) can also list:

- `related:` records it links to, by kind and slug, for example `members: [university-of-oxford]`;
- `about:` organisations the item is **about**. A story tagged with a person *and* their organisation drops the organisation – it is there because of the person – unless the organisation is listed here;
- `display:` `hide` or `show` linked records on this page only (see `_data/display-rules.json`).

`_data/corrections.json` removes people from leads or governance roles until the source data is fixed. Review it when moving people to Baserow.

## Editing in the CMS, with review

Stories, events and pages are edited in [Decap CMS](https://decapcms.org) at `/admin/` (set-up: `admin/README.md`).

1. **Save** makes a draft: its own branch and pull request, built and checked like any change.
2. Drafts move across the **Workflow** board: Draft → In review → Ready.
3. Xènia or Joe **publish**: the pull request is merged and the site updates in a couple of minutes.

Text is Markdown. Where Markdown isn't enough:
- a button: `[Fill in the form](https://…){: .btn}`
- a note panel: a quote followed by `{: .wp-note}`
- accordions and tabs: **Sections** in the editor (`blocks:` in the file).

People are tagged with a picker that shows names but stores numbers, so no names are kept in the repository.
The picker's lists come from `/assets/cms-index.json`, which the build publishes (published profiles only).

## Addresses and search engines

- Every page keeps its WordPress address (`/event/…`, `/service/…`, `/news/2025/…`). The build checks all of
  them against `tools/wordpress-urls.txt` and stops if one goes missing.
- Anything that moves goes in `_redirects` (`/old/ /new/ 301`), which Cloudflare Pages reads.
- The build writes `sitemap.xml` and `robots.txt`. `indexable: false` in `_config.yml` keeps the test site out of
  search engines; set it to `true` on the real domain.

## Working on it locally

```sh
pip install -r tools/requirements.txt
bundle install
PEOPLE_SOURCE=sample python3 tools/prepare.py   # invented sample people; leave it out to fetch from WordPress
bundle exec jekyll serve
```

## Credits

Built by Xènia Pérez Sitjà with Claude (Anthropic) as a coding assistant.
