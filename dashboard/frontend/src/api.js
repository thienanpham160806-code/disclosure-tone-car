// Gọi API backend.
//  • Máy cá nhân: Vite chuyển /api → 127.0.0.1:8000 (vite.config.js); bản build chạy cùng origin với FastAPI.
//  • Vercel: đặt biến môi trường VITE_API_BASE = https://<tên-dịch-vụ>.onrender.com/api (xem DEPLOY.md).
// Chấp nhận cả địa chỉ thiếu đuôi /api (vd https://x.onrender.com) – tự thêm cho đúng.
const BASE = ((b) => (/\/api$/.test(b) ? b : `${b}/api`))((import.meta.env.VITE_API_BASE || '/api').replace(/\/+$/, ''))

async function req(path, opts) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let msg = `Lỗi ${res.status}`
    try { msg = (await res.json()).detail || msg } catch { /* giữ thông báo mặc định */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  overview: () => req('/overview'),
  toneByYear: (m) => req(`/${m}/tone_by_year`),
  misclassified: (m) => req(`/${m}/misclassified`),
  caar: (m) => req(`/${m}/caar`),
  carByTone: (m) => req(`/${m}/car_by_tone`),
  coefficients: (m) => req(`/${m}/coefficients`),
  documents: (m) => req(`/${m}/documents`),
  document: (m, docId, section = 'main') =>
    req(`/${m}/document?doc_id=${encodeURIComponent(docId)}&section=${section}`),
  analyze: (text, lang) =>
    req('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, lang }) }),
  quality: () => req('/quality'),
  status: () => req('/status'),
  news: (docId) => req(`/vn/news?doc_id=${encodeURIComponent(docId)}`),
  letterPages: (docId) => req(`/vn/pages?doc_id=${encodeURIComponent(docId)}`),
  pageImage: (docId, page) => `${BASE}/vn/page_image?doc_id=${encodeURIComponent(docId)}&page=${page}`,
  ocrFix: (docId, page, mode) =>
    req('/vn/ocr_fix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ doc_id: docId, page, mode }) }),
}

// ---------------------------------------------------------------- định dạng số kiểu Việt Nam
const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d })
export const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? '–' : nf(d).format(v))
export const fmtSigned = (v, d = 2) => (v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '') + nf(d).format(Math.abs(v)))
export const fmtInt = (v) => (v == null ? '–' : new Intl.NumberFormat('vi-VN').format(v))
