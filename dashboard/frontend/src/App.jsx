import { Fragment, useEffect, useState } from 'react'
import { BarChart3, BookOpenText, FileSearch, PenLine } from 'lucide-react'
import { Segmented } from './components/ui'
import { applyTheme, initialTheme } from './hooks'
import Report from './pages/Report'
import Explorer from './pages/Explorer'
import TryIt from './pages/TryIt'

const PAGES = [
  { id: 'bao-cao', label: 'Báo cáo kết quả', hint: 'Đọc từ đầu đến cuối', icon: BookOpenText },
  { id: 'tra-cuu', label: 'Tra cứu văn bản', hint: 'Từng công ty, từng năm', icon: FileSearch },
  { id: 'thu-cau', label: 'Thử một câu', hint: 'Demo trực tiếp', icon: PenLine },
]
// đường dẫn của bản dashboard cũ → mục tương ứng trong báo cáo
const OLD = { 'tong-quan': 'tom-tat', 'giong-dieu': 'muc-2', 'thi-truong': 'muc-4', 'du-lieu': 'muc-1' }

const fromHash = () => {
  const [page, mkt, sec] = window.location.hash.replace('#', '').split('/')
  const m = mkt === 'us' ? 'us' : 'vn'
  if (OLD[page]) return { page: 'bao-cao', mkt: m, sec: OLD[page] }
  return { page: PAGES.some((p) => p.id === page) ? page : 'bao-cao', mkt: m, sec }
}

export default function App() {
  const [{ page, mkt, sec }, setRoute] = useState(fromHash)
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
          {PAGES.map(({ id, label, hint, icon: Icon }, i) => (
            <Fragment key={id}>
              {i === 1 && <div className="nav-group">Công cụ tương tác</div>}
              <button className={`nav-item ${page === id ? 'on' : ''}`} onClick={() => go(id)} aria-current={page === id ? 'page' : undefined}>
                <Icon size={18} aria-hidden />
                <span className="nav-text"><span className="nav-label">{label}</span><span className="nav-hint">{hint}</span></span>
              </button>
            </Fragment>
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
        {page === 'bao-cao' && <Report {...props} sec={sec} />}
        {page === 'tra-cuu' && <Explorer {...props} />}
        {page === 'thu-cau' && <TryIt {...props} />}
      </main>
    </div>
  )
}
