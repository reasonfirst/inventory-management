// CSV export helpers

// Quote a value when it contains a delimiter, quote or line break (RFC 4180)
function escapeCell(value) {
  const text = value === null || value === undefined ? '' : String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

// columns: [{ header, value: row => cell }]
export function toCsv(rows, columns) {
  const lines = [columns.map(c => escapeCell(c.header)).join(',')]
  for (const row of rows) {
    lines.push(columns.map(c => escapeCell(c.value(row))).join(','))
  }
  return lines.join('\r\n')
}

export function downloadCsv(filename, csv) {
  // The BOM makes Excel read the file as UTF-8, which keeps Japanese text intact
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
