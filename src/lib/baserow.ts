// Reads rows from Baserow at build time. Nothing fetched here is committed to the repo.
// Without BASEROW_TOKEN (local work, this mock-up) it falls back to the invented sample data.
import { readFile } from 'node:fs/promises';

const API = process.env.BASEROW_URL ?? 'https://api.baserow.io';

export async function fetchRows(tableId: string | undefined, sampleFile: string) {
  const token = process.env.BASEROW_TOKEN;
  if (!token || !tableId) {
    const raw = await readFile(new URL(`../data/sample/${sampleFile}`, import.meta.url), 'utf8');
    return JSON.parse(raw) as Record<string, unknown>[];
  }
  const rows: Record<string, unknown>[] = [];
  let next: string | null = `${API}/api/database/rows/table/${tableId}/?user_field_names=true&size=200`;
  while (next) {
    const res = await fetch(next, { headers: { Authorization: `Token ${token}` } });
    if (!res.ok) throw new Error(`Baserow table ${tableId}: ${res.status} ${res.statusText}`);
    const page = (await res.json()) as { results: Record<string, unknown>[]; next: string | null };
    rows.push(...page.results);
    next = page.next; // follow pagination links rather than capping at one page
  }
  return rows;
}

// Baserow single-select values arrive as { id, value, color } objects.
export const selectValue = (v: unknown) =>
  v && typeof v === 'object' && 'value' in v ? String((v as { value: unknown }).value) : (v as string | null) ?? null;

export const slugify = (s: string) =>
  s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
