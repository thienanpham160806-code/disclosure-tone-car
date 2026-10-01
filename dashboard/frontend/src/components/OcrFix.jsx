import { useState } from 'react'
import { CheckCircle2, CircleSlash, Loader2, Sparkles } from 'lucide-react'
import { api, fmt, fmtInt } from '../api'
import { useData } from '../hooks'
import { Card, Legend, Note, Segmented, Status } from './ui'

const SOURCE = { text: 'Lớp chữ của PDF', ocr: 'OCR (Tesseract)', text_ocr_fail: 'Không OCR được' }

function QualityBadge({ q, threshold }) {
  if (q == null) return <span className="muted-text">–</span>
  const low = q < threshold
  return <span className={`qbadge ${low ? 'qbadge-low' : ''}`}>{fmt(q, 2)}{low ? ' · thấp' : ''}</span>
}

function DiffText({ parts, kind }) {
  return (
    <div className="diff-text">
      {parts.map(([t, k], i) => (k === 'same' ? <span key={i}>{t}</span> : <mark key={i} className={`diff-${k}`}>{t}</mark>))}
    </div>
  )
}

function Result({ res }) {
  const [view, setView] = useState('ai')
  const nChanged = res.ai.filter(([, k]) => k === 'ins').reduce((s, [t]) => s + t.trim().split(/\s+/).filter(Boolean).length, 0)
  return (
    <div className="ocr-result">
      <div className={`ocr-verdict ${res.accepted ? 'ok' : 'no'}`}>
        {res.accepted ? <CheckCircle2 size={18} aria-hidden /> : <CircleSlash size={18} aria-hidden />}
        <div>
          <b>{res.reason}</b>
          <div className="ocr-verdict-sub">
            Chất lượng chữ {fmt(res.q_before, 2)} → {fmt(res.q_ai, 2)} · độ giống bản cũ {fmt(100 * res.similarity, 0)}% ·
            {' '}{fmtInt(nChanged)} từ khác · {res.provider} / {res.model}{res.cached ? ' · lấy từ cache (không tốn lượt gọi)' : ''}
          </div>
        </div>
      </div>
      {res.note && <Note kind="warn">{res.note}</Note>}
      {res.is_letter_page === false && <Note>AI nhận định trang này không thuộc thư của ban lãnh đạo – chỉ để tham khảo, không tự loại trang.</Note>}
      <div className="hl-toolbar">
        <Segmented value={view} onChange={setView} label="Bản xem" options={[
          { value: 'ai', label: 'Bản AI chép lại' }, { value: 'before', label: `Bản hiện tại (${SOURCE[res.source] || res.source})` },
          { value: 'both', label: 'Đặt cạnh nhau' },
        ]} />
      </div>
      <Legend items={[
        { label: 'Có trong bản AI, khác bản cũ', color: 'var(--pos)', box: true },
        { label: 'Có trong bản cũ, AI không giữ', color: 'var(--neg)', box: true },
      ]} />
      {view === 'both' ? (
        <div className="diff-grid">
          <div><div className="diff-head">Bản hiện tại</div><DiffText parts={res.before} /></div>
          <div><div className="diff-head">Bản AI</div><DiffText parts={res.ai} /></div>
        </div>
      ) : <DiffText parts={view === 'ai' ? res.ai : res.before} />}
    </div>
  )
}

export default function OcrFix({ docId }) {
  const info = useData(() => api.letterPages(docId), [docId])
  const [sel, setSel] = useState(null)               // trang đang xem
  const [mode, setMode] = useState('vision')
  const [runs, setRuns] = useState({})                // key `${page}/${mode}` → kết quả | lỗi
  const [busy, setBusy] = useState(null)
  const d = info.data
  const page = d && (d.pages.find((p) => p.page === sel) || d.pages.find((p) => p.q_before != null && p.q_before < d.threshold) || d.pages[0])
  const key = page ? `${docId}/${page.page}/${mode}` : null
  const run = runs[key]

  const go = async () => {
    setBusy(key)
    try { const res = await api.ocrFix(docId, page.page, mode); setRuns((r) => ({ ...r, [key]: { res } })) }
    catch (e) { setRuns((r) => ({ ...r, [key]: { err: e.message } })) }
    setBusy(null)
  }

  return (
    <Card title={<span className="title-icon"><Sparkles size={18} aria-hidden /> Sửa OCR bằng AI</span>}
      subtitle="AI (Gemini, temperature 0) chép nguyên văn ảnh trang – chỉ để xem và kiểm tra; không ghi đè dữ liệu. Pipeline chỉ gửi AI các trang có điểm chất lượng chữ thấp.">
      <Status state={info}>
        {d && (
          <>
            {!d.pdf_available && <Note>Bản đang xem không có PDF gốc của báo cáo (data/vn/raw, khoảng 11 GB, không đưa lên GitHub), nên không xem được ảnh trang và không chạy được AI. Bảng dưới vẫn là kết quả thật của lần chạy pipeline. Muốn chạy AI: mở dashboard trên máy có dữ liệu (<code>dashboardun.ps1</code>).</Note>}
            {d.pdf_available && !d.has_key && <Note kind="warn">Chưa có API key nên chưa chạy được AI. Tạo file <code>.env</code> ở thư mục gốc repo với dòng <code>GEMINI_API_KEY=...</code> (lấy miễn phí tại aistudio.google.com/apikey), rồi chạy lại <code>dashboard\run.ps1</code>. Bảng dưới vẫn hiện kết quả của lần chạy pipeline.</Note>}
            <table className="table table-click">
              <thead><tr><th>Trang PDF</th><th>Nguồn chữ</th><th>Điểm chất lượng</th><th>Lần chạy pipeline</th></tr></thead>
              <tbody>
                {d.pages.map((p) => (
                  <tr key={p.page} className={page?.page === p.page ? 'row-on' : ''} onClick={() => setSel(p.page)}>
                    <td>Trang {p.page}</td>
                    <td>{SOURCE[p.source] || p.source || '–'}</td>
                    <td><QualityBadge q={p.q_before} threshold={d.threshold} /></td>
                    <td className="muted-cell">{p.sent ? (p.reason || p.decision) : p.q_before != null && p.q_before >= d.threshold ? 'Không cần gửi AI (chữ đã tốt)' : '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="chart-foot">Điểm chất lượng = tỷ lệ âm tiết tiếng Việt hợp lệ, ký tự rác, từ vỡ (0–1). Dưới {fmt(d.threshold, 2)} là “thấp” và được gửi AI khi chạy <code>v03_extract_letter.py --llm</code>.</p>

            {page && d.pdf_available && (
              <div className="ocr-work">
                <figure className="ocr-image">
                  <img src={api.pageImage(docId, page.page)} alt={`Ảnh trang ${page.page} của PDF`} loading="lazy" />
                  <figcaption>Ảnh gốc trang {page.page}</figcaption>
                </figure>
                <div className="ocr-side">
                  <div className="toolbar">
                    <Segmented value={mode} onChange={setMode} label="Chế độ AI" options={[
                      { value: 'vision', label: 'Đọc ảnh trang (mặc định)' }, { value: 'text_fix', label: 'Chỉ sửa lỗi ký tự' },
                    ]} />
                    <button className="btn" onClick={go} disabled={!d.has_key || busy === key}>
                      {busy === key ? <Loader2 size={16} className="spin" aria-hidden /> : <Sparkles size={16} aria-hidden />}
                      {busy === key ? 'Đang chạy… (OCR + AI, ~10–30 giây)' : `Chạy AI cho trang ${page.page}`}
                    </button>
                  </div>
                  {run?.err && <Note kind="warn">{run.err}</Note>}
                  {run?.res && <Result res={run.res} />}
                  {!run && <p className="muted-text">Bấm “Chạy AI” để so sánh bản chữ hiện tại của trang với bản AI chép lại từ ảnh. Trang pipeline đã gửi trước đó sẽ lấy ngay từ cache.</p>}
                </div>
              </div>
            )}
          </>
        )}
      </Status>
    </Card>
  )
}
