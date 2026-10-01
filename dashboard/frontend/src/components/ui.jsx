import { AlertTriangle, CheckCircle2, CircleSlash, Info, Loader2 } from 'lucide-react'

export function Card({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}

export function PageHeader({ eyebrow, title, children, right }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2 className="page-title">{title}</h2>
        {children && <p className="page-lead">{children}</p>}
      </div>
      {right && <div className="page-head-right">{right}</div>}
    </div>
  )
}

export function Stat({ label, value, unit, note, tone }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ? `tone-${tone}` : ''}`}>
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  )
}

// Kết luận thống kê: luôn có biểu tượng + chữ, không dựa vào màu.
export function Verdict({ stars, text }) {
  const sig = Boolean(stars)
  return (
    <span className={`verdict ${sig ? 'verdict-sig' : 'verdict-ns'}`}>
      {sig ? <CheckCircle2 size={14} aria-hidden /> : <CircleSlash size={14} aria-hidden />}
      {sig ? `Có ý nghĩa (${text})` : 'Không có ý nghĩa thống kê'}
    </span>
  )
}

export function Segmented({ value, onChange, options, label }) {
  return (
    <div className="segmented" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value}
          className={value === o.value ? 'on' : ''} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Note({ children, kind = 'info' }) {
  const Icon = kind === 'warn' ? AlertTriangle : Info
  return (
    <div className={`note note-${kind}`}>
      <Icon size={16} aria-hidden />
      <div>{children}</div>
    </div>
  )
}

export function Status({ state, children }) {
  if (state.error) return <Note kind="warn">Không tải được dữ liệu: {state.error.message}. Máy chủ (backend) đã chạy chưa? Nếu là bản online, thử tải lại trang sau 1 phút.</Note>
  if (!state.data) return (
    <div className="loading"><Loader2 size={18} className="spin" aria-hidden /> Đang tải… (bản online dùng máy chủ miễn phí, lần mở đầu tiên có thể mất khoảng 1 phút để máy chủ khởi động)</div>
  )
  return children
}

export function Legend({ items }) {
  return (
    <ul className="legend">
      {items.map((it) => (
        <li key={it.label}>
          <span className={`legend-mark ${it.dashed ? 'dashed' : ''} ${it.box ? 'box' : ''}`} style={{ '--c': it.color }} />
          {it.label}
        </li>
      ))}
    </ul>
  )
}
