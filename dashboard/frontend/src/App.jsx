import { useEffect, useState } from 'react'
import { BarChart3, Database, FileSearch, Home, LineChart, MessageSquareText, PenLine } from 'lucide-react'
import { Segmented } from './components/ui'
import { applyTheme, initialTheme } from './hooks'
import Overview from './pages/Overview'
import Tone from './pages/Tone'
import Market from './pages/Market'
import Explorer from './pages/Explorer'
import TryIt from './pages/TryIt'
import Data from './pages/Data'

const PAGES = [
  { id: 'tong-quan', label: 'Tổng quan', hint: 'Câu hỏi & câu trả lời', icon: Home },
  { id: 'giong-dieu', label: 'Giọng điệu', hint: 'Mục tiêu 1–2', icon: MessageSquareText },
  { id: 'thi-truong', label: 'Phản ứng thị trường', hint: 'Mục tiêu 3', icon: LineChart },
  { id: 'tra-cuu', label: 'Tra cứu văn bản', hint: 'Từng công ty, từng năm', icon: FileSearch },
  { id: 'thu-cau', label: 'Thử một câu', hint: 'Demo trực tiếp', icon: PenLine },
  { id: 'du-lieu', label: 'Dữ liệu & chất lượng', hint: 'Mẫu, OCR, tầng AI', icon: Database },
]

const fromHash = () => {
  const [page, mkt] = window.location.hash.replace('#', '').split('/')
  return { page: PAGES.some((p) => p.id === page) ? page : 'tong-quan', mkt: mkt === 'us' ? 'us' : 'vn' }
}

export default function App() {
  const [{ page, mkt }, setRoute] = useState(fromHash)
  const [theme, setTheme] = useState(() => { const t = initialTheme(); applyTheme(t); return t })
  const changeTheme = (t) => { applyTheme(t); setTheme(t) }
  useEffect(() => {
    const on = () => setRoute(fromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = (p, m = mkt) => { window.location.hash = `${p}/${m}`; window.scrollTo(0, 0) }

  const marketSwitch = (
    <Segmented value={mkt} onChange={(m) => go(page, m)} label="Thị trường" options={[
      { value: 'vn', label: 'Việt Nam' }, { value: 'us', label: 'Mỹ' },
    ]} />
  )
  const props = { mkt, marketSwitch, go }
  const current = PAGES.find((p) => p.id === page)

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><BarChart3 size={20} aria-hidden /></span>
          <div>
            <div className="brand-title">Đồ án 05</div>
            <div className="brand-sub">Giọng điệu văn bản &amp; phản ứng giá</div>
          </div>
        </div>
        <nav className="nav" aria-label="Các trang">
          {PAGES.map(({ id, label, hint, icon: Icon }) => (
            <button key={id} className={`nav-item ${page === id ? 'on' : ''}`} onClick={() => go(id)} aria-current={page === id ? 'page' : undefined}>
              <Icon size={18} aria-hidden />
              <span className="nav-text"><span className="nav-label">{label}</span><span className="nav-hint">{hint}</span></span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="theme-pick">
            <span>Giao diện</span>
            <Segmented value={theme} onChange={changeTheme} label="Giao diện" options={[
              { value: 'auto', label: 'Tự động' }, { value: 'light', label: 'Sáng' }, { value: 'dark', label: 'Tối' },
            ]} />
          </div>
          <p className="sidebar-note">Số liệu đọc từ <code>outputs/</code>, cùng nguồn với RESULTS.md</p>
        </div>
      </aside>

      <main className="main" aria-label={current.label}>
        {page === 'tong-quan' && <Overview {...props} />}
        {page === 'giong-dieu' && <Tone {...props} />}
        {page === 'thi-truong' && <Market {...props} />}
        {page === 'tra-cuu' && <Explorer {...props} />}
        {page === 'thu-cau' && <TryIt {...props} />}
        {page === 'du-lieu' && <Data {...props} />}
      </main>
    </div>
  )
}
