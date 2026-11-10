// British date formatting: 14 October 2026
export const longDate = (d: Date) =>
  d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/London' });

// Midnight today in UK time, used to decide which events are upcoming at build time
export const todayUK = () => {
  const s = new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/London' });
  return new Date(`${s}T00:00:00Z`);
};
