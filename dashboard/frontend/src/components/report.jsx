// Khối dựng trang Báo cáo: mục đánh số, hình/bảng có chú thích + "cách đọc" + nguồn file, khung lưu ý, mục lục.
import { scrollToId } from '../hooks'
import { AlertTriangle, BookOpen, Eye, Lightbulb } from 'lucide-react'

export function Section({ id, no, title, kicker, children }) {
  return (
    <section id={id} className="rsec" aria-labelledby={`${id}-t`}>
      <header className="rsec-head">
        {no && <span className="rsec-no">{no}</span>}
        <h2 className="rsec-title" id={`${id}-t`}>{title}</h2>
        {kicker && <span className="rsec-kicker">{kicker}</span>}
      </header>
      {children}
    </section>
  )
}

export function Sub({ id, no, children }) {
  return <h3 className="rsub" id={id}>{no && <span className="rsub-no">{no}</span>}{children}</h3>
}

export function P({ children }) {
  return <p className="prose">{children}</p>
}

// số nổi bật trong đoạn văn
export function N({ children }) {
  return <span className="num-hl">{children}</span>
}

// Hình / Bảng: tiêu đề đánh số, nội dung, "Cách đọc", chú thích và tệp nguồn trong outputs/
export function Figure({ kind = 'Hình', no, title, sub, read, caption, source, children }) {
  return (
    <figure className="rfig card">
      <figcaption className="rfig-head">
        <span className="rfig-label">{kind} {no}</span>
        <span className="rfig-title">{title}</span>
        {sub && <span className="rfig-sub">{sub}</span>}
      </figcaption>
      {children}
      {read && <div className="rfig-read"><Eye size={16} aria-hidden /><div><b>Cách đọc:</b> {read}</div></div>}
      {caption && <p className="rfig-cap">{caption}</p>}
      {source && <p className="rfig-src">Nguồn số liệu: {[].concat(source).map((s, i) => <span key={s}>{i ? ', ' : ''}<code>{s}</code></span>)}</p>}
    </figure>
  )
}

const CALLOUT = { key: Lightbulb, warn: AlertTriangle, method: BookOpen }

export function Callout({ kind = 'key', title, children }) {
  const Icon = CALLOUT[kind] || Lightbulb
  return (
    <aside className={`callout callout-${kind}`}>
      <Icon size={18} aria-hidden />
      <div className="callout-body">
        {title && <div className="callout-title">{title}</div>}
        {children}
      </div>
    </aside>
  )
}

// plain: bỏ chấm màu thị trường khi hình đã dùng màu cho ý nghĩa khác (tránh nhầm)
export function MarketLabel({ mkt, plain }) {
  return <div className="mkt-label">{!plain && <span className="mkt-dot" style={{ '--c': `var(--${mkt})` }} />}{mkt === 'vn' ? 'Việt Nam' : 'Mỹ'}</div>
}

export function Kpi({ value, label, tone }) {
  return (
    <div className="kpi">
      <div className={`kpi-value ${tone ? `tone-${tone}` : ''}`}>{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  )
}

export function Toc({ items, active, children }) {
  return (
    <nav className="toc" aria-label="Mục lục báo cáo">
      <div className="toc-title">Mục lục</div>
      <ol>
        {items.map((it) => (
          <li key={it.id}>
            <button className={active === it.id ? 'on' : ''} onClick={() => scrollToId(it.id)} aria-current={active === it.id ? 'true' : undefined}>
              <span className="toc-no">{it.no}</span><span>{it.label}</span>
            </button>
          </li>
        ))}
      </ol>
      {children && <div className="toc-actions">{children}</div>}
    </nav>
  )
}

export function TocMobile({ items }) {
  return (
    <details className="toc-mobile">
      <summary>Mục lục báo cáo</summary>
      <ol>
        {items.map((it) => (
          <li key={it.id}><a href={`#bao-cao`} onClick={(e) => { e.preventDefault(); scrollToId(it.id) }}>{it.no} {it.label}</a></li>
        ))}
      </ol>
    </details>
  )
}
