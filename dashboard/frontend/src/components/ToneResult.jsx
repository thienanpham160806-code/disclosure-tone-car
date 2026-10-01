import { useMemo, useState } from 'react'
import { fmt, fmtSigned, fmtInt } from '../api'
import { Legend, Segmented } from './ui'

const PRIORITY = ['negative', 'positive', 'uncertainty', 'litigious']
const NAMES = { negative: 'Tiêu cực', positive: 'Tích cực', uncertainty: 'Bất định', litigious: 'Pháp lý' }

function mainCat(cats) {
  return PRIORITY.find((p) => cats.includes(p))
}

// Văn bản với các từ khớp từ điển được tô màu. mode: 'financial' | 'general' | 'mislabeled'
// hidden: các khoảng [đầu, cuối, nhãn] thu gọn trong "Bản đọc" (khối rác) – vị trí ký tự giữ nguyên như văn bản đã chấm.
function Highlighted({ text, spans, mode, hidden = [], reading }) {
  const parts = useMemo(() => {
    const out = []
    let pos = 0, h = 0
    const emit = (upto) => {                       // chữ thường từ pos → upto, chen các khối ẩn
      while (pos < upto) {
        while (h < hidden.length && hidden[h][1] <= pos) h++
        const hs = h < hidden.length ? hidden[h][0] : Infinity
        if (hs <= pos) {
          out.push(<span key={`h${h}`} className="hidden-run" title="Đã ẩn trong Bản đọc – vẫn nằm trong văn bản được chấm">⋯ đã ẩn {hidden[h][2]} ⋯</span>)
          pos = Math.max(pos, hidden[h][1]); h++
          continue
        }
        const stop = Math.min(upto, hs)
        out.push(text.slice(pos, stop)); pos = stop
      }
    }
    spans.forEach(([s, e, cats], i) => {
      if (s < pos) return
      emit(s)
      if (s < pos) return                            // từ nằm trong khối ẩn
      const cls = mode === 'mislabeled' ? 'hl-noise' : `hl-${mainCat(cats)}`
      const tip = mode === 'mislabeled' ? 'Từ điển tổng quát: tiêu cực · Từ điển tài chính: không' : cats.map((c) => NAMES[c] || c).join(', ')
      out.push(<mark key={i} className={cls} title={tip}>{text.slice(s, e)}</mark>)
      pos = e
    })
    emit(text.length)
    return out
  }, [text, spans, mode, hidden])
  return <div className={`doc-text ${reading ? 'doc-reading' : ''}`}>{parts}</div>
}

function DictColumn({ title, r, highlight }) {
  return (
    <div className={`dict-col ${highlight ? 'dict-col-on' : ''}`}>
      <div className="dict-name">{title}</div>
      <div className="dict-net">
        <span className="dict-net-label">Tone ròng</span>
        <span className="dict-net-value">{fmtSigned(r.net, 2)}</span>
      </div>
      <NetBar net={r.net} />
      <dl className="dict-counts">
        <div><dt><span className="dot dot-negative" />Tiêu cực</dt><dd>{fmtInt(r.counts.negative)} <small>({fmt(r.neg_pct, 2)}%)</small></dd></div>
        <div><dt><span className="dot dot-positive" />Tích cực</dt><dd>{fmtInt(r.counts.positive)} <small>({fmt(r.pos_pct, 2)}%)</small></dd></div>
        {r.counts.uncertainty > 0 && <div><dt><span className="dot dot-uncertainty" />Bất định</dt><dd>{fmtInt(r.counts.uncertainty)}</dd></div>}
        <div><dt>Số từ (mẫu số)</dt><dd>{fmtInt(r.n_words)}</dd></div>
      </dl>
      {['negative', 'positive'].map((k) => r.top[k]?.length ? (
        <div key={k} className="chips">
          <span className="chips-label">{NAMES[k]}:</span>
          {r.top[k].slice(0, 8).map(([w, n]) => <span key={w} className={`chip chip-${k}`}>{w}{n > 1 ? ` ×${n}` : ''}</span>)}
        </div>
      ) : null)}
    </div>
  )
}

// Thanh −1 … +1, điểm giữa 0 trung tính.
export function NetBar({ net }) {
  const pct = ((net + 1) / 2) * 100
  return (
    <div className="netbar" aria-hidden>
      <span className="netbar-mid" />
      <span className="netbar-dot" style={{ left: `${pct}%` }} />
      <span className="netbar-l">−1 bi quan</span>
      <span className="netbar-r">lạc quan +1</span>
    </div>
  )
}

export default function ToneResult({ result }) {
  const [mode, setMode] = useState('financial')
  const rd = result.readable
  const [view, setView] = useState(rd ? 'read' : 'raw')
  const reading = rd && view === 'read'
  const nMis = result.mislabeled.length
  const spans = mode === 'mislabeled' ? result.mislabeled.map(([s, e]) => [s, e, ['negative']])
    : result[mode].spans
  return (
    <div className="tone-result">
      <div className="dict-grid">
        <DictColumn title={`Từ điển tài chính · ${result.dict_names.financial}`} r={result.financial} highlight={mode === 'financial'} />
        <DictColumn title={`Từ điển tổng quát · ${result.dict_names.general}`} r={result.general} highlight={mode === 'general'} />
      </div>
      <div className={`mis-callout ${nMis ? '' : 'mis-none'}`}>
        <strong>{fmtInt(nMis)}</strong> chỗ từ điển tổng quát gắn nhãn <em>tiêu cực</em> nhưng từ điển tài chính thì không
        {nMis ? ' (bấm “Chỗ gán sai” để xem).' : '.'}
      </div>
      <div className="hl-toolbar">
        <span className="hl-toolbar-label">Tô màu theo</span>
        <Segmented value={mode} onChange={setMode} label="Chế độ tô màu" options={[
          { value: 'financial', label: 'Từ điển tài chính' },
          { value: 'general', label: 'Từ điển tổng quát' },
          { value: 'mislabeled', label: `Chỗ gán sai (${nMis})` },
        ]} />
      </div>
      {mode === 'mislabeled'
        ? <Legend items={[{ label: 'Tổng quát: tiêu cực · Tài chính: không', color: 'var(--noise)', box: true }]} />
        : <Legend items={[
          { label: 'Tiêu cực', color: 'var(--neg)', box: true },
          { label: 'Tích cực', color: 'var(--pos)', box: true },
          { label: 'Bất định', color: 'var(--unc)', box: true },
        ]} />}
      {rd && (
        <div className="hl-toolbar">
          <span className="hl-toolbar-label">Hiển thị</span>
          <Segmented value={view} onChange={setView} label="Cách hiển thị văn bản" options={[
            { value: 'read', label: 'Bản đọc' }, { value: 'raw', label: 'Văn bản gốc (đúng như khi chấm)' },
          ]} />
        </div>
      )}
      {reading && (
        <p className="muted-text read-note">
          <b>Bản đọc</b> chỉ đổi cách hiển thị: nối các dòng bị ngắt giữa câu
          {rd.hidden.length ? `, thu gọn ${fmtInt(rd.hidden.length)} khối không phải chữ (${result.lang === 'en' ? 'dữ liệu máy XBRL' : 'ký tự lẻ, số trang, mảnh hình do OCR'})` : ''}.
          Số đếm phía trên vẫn tính trên văn bản đầy đủ.
          {result.lang === 'vi' ? ' Chữ hiển thị đúng như văn bản đã chấm: nếu còn lỗi chính tả do OCR thì đó là lỗi thật trong dữ liệu, không được sửa riêng cho phần hiển thị.' : ' Văn bản 10-K được viết hoa toàn bộ theo quy ước đếm từ của Loughran–McDonald.'}
        </p>
      )}
      <Highlighted text={reading ? rd.text : result.text} spans={spans} mode={mode} hidden={reading ? rd.hidden : []} reading={reading} />
    </div>
  )
}
