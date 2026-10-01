import { useEffect, useState } from 'react'
import { Loader2, Play } from 'lucide-react'
import { api } from '../api'
import { Card, Note, PageHeader, Segmented } from '../components/ui'
import ToneResult from '../components/ToneResult'

const EXAMPLES = [
  { lang: 'vi', label: 'Ngân hàng khó khăn', text: 'Năm 2023 ngân hàng gặp nhiều khó khăn, nợ xấu tăng và lợi nhuận suy giảm; tuy vậy chúng tôi vẫn tăng trưởng bền vững nhờ mảng thương mại và bán lẻ.' },
  { lang: 'vi', label: 'Thư “tô hồng”', text: 'Kính thưa Quý cổ đông, năm qua Công ty đạt kết quả kinh doanh ấn tượng, doanh thu tăng trưởng mạnh mẽ, lợi nhuận vượt kế hoạch và tiếp tục giữ vững vị thế dẫn đầu thị trường.' },
  { lang: 'vi', label: 'Bẫy “tiền tệ”, “ngắn hạn”', text: 'Chính sách tiền tệ thắt chặt khiến chi phí vốn ngắn hạn tăng, nhưng Công ty vẫn duy trì hạn mức tín dụng xanh cho khách hàng.' },
  { lang: 'en', label: '10-K (tiếng Anh)', text: 'The company reported a net loss, higher tax expense and may face adverse litigation. Capital expenditures and other costs increased.' },
]

export default function TryIt() {
  const [lang, setLang] = useState('vi')
  const [text, setText] = useState(EXAMPLES[0].text)
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const run = async (t = text, l = lang) => {
    if (!t.trim()) return
    setBusy(true); setErr(null)
    try { setRes(await api.analyze(t, l)) } catch (e) { setErr(e) }
    setBusy(false)
  }

  // chấm sẵn câu mẫu đầu tiên khi mở trang
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run() }, [])

  return (
    <>
      <PageHeader eyebrow="Thử trực tiếp" title="Gõ một câu bất kỳ, xem hai bộ từ điển chấm khác nhau ra sao">
        Dùng đúng bộ đếm từ của đồ án. Phù hợp để demo Mục tiêu 2: từ điển tổng quát hiểu sai văn bản tài chính.
      </PageHeader>

      <Card>
        <div className="examples">
          <span className="examples-label">Câu mẫu:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex.label} className="chip-btn" onClick={() => { setLang(ex.lang); setText(ex.text); run(ex.text, ex.lang) }}>{ex.label}</button>
          ))}
        </div>
        <textarea className="textarea" value={text} onChange={(e) => setText(e.target.value)} rows={4}
          placeholder="Nhập câu hoặc đoạn văn…" onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) run() }} />
        <div className="toolbar">
          <Segmented value={lang} onChange={setLang} label="Ngôn ngữ" options={[
            { value: 'vi', label: 'Tiếng Việt · fin_vn vs VietSentiWordNet' },
            { value: 'en', label: 'Tiếng Anh · Loughran–McDonald vs Harvard GI' },
          ]} />
          <button className="btn" onClick={() => run()} disabled={busy || !text.trim()}>
            {busy ? <Loader2 size={16} className="spin" aria-hidden /> : <Play size={16} aria-hidden />}
            Chấm giọng điệu <kbd>Ctrl + Enter</kbd>
          </button>
        </div>
      </Card>

      {err && <Note kind="warn">{err.message}</Note>}
      {res && <Card title="Kết quả"><ToneResult result={res} /></Card>}
    </>
  )
}
