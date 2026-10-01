import { useEffect, useState } from 'react'

// Màu biểu đồ lấy từ token CSS (:root) để sáng/tối dùng chung một nguồn; cập nhật khi người dùng đổi chế độ hệ thống.
const KEYS = ['--neg', '--pos', '--neutral', '--noise', '--accent', '--text', '--text-2', '--muted', '--grid', '--surface', '--band']

function read() {
  const cs = getComputedStyle(document.documentElement)
  return Object.fromEntries(KEYS.map((k) => [k.slice(2), cs.getPropertyValue(k).trim()]))
}

export function useChartColors() {
  const [c, setC] = useState(read)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const on = () => setC(read())
    mq.addEventListener('change', on)
    window.addEventListener('themechange', on)
    return () => { mq.removeEventListener('change', on); window.removeEventListener('themechange', on) }
  }, [])
  return c
}

// Tải dữ liệu theo khóa; giữ dữ liệu cũ khi đang tải lại (không nháy khung trống).
export function useData(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error) => alive && setState((s) => ({ ...s, error, loading: false })),
    )
    return () => { alive = false }
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- deps do nơi gọi truyền vào
  }, deps)
  return state
}

// Chế độ giao diện: 'auto' | 'light' | 'dark'. Ưu tiên ?theme= trên URL, rồi lựa chọn đã lưu (nếu trình duyệt cho lưu).
export function initialTheme() {
  const q = new URLSearchParams(window.location.search).get('theme')
  if (['auto', 'light', 'dark'].includes(q)) return q
  try { return localStorage.getItem('theme') || 'auto' } catch { return 'auto' }
}

export function applyTheme(t) {
  const el = document.documentElement
  if (t === 'auto') delete el.dataset.theme
  else el.dataset.theme = t
  try { localStorage.setItem('theme', t) } catch { /* không lưu được thì thôi */ }
  window.dispatchEvent(new Event('themechange'))
}
