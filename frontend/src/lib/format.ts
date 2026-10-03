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

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return DATE_TIME.format(date)
    .replace(/\b(AM|PM)\b/, (m) => m.toLowerCase())
    .replace(/(\d{4}) at /, '$1, ');
}
