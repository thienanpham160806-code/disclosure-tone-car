import { useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api, fmt, fmtSigned } from '../api'
import { useData } from '../hooks'
import { Card, Note, PageHeader, Segmented, Stat, Status } from '../components/ui'
import ToneResult from '../components/ToneResult'
import OcrFix from '../components/OcrFix'

const METHOD = {
  text: 'Lớp chữ của PDF', ocr: 'OCR (Tesseract)', llm_vision: 'OCR + AI chép lại trang chữ xấu',
  'ocr+llm_fix': 'OCR + AI sửa lỗi ký tự', manual: 'Trang xác định bằng tay',
}
const DEFAULT = { vn: ['MWG', 'MWG_2019'], us: ['AAPL', null] }   // [mã, văn bản mở sẵn]

export default function Explorer({ mkt, marketSwitch }) {
  const list = useData(() => api.documents(mkt), [mkt])
  const docs = useMemo(() => list.data || [], [list.data])
  const tickers = useMemo(() => [...new Set(docs.map((d) => d.ticker))].sort(), [docs])
  // lựa chọn của người dùng; giá trị hiệu lực được suy ra khi render (đổi thị trường → về mặc định)
  const [pick, setPick] = useState({ mkt, ticker: '', docId: '', section: 'main' })
  const own = pick.mkt === mkt
  const ticker = own && tickers.includes(pick.ticker) ? pick.ticker : tickers.includes(DEFAULT[mkt][0]) ? DEFAULT[mkt][0] : tickers[0] || ''
  const years = docs.filter((d) => d.ticker === ticker)
  const want = own && pick.docId ? pick.docId : DEFAULT[mkt][1]
  const docId = years.some((y) => y.doc_id === want) ? want : years[0]?.doc_id || ''
  const section = own ? pick.section : 'main'
  const setTicker = (t) => setPick({ mkt, ticker: t, docId: '', section: 'main' })
  const setDocId = (id) => setPick({ mkt, ticker, docId: id, section })
  const setSection = (sec) => setPick({ mkt, ticker, docId, section: sec })

  const doc = useData(() => (docId ? api.document(mkt, docId, section) : Promise.resolve(null)), [mkt, docId, section])
  const meta = doc.data?.meta

  return (
    <>
      <PageHeader eyebrow="Tra cứu" title="Xem từng văn bản được chấm tone như thế nào" right={marketSwitch}>
        Chọn công ty và năm. Mỗi từ được đếm đều được tô màu, kèm kết quả nghiên cứu sự kiện của chính văn bản đó.
      </PageHeader>

      <Status state={list}>
        <div className="filters">
          <label className="field">
            <span>Công ty</span>
            <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
              {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <div className="field">
            <span>Năm</span>
            <div className="year-pills">
              {years.map((y) => (
                <button key={y.doc_id} className={y.doc_id === docId ? 'on' : ''} onClick={() => setDocId(y.doc_id)}>{y.year}</button>
              ))}
            </div>
          </div>
          {mkt === 'us' && meta?.has_alt && (
            <div className="field">
              <span>Phần văn bản</span>
              <Segmented value={section} onChange={setSection} label="Phần văn bản" options={[
                { value: 'main', label: 'Toàn văn 10-K' }, { value: 'alt', label: 'MD&A' },
              ]} />
            </div>
          )}
          {doc.loading && <span className="inline-loading"><Loader2 size={16} className="spin" aria-hidden /> Đang chấm…</span>}
        </div>
      </Status>

      {meta && (
        <Card title={`${meta.ticker} · ${mkt === 'vn' ? 'Báo cáo thường niên' : '10-K nộp năm'} ${meta.year}`}
          subtitle={mkt === 'vn' ? `${METHOD[meta.method] || meta.method || ''}${meta.start_page ? ` · trang ${meta.start_page === meta.end_page ? fmt(meta.start_page, 0) : `${fmt(meta.start_page, 0)}–${fmt(meta.end_page, 0)}`} của PDF` : ''}` : `Mã hồ sơ SEC ${meta.doc_id}`}>
          <div className="stat-strip">
            <Stat label="Tone ròng (từ điển tài chính)" value={fmtSigned(meta.fin_net, 2)}
              note={`lạc quan hơn ${fmt(meta.net_pct_rank, 0)}% văn bản trong mẫu`} />
            <Stat label="Nhóm tone" value={meta.tone_grp ? meta.tone_grp.split(' ')[0] : '–'} note={meta.tone_grp ? meta.tone_grp.slice(3) : 'không có trong mẫu sự kiện'} />
            <Stat label="Ngày công bố (T = 0)" value={meta.event_date || '–'} note={meta.event_date ? 'dùng cho nghiên cứu sự kiện' : 'không có ngày hợp lệ'} />
            <Stat label="CAR[0, 3] của sự kiện" value={meta.car_0_3 == null ? '–' : `${fmtSigned(100 * meta.car_0_3, 2)}%`}
              tone={meta.car_0_3 == null ? undefined : meta.car_0_3 < 0 ? 'neg' : 'pos'} note="lợi suất bất thường T → T+3" />
          </div>
        </Card>
      )}

      <Status state={doc}>
        {doc.data && !doc.data.available && (
          <Note kind="warn">Máy này không có văn bản đã trích của {meta?.doc_id} (thư mục <code>data/{mkt}/interim/text</code> không đưa lên git).
            Các chỉ số phía trên vẫn đúng vì lấy từ dữ liệu đã xử lý. Muốn xem văn bản: chạy lại bước trích văn bản (HUONG_DAN_CHAY.md, Cách B).</Note>
        )}
        {doc.data?.available && doc.data.error && <Note kind="warn">{doc.data.error}</Note>}
        {doc.data?.available && doc.data.analysis && (
          <Card title="Văn bản và các từ được đếm">
            <ToneResult result={doc.data.analysis} />
          </Card>
        )}
        {mkt === 'vn' && doc.data?.available && docId && <OcrFix key={docId} docId={docId} />}
      </Status>
    </>
  )
}
