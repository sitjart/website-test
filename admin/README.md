# Content editor (Decap CMS)

Open `/admin/` on the site. Editors sign in with their GitHub account (they need write access to the repository).

## How publishing works
1. **Save** creates a draft: a branch and a pull request, built and checked like any change.
2. Move it to **In review** on the Workflow board when it's ready.
3. Xènia or Joe **Publish** it: the pull request is merged and the site updates in a couple of minutes.

## One-off set-up: the login helper
Signing in with GitHub needs a small helper that holds the GitHub app's secret. We use the free
[sveltia-cms-auth](https://github.com/sveltia/sveltia-cms-auth) Cloudflare Worker (it works for Decap too):
1. In GitHub (ELIXIR-UK organisation settings › Developer settings › OAuth apps) create an OAuth app.
   Callback URL: the Worker's address followed by `/callback`.
2. Deploy the Worker from its README (one button), with `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
   and `ALLOWED_DOMAINS` set to the site's domain.
3. Put the Worker's address in `admin/config.yml` under `backend: base_url`.

## Working on your own computer
`npx decap-server` in the repository, then open the site locally at `/admin/` – no login needed.
