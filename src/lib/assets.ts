// WordPress uploads copied into public/assets/wp by the "Fetch WordPress SVG assets" workflow.
// If a copy exists, use it: no request to WordPress, and the file ships with the site.
import fs from 'node:fs';
import path from 'node:path';
import { url } from './url';

const dir = path.resolve('public/assets/wp');
const local = new Set(fs.existsSync(dir) ? fs.readdirSync(dir) : []);

export function localAsset(src?: string): string | undefined {
  if (!src) return src;
  const m = src.match(/elixiruknode\.org\/wp-content\/uploads\/.+\/([^/?#]+)$/);
  if (m && local.has(m[1])) return url(`/assets/wp/${m[1]}`);
  return src;
}
export const asset = (file: string) => url(`/assets/wp/${file}`);
