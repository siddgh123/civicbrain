// docs/05_UI_SPEC.md §2: dates in Asia/Kolkata, e.g. "5 Oct 2026, 8:20 am".
const DATE_TIME = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
});

const DATE_ONLY = new Intl.DateTimeFormat('en-IN', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' });

/** A calendar date `YYYY-MM-DD` (e.g. a plan's date), shown as "6 Oct 2026" without any time-zone shift. */
export function formatDate(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (match === null) return isoDate;
  return DATE_ONLY.format(new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]))));
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return DATE_TIME.format(date)
    .replace(/\b(AM|PM)\b/, (m) => m.toLowerCase())
    .replace(/(\d{4}) at /, '$1, ');
}
