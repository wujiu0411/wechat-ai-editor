const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export function assetUrl(filepath) {
  if (!filepath) return ''
  // If already absolute URL, return as-is
  if (filepath.startsWith('http://') || filepath.startsWith('https://')) return filepath
  return `${BASE_URL}/api/assets/serve/${filepath}`
}

export function fixHtmlImages(html) {
  if (!html) return html
  // Replace /api/assets/serve/... with absolute URLs
  return html.replace(/src="\/api\/assets\/serve\/([^"]+)"/g, (match, filepath) => {
    return `src="${assetUrl(filepath)}"`
  })
}
