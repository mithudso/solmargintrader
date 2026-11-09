/** Render external text as text in spreadsheets; numeric cells remain numeric. */
export function spreadsheetText(value) {
  const text = String(value ?? '');
  return typeof value === 'string' && /^[\s\x00-\x1f]*[=+@-]/.test(text) ? `'${text}` : text;
}

export function csvCell(value) {
  const text = spreadsheetText(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
