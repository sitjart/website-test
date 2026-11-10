import { defineConfig } from 'astro/config';

// Test deployment on GitHub Pages: https://sitjart.github.io/website-test/
// When moving to elixiruknode.org, set site to that domain and remove base.
export default defineConfig({
  site: 'https://sitjart.github.io',
  base: '/website-test',
  trailingSlash: 'always',
});
