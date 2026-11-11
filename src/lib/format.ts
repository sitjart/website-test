// British date formatting: 14 October 2026
export const longDate = (d: Date) =>
  d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/London' });

// Midnight today in UK time, used to decide which events are upcoming at build time
export const todayUK = () => {
  const s = new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/London' });
  return new Date(`${s}T00:00:00Z`);
};

/** First full sentence(s) of a summary, never cut mid-word. */
export function firstSentence(s = '', max = 220): string {
  const m = s.match(/^.{20,}?[.!?](?=\s|$)/);
  if (m && m[0].length <= max) return m[0];
  if (s.length <= max) return s;
  return s.slice(0, s.lastIndexOf(' ', max)) + '…';
}
/** Orange full stop, unless the title already ends in punctuation. */
export const needsStop = (t: string) => !/[.!?…]$/.test(t.trim());
