// Trang Báo cáo: trình bày RESULTS.md dưới dạng trực quan – đọc từ trên xuống như một bài báo cáo, có mục đánh số,
// hình/bảng có "cách đọc", chú thích, nguồn file. MỌI con số lấy từ /api/report (đọc outputs/), không gõ tay.
import { useEffect } from 'react'
import { ArrowRight, CalendarDays, CheckCircle2, CircleSlash, Database, FileText, Printer } from 'lucide-react'
import { api, fmt, fmtInt, fmtSigned } from '../api'
import { scrollToId, useActiveSection, useChartColors, useData } from '../hooks'
import { Card, Status, Verdict } from '../components/ui'
import { CaarChart, CoefPlot, MarketYearLines, MisclassifiedBars, MisclassifiedLegend, NewsCoverageChart, SimpleBars } from '../components/charts'
import { Callout, Figure, Kpi, MarketLabel, N, P, Section, Sub, Toc, TocMobile } from '../components/report'

const TOC = [
  { id: 'tom-tat', no: '★', label: 'Tóm tắt' },
  { id: 'muc-1', no: '1', label: 'Dữ liệu và mẫu' },
  { id: 'muc-2', no: '2', label: 'Đo giọng điệu' },
  { id: 'muc-3', no: '3', label: 'Từ điển tổng quát sai lệch' },
  { id: 'muc-4', no: '4', label: 'Thị trường có phản ứng?' },
  { id: 'muc-5', no: '5', label: 'Chất lượng văn bản VN' },
  { id: 'muc-6', no: '6', label: 'Tin tức quanh ngày công bố' },
  { id: 'muc-7', no: '7', label: 'So sánh Mỹ – Việt Nam' },
  { id: 'muc-8', no: '8', label: 'Hạn chế' },
  { id: 'muc-9', no: '9', label: 'Hàm ý' },
  { id: 'phu-luc', no: 'A', label: 'Phụ lục: thuật ngữ, kiểm định, tái lập' },
]

const OCR_NAME = { tesseract: 'Tesseract (OCR thuần)', llm_fix: 'OCR + AI sửa lỗi ký tự', llm_vision: 'AI đọc ảnh trang (phương án dùng)' }
const TOPIC_NAME = {
  dhdcd: 'Đại hội đồng cổ đông', bctn: 'Báo cáo thường niên', kqkd: 'Kết quả kinh doanh / BCTC', gd_noi_bo: 'GD cổ đông lớn / nội bộ',
  nhan_su: 'Nhân sự', co_tuc: 'Cổ tức', chung_quyen: 'Chứng quyền',
}

// ---------------------------------------------------------------- tiện ích đọc số
const p3 = (p) => (p == null ? '–' : p < 0.001 ? '< 0,001' : fmt(p, p < 0.01 ? 4 : p < 0.1 ? 3 : 2))
const pick = (obj, prefix) => { const k = Object.keys(obj || {}).find((x) => x.startsWith(prefix)); return k ? obj[k] : null }
const fun = (m, prefix) => m.funnel.find((r) => r.buoc.trim().startsWith(prefix))?.so_van_ban
const carRow = (m, w) => m.car_tests.find((r) => r.window === w)
const grp = (m, key) => m.car_by_tone.find((r) => r.tone_grp.startsWith(key))
const coefOf = (m, label) => m.coefficients.find((r) => r.label === label)
const cell = (c) => (c ? `${fmtSigned(c.coef, 4)}${c.stars || ''} (${fmt(c.se, 4)})` : '–')

function SigPill({ p, alpha = 0.05 }) {
  if (p == null) return null
  return p < alpha ? <span className="pill pill-sig">có ý nghĩa</span> : <span className="pill">không có ý nghĩa</span>
}

// ---------------------------------------------------------------- tóm tắt: câu trả lời cho từng thị trường
function MarketAnswer({ mkt, d }) {
  const m = d.main
  return (
    <Card className="answer">
      <div className="answer-head">
        <div>
          <MarketLabel mkt={mkt} />
          <p className="answer-doc">{mkt === 'vn' ? 'Thư của ban lãnh đạo trong báo cáo thường niên, VN30 + VN100' : 'Báo cáo 10-K của các công ty vốn hóa lớn'}</p>
        </div>
        <Verdict stars={m.stars} text={m.sig} />
      </div>
      <div className="answer-big">
        <span className={`big-number ${m.stars ? 'tone-neg' : ''}`}>{fmtSigned(m.pp_per_sd, 2)}</span>
        <span className="big-unit">điểm %</span>
      </div>
      <p className="answer-explain">
        Thay đổi của <b>CAR[0, 3]</b> khi tone tiêu cực tăng <b>1 độ lệch chuẩn</b> · sai số chuẩn {fmt(100 * m.se, 2)} điểm % · N = {fmtInt(d.n_reg)}
      </p>
    </Card>
  )
}

export default function Report({ go, sec }) {
  const st = useData(api.report, [])
  const active = useActiveSection(TOC.map((t) => t.id))
  useEffect(() => { if (st.data && sec) setTimeout(() => scrollToId(sec), 50) }, [st.data, sec])
  return (
    <div className="report">
      <article className="report-body">
        <header className="hero">
          <div className="eyebrow">Báo cáo kết quả · Đồ án 05 · Phân tích văn bản công bố thông tin</div>
          <h1 className="hero-title">Giọng điệu văn bản công bố có làm giá cổ phiếu phản ứng không?</h1>
          <p className="hero-q">
            Chúng tôi chấm “giọng điệu” (tone) của báo cáo 10-K ở Mỹ và thư của ban lãnh đạo trong báo cáo thường niên ở Việt Nam
            bằng từ điển tài chính, rồi kiểm tra xem tone có giải thích được <b>lợi suất bất thường tích lũy CAR[T, T+3]</b> quanh ngày công bố hay không.
          </p>
          <div className="hero-meta">
            <span><Database size={14} aria-hidden /> Mọi con số đọc trực tiếp từ <code>outputs/</code> – cùng nguồn với RESULTS.md</span>
            <span><CalendarDays size={14} aria-hidden /> Mỹ: 10-K nộp 2015–2024 · VN: BCTN 2016–2025</span>
            <span><FileText size={14} aria-hidden /> Đọc khoảng 15 phút</span>
          </div>
          <TocMobile items={TOC} />
        </header>
        <Status state={st}>{st.data && <Body d={st.data} go={go} />}</Status>
      </article>
      <Toc items={TOC} active={active}>
        <button className="btn-ghost no-print" onClick={() => window.print()}><Printer size={15} aria-hidden /> In / lưu PDF</button>
        <button className="btn-ghost no-print" onClick={() => go('tra-cuu')}>Tra cứu từng văn bản <ArrowRight size={14} aria-hidden /></button>
      </Toc>
    </div>
  )
}

function Body({ d, go }) {
  const c = useChartColors()
  const V = d.markets.vn, U = d.markets.us, X = d.vn_extra, O = d.overview
  // ---- số dùng nhiều lần
  const nWin = V.coefficients.filter((r) => !r.placebo).length
  const alpha = 0.05 / nWin
  const fx = X.goc_fix?.length ? X.goc_fix : X.page_fix          // bảng trước/sau mới nhất (#65), dự phòng bảng #55
  const pf = (mo) => fx.find((r) => r.mo_hinh === mo)
  const p05 = pf('CAR[0,5]')?.p_sau, p010 = pf('CAR[0,10]')?.p_sau, pMain = pf('M2 fin_neg')?.p_sau, pPlc = pf('Placebo −60 phiên')?.p_sau
  const pass05 = p05 != null && p05 < alpha
  const genStars = U.m4.gen_neg_z?.stars || ''
  const vnFound = fun(V, 'Tìm được'), vnNotFound = fun(V, 'không tìm thấy'), vnPdf = fun(V, 'Mã–năm có BCTN')
  const vnT0 = fun(V, 'Có ngày sự kiện'), vnCar = fun(V, 'Có CAR (đủ'), vnCar03 = fun(V, 'Có CAR[0,3]')
  const vnManual = vnPdf - vnFound - vnNotFound
  const usN = fun(U, 'Hồ sơ 10-K')
  const tdV = V.tone_desc, tdU = U.tone_desc
  const yv = V.tone_by_year, yu = U.tone_by_year
  const vPeak = yv.reduce((a, b) => (b.fin_neg > a.fin_neg ? b : a)), vLow = yv.reduce((a, b) => (b.fin_neg < a.fin_neg ? b : a))
  const uLow = yu.reduce((a, b) => (b.fin_neg < a.fin_neg ? b : a)), uLast = yu[yu.length - 1]
  const car03V = carRow(V, 'CAR[0,3]'), car03U = carRow(U, 'CAR[0,3]')
  const car05V = carRow(V, 'CAR[0,5]'), car010V = carRow(V, 'CAR[0,10]'), plV = carRow(V, 'PLACEBO CAR[0,3]'), plU = carRow(U, 'PLACEBO CAR[0,3]')
  const sdV = V.diag.CAR_0_3_do_lech_chuan_pct, sdU = U.diag.CAR_0_3_do_lech_chuan_pct
  const news = X.news
  const nEv = news['Sự kiện (BCTN có T = 0 và CAR)']
  const gapMonths = String(news['Tháng kho tin CafeF bị hổng (< 25% trung vị)'] || '').split(', ').filter(Boolean)
  const crawlMonth = String(news['Thời điểm thu thập'] || '').slice(0, 7)
  const llm = X.llm
  const ocr = [...X.ocr_eval].sort((a, b) => b.cer - a.cer)
  const ocrOf = (m) => X.ocr_eval.find((r) => r.method === m)
  const toneDev = (m) => X.ocr_tone.find((r) => r.method === m)?.mae_fin_net
  const vifMax = (a) => Math.max(...Object.entries(a).filter(([k]) => k.startsWith('VIF')).map(([, v]) => v))
  const eo = U.earnings

  return (
    <>
      {/* ======================================================= TÓM TẮT */}
      <Section id="tom-tat" title="Tóm tắt" kicker="Câu trả lời ngắn">
        <div className="grid-2">
          <MarketAnswer mkt="vn" d={O.vn} />
          <MarketAnswer mkt="us" d={O.us} />
        </div>
        <Callout kind="key" title="Ba điều cần nhớ">
          <ul>
            <li><b>Mỹ:</b> không có bằng chứng giọng điệu 10-K mang thông tin cho giá. Hệ số {fmtSigned(O.us.main.pp_per_sd, 2)} điểm % trên 1 độ lệch chuẩn,
              không có ý nghĩa; kết luận giữ nguyên trong mọi phép kiểm tra độ vững (MD&amp;A, tf-idf, FinBERT, bỏ 10-K trùng KQKD).</li>
            <li><b>Việt Nam:</b> ở cửa sổ chính [0, 3] hệ số đúng dấu kỳ vọng ({fmtSigned(O.vn.main.pp_per_sd, 2)} điểm %) nhưng không có ý nghĩa (p = {p3(pMain)}).
              Ở [0, 5] hệ số có ý nghĩa ({fmtSigned(O.vn.car05.pp_per_sd, 2)} điểm %, p = {p3(p05)}) – gợi ý thị trường phản ứng chậm –
              {pass05
                ? <> và <b>qua</b> hiệu chỉnh Bonferroni cho {nWin} cửa sổ (ngưỡng {fmt(alpha, 4)}); tuy vậy p đã dao động quanh ngưỡng qua các bước làm sạch dữ liệu và các phân tích bổ sung đăng ký trước không xác nhận thêm, nên vẫn là bằng chứng chưa vững.</>
                : <> nhưng <b>không qua</b> hiệu chỉnh Bonferroni cho {nWin} cửa sổ (ngưỡng {fmt(alpha, 4)}), nên chỉ là bằng chứng yếu.</>}</li>
            <li><b>Từ điển tổng quát dùng sai chỗ:</b> {fmt(U.noise_pct, 1)}% (Harvard GI, Mỹ) và {fmt(V.noise_pct, 1)}% (VietSentiWordNet, VN) số lần
              gắn nhãn “tiêu cực” rơi vào từ không hề tiêu cực trong tài chính – như TAX, COST hay “thương” trong “thương mại”.</li>
          </ul>
        </Callout>
        <P>
          Báo cáo đi theo ba mục tiêu của đồ án: <b>(1)</b> biến văn bản thành biến định lượng (mục 2), <b>(2)</b> chỉ ra vì sao từ điển tổng quát
          sai lệch trong ngữ cảnh tài chính (mục 3), <b>(3)</b> kiểm tra thị trường có phản ứng với giọng điệu không (mục 4). Các mục 5–6 kiểm tra
          độ tin cậy của dữ liệu Việt Nam; mục 7–9 so sánh hai thị trường, nêu hạn chế và hàm ý.
        </P>
      </Section>

      {/* ======================================================= 1. DỮ LIỆU */}
      <Section id="muc-1" no="1" title="Dữ liệu và mẫu nghiên cứu" kicker="Từ danh sách công ty đến hồi quy">
        <P>
          <b>Mỹ:</b> {fmtInt(fun(U, 'Công ty'))} công ty vốn hóa lớn, toàn bộ <N>{fmtInt(usN)}</N> hồ sơ 10-K nộp 2015–2024 tải từ SEC EDGAR; giá từ yfinance,
          vốn hóa và B/M từ SEC XBRL. <b>Việt Nam:</b> {fmtInt(fun(V, 'Mã VN30'))} mã thuộc rổ VN30 + VN100; báo cáo thường niên (BCTN) dạng PDF
          và giá điều chỉnh lấy từ CafeF. Từ mỗi BCTN, chúng tôi trích riêng phần <b>thư / thông điệp của ban lãnh đạo</b> – nơi lãnh đạo trực tiếp
          nói với cổ đông – thay vì cả báo cáo dài hàng trăm trang.
        </P>
        <Figure no="1" title="Phễu mẫu: còn lại bao nhiêu văn bản sau mỗi bước lọc"
          read="Mỗi thanh là số văn bản còn lại sau bước lọc ghi bên trái; dòng thụt vào là phần bị loại ở bước ngay trên."
          source={['outputs/vn/sample_funnel.csv', 'outputs/us/sample_funnel.csv']}>
          <div className="grid-2">
            <div><MarketLabel mkt="vn" /><SimpleBars color={c.vn} items={V.funnel.map((r) => ({ label: r.buoc.trim(), value: r.so_van_ban, indent: r.buoc.startsWith('  ') }))} /></div>
            <div><MarketLabel mkt="us" /><SimpleBars color={c.us} items={U.funnel.map((r) => ({ label: r.buoc.trim(), value: r.so_van_ban, indent: r.buoc.startsWith('  ') }))} /></div>
          </div>
        </Figure>
        <Callout kind="method" title="Vì sao có mã có điểm giọng điệu nhưng không có CAR hay tin tức?">
          <p>Mỗi văn bản phải qua lần lượt ba cửa; rơi ở cửa nào thì thiếu từ đó trở đi:</p>
          <ul>
            <li><b>Không có thư lãnh đạo → không có tone:</b> {fmtInt(vnNotFound)}/{fmtInt(vnPdf)} BCTN không tìm thấy thư (nhiều BCTN lập theo mẫu biểu không có thư,
              hoặc thư là trang thiết kế dạng ảnh), {fmtInt(vnManual)} bị loại sau khi mở PDF kiểm tra tay. Còn <N>{fmtInt(vnFound)}</N> thư có tone.</li>
            <li><b>Không có ngày công bố → không có CAR:</b> {fmtInt(vnFound - vnT0)} thư không xác định được ngày công bố (PDF thiếu ngày sửa đổi hợp lệ).</li>
            <li><b>Không đủ lịch sử giá → không có CAR:</b> {fmtInt(vnT0 - vnCar)} sự kiện thiếu 80 phiên giao dịch trong cửa sổ ước lượng – phần lớn là mã mới lên sàn
              (TCB, MSB, TPB, VPB, HDB, SSB, OCB…) hoặc cổ phiếu giá đứng im nhiều phiên. {fmtInt(vnCar - vnCar03)} sự kiện thiếu giá ngay trong [0, 3].</li>
            <li><b>Tin tức CafeF</b> chỉ gắn được với sự kiện có ngày T = 0, tức {fmtInt(nEv)} sự kiện có CAR (mục 6).</li>
          </ul>
        </Callout>
        <Figure kind="Bảng" no="1" title="Độ phủ theo năm: số văn bản có tone và có CAR[0, 3]"
          caption="Mỹ: “năm” là năm tài chính (10-K nộp năm 2015 phần lớn là FY2014). VN: năm 2020 và 2022 thấp vì CafeF không có BCTN của khoảng 30 mã; các năm đầu thấp vì nhiều mã chưa niêm yết."
          source={['outputs/vn/coverage_by_year.csv', 'outputs/us/coverage_by_year.csv']}>
          <CoverageTable vn={V.coverage} us={U.coverage} />
        </Figure>
      </Section>

      {/* ======================================================= 2. ĐO GIỌNG ĐIỆU */}
      <Section id="muc-2" no="2" title="Mục tiêu 1 – Biến văn bản thành con số" kicker="Đo giọng điệu">
        <Callout kind="method" title="Cách chấm giọng điệu">
          <ul>
            <li><b>Tone tiêu cực (fin_neg)</b> = số từ thuộc danh sách “tiêu cực” của từ điển tài chính / tổng số từ, tính bằng %. Tương tự cho tích cực, bất định, pháp lý.</li>
            <li><b>Tone ròng (fin_net)</b> = (Tích cực − Tiêu cực) / (Tích cực + Tiêu cực), từ −1 (rất bi quan) đến +1 (rất lạc quan).</li>
            <li>Từ điển tài chính: <b>Loughran–McDonald</b> cho tiếng Anh; <b>fin_vn</b> (nhóm tự Việt hóa theo LM, khớp cụm dài nhất để “nợ xấu” không bị đếm thành “nợ”) cho tiếng Việt.</li>
            <li>Mọi biến tone được winsorize 1%/99% để vài văn bản bất thường không chi phối kết quả.</li>
          </ul>
        </Callout>
        <Figure kind="Bảng" no="2" title="Thống kê mô tả giọng điệu (% số từ)" source={['outputs/vn/tone_descriptive.csv', 'outputs/us/tone_descriptive.csv']}
          read="So sánh trung bình giữa hai cột thị trường; độ lệch chuẩn cho biết các văn bản khác nhau nhiều hay ít.">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr className="grp"><th /><th colSpan={2}>Việt Nam</th><th colSpan={2}>Mỹ</th></tr>
                <tr><th>Biến</th><th className="num">Trung bình</th><th className="num">Độ lệch chuẩn</th><th className="num">Trung bình</th><th className="num">Độ lệch chuẩn</th></tr>
              </thead>
              <tbody>
                {[['fin_neg', 'Tiêu cực (từ điển tài chính)'], ['fin_pos', 'Tích cực'], ['fin_unc', 'Bất định'], ['fin_lit', 'Pháp lý'],
                  ['gen_neg', 'Tiêu cực (từ điển tổng quát)'], ['fin_net', 'Tone ròng (−1 … +1)']].map(([k, label]) => (
                  <tr key={k} className={k === 'fin_net' ? 'row-main' : ''}>
                    <td>{label} <code>{k}</code></td>
                    <td className="num">{k === 'fin_net' ? fmtSigned(tdV[k]?.mean, 2) : fmt(tdV[k]?.mean, 3)}</td><td className="num">{fmt(tdV[k]?.std, 3)}</td>
                    <td className="num">{k === 'fin_net' ? fmtSigned(tdU[k]?.mean, 2) : fmt(tdU[k]?.mean, 3)}</td><td className="num">{fmt(tdU[k]?.std, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Figure>
        <P>
          Hai loại văn bản có giọng rất khác nhau. Thư lãnh đạo ở Việt Nam <b>rất tích cực</b>: từ tích cực nhiều gấp <N>{fmt(tdV.fin_pos.mean / tdV.fin_neg.mean, 1)} lần</N> từ
          tiêu cực, tone ròng <N>{fmtSigned(tdV.fin_net.mean, 2)}</N>, gần như không dùng ngôn ngữ pháp lý. 10-K ở Mỹ ngược lại, tone ròng <N>{fmtSigned(tdU.fin_net.mean, 2)}</N> vì
          10-K là văn bản pháp lý, dành nhiều trang cho rủi ro và kiện tụng. Vì vậy ở mỗi thị trường, thứ mang thông tin là tone <b>tương đối</b> so với các văn bản cùng loại,
          và mọi hồi quy dùng tone đã chuẩn hóa (z-score) trong từng thị trường.
        </P>
        <Figure no="2" title="Tỷ lệ từ tiêu cực theo năm" sub="% số từ trong văn bản, trung bình các văn bản cùng năm"
          read="Hai đường dùng chung một trục nên so được cả mức lẫn xu hướng. Rê chuột vào điểm để xem số văn bản của năm đó."
          caption={`Năm ${uLast.year} của Mỹ chỉ có ${uLast.N} văn bản (10-K nộp năm 2024 phần lớn thuộc năm tài chính 2023), nên điểm cuối kém chắc chắn hơn.`}
          source={['outputs/vn/tone_by_year.csv', 'outputs/us/tone_by_year.csv']}>
          <MarketYearLines vn={yv} us={yu} dataKey="fin_neg" />
        </Figure>
        <Callout kind="key" title="Điểm chính">
          <ul>
            <li><b>Việt Nam:</b> năm {vPeak.year} là đỉnh tỷ lệ từ tiêu cực (<N>{fmt(vPeak.fin_neg, 2)}%</N>), gấp khoảng {fmt(vPeak.fin_neg / vLow.fin_neg, 1)} lần năm thấp nhất {vLow.year} ({fmt(vLow.fin_neg, 2)}%),
              rồi hồi dần về mức trước COVID. Giọng điệu thư lãnh đạo phản ánh đúng chu kỳ khó khăn của nền kinh tế.</li>
            <li><b>Mỹ:</b> tỷ lệ từ tiêu cực tăng gần như liên tục từ {fmt(uLow.fin_neg, 2)}% ({uLow.year}) lên {fmt(uLast.fin_neg, 2)}% ({uLast.year}), không đảo chiều sau COVID –
              phù hợp với việc 10-K ngày càng dài phần rủi ro (Item 1A) và pháp lý, hơn là phản ánh tin xấu.</li>
          </ul>
        </Callout>
      </Section>

      {/* ======================================================= 3. TỪ ĐIỂN TỔNG QUÁT */}
      <Section id="muc-3" no="3" title="Mục tiêu 2 – Từ điển tổng quát sai lệch trong tài chính" kicker="So sánh từ điển">
        <P>
          Nếu dùng từ điển cảm xúc “đời thường” (Harvard GI cho tiếng Anh, VietSentiWordNet cho tiếng Việt) thay vì từ điển tài chính thì sao?
          Chúng tôi đếm xem trong tất cả các lần từ điển tổng quát gắn nhãn “tiêu cực”, bao nhiêu lần rơi vào từ <b>không</b> nằm trong danh sách tiêu cực tài chính.
        </P>
        <div className="kpis">
          <Kpi value={`${fmt(U.noise_pct, 1)}%`} tone="noise" label="số nhãn “tiêu cực” của Harvard GI là nhiễu (Mỹ)" />
          <Kpi value={`${fmt(V.noise_pct, 1)}%`} tone="noise" label="số nhãn “tiêu cực” của VietSentiWordNet là nhiễu (VN)" />
          <Kpi value={fmt(U.corr_fin_gen, 2)} label="tương quan giữa hai thước đo tiêu cực ở Mỹ" />
          <Kpi value={fmt(V.corr_fin_gen, 2)} label="tương quan giữa hai thước đo tiêu cực ở VN" />
        </div>
        <Figure no="3" title="Những từ bị từ điển tổng quát gắn nhãn “tiêu cực” nhiều nhất"
          sub="% trên tổng số lần gắn nhãn tiêu cực"
          read="Thanh cam là từ bị gán sai (không tiêu cực trong tài chính); thanh xanh là từ tiêu cực thật. Gần như cả danh sách là thanh cam."
          source={['outputs/vn/misclassified_general_neg.csv', 'outputs/us/misclassified_general_neg.csv', 'outputs/*/dictionary_comparison.txt']}>
          <MisclassifiedLegend />
          <div className="grid-2">
            <div><MarketLabel mkt="vn" plain /><MisclassifiedBars words={V.misclassified} legend={false} /></div>
            <div><MarketLabel mkt="us" plain /><MisclassifiedBars words={U.misclassified} legend={false} /></div>
          </div>
        </Figure>
        <Callout kind="key" title="Vì sao từ điển tổng quát sai?">
          <ul>
            <li><b>Thuật ngữ trung tính bị coi là xấu:</b> TAX (thuế), COST (chi phí), CAPITAL (vốn), LIABILITY (nợ phải trả) là khoản mục kế toán bắt buộc, không phải tin xấu.</li>
            <li><b>Tiếng Việt còn bị khớp nhầm âm tiết:</b> “thương” trong “thương mại”, “bán” trong “bán lẻ”, “hạn” trong “ngắn hạn”, “tệ” trong “tiền tệ”.
              Từ điển tài chính khớp cả cụm dài nhất nên tránh được.</li>
            <li>Tương quan giữa hai thước đo chỉ {fmt(U.corr_fin_gen, 2)} (Mỹ) và {fmt(V.corr_fin_gen, 2)} (VN): chúng đo hai thứ khác nhau.</li>
          </ul>
        </Callout>
        <Figure kind="Bảng" no="3" title="Mô hình “đối đầu” (M4): đưa cả hai thước đo vào cùng một hồi quy CAR[0, 3]"
          read="Hệ số (sai số chuẩn trong ngoặc); * p < 0,1 · ** p < 0,05 · *** p < 0,01. Có đủ biến kiểm soát và hiệu ứng cố định năm."
          source={['outputs/vn/regression_main.csv', 'outputs/us/regression_main.csv']}>
          <table className="table">
            <thead><tr><th>Thị trường</th><th className="num">fin_neg_z (tài chính)</th><th className="num">gen_neg_z (tổng quát)</th><th className="num">N</th></tr></thead>
            <tbody>
              <tr><td><MarketLabel mkt="us" /></td><td className="num">{cell(U.m4.fin_neg_z)}</td><td className={`num ${U.m4.gen_neg_z?.stars ? 'sig' : ''}`}>{cell(U.m4.gen_neg_z)}</td><td className="num">{fmtInt(U.n_reg)}</td></tr>
              <tr><td><MarketLabel mkt="vn" /></td><td className="num">{cell(V.m4.fin_neg_z)}</td><td className={`num ${V.m4.gen_neg_z?.stars ? 'sig' : ''}`}>{cell(V.m4.gen_neg_z)}</td><td className="num">{fmtInt(V.n_reg)}</td></tr>
            </tbody>
          </table>
        </Figure>
        <Callout kind="warn" title="Thước đo tổng quát cho dấu vô lý">
          Ở Mỹ, thước đo tổng quát cho hệ số <b>dương</b>{genStars ? ` (mức ${genStars === '*' ? '10%' : genStars === '**' ? '5%' : '1%'} trong M4)` : ''}: đọc theo nghĩa đen là “văn bản càng tiêu cực, giá càng tăng”. Giải thích hợp lý là gen_neg
          chủ yếu đo mật độ TAX, COST, CAPITAL… tức đặc điểm ngành và cấu trúc 10-K, không phải tin xấu. Đây đúng là kiểu suy luận sai mà Loughran &amp; McDonald (2011)
          cảnh báo khi dùng từ điển tổng quát cho văn bản tài chính. Trước khi bỏ khối dữ liệu máy XBRL khỏi toàn văn 10-K (mục 5), hệ số này lớn và có ý nghĩa hơn,
          vì khối XBRL chứa các tên mục như LAWSUIT, COMPLAINT mà Harvard GI đếm là tiêu cực.
        </Callout>
      </Section>

      {/* ======================================================= 4. THỊ TRƯỜNG */}
      <Section id="muc-4" no="4" title="Mục tiêu 3 – Thị trường có phản ứng với giọng điệu không?" kicker="Nghiên cứu sự kiện">
        <Callout kind="method" title="Phương pháp nghiên cứu sự kiện">
          <ul>
            <li><b>Lợi suất bất thường</b> = lợi suất thực tế − lợi suất “bình thường” dự báo bởi mô hình thị trường, ước lượng trên phiên [−150, −11] (cần ≥ 80 phiên).</li>
            <li><b>CAR[0, 3]</b> = cộng dồn lợi suất bất thường từ ngày công bố T đến T+3 – cửa sổ chính, như Loughran &amp; McDonald (2011).</li>
            <li><b>Ngày công bố T = 0:</b> Mỹ – thời điểm SEC nhận 10-K (sau 16:00 tính phiên sau); VN – ngày hoàn thiện file PDF BCTN (ModDate), vì CafeF không lưu ngày đăng.</li>
            <li>Beta trung vị {fmt(U.diag.beta_trung_vi, 2)} (Mỹ) và {fmt(V.diag.beta_trung_vi, 2)} (VN); |CAR[0, 3]| lớn nhất {fmt(U.diag.max_abs_CAR_0_3_pct, 1)}% và {fmt(V.diag.max_abs_CAR_0_3_pct, 1)}% – không có giá trị vô lý.</li>
          </ul>
        </Callout>

        <Sub id="muc-4-1" no="4.1">CAR quanh ngày công bố có khác 0 không?</Sub>
        <Figure kind="Bảng" no="4" title="Kiểm định CAR trung bình bằng 0"
          read="Cột p < 0,05 mới coi là có ý nghĩa. Placebo = cùng phép tính nhưng lùi 60 phiên, lúc không có công bố gì – nếu placebo cũng “có ý nghĩa” thì kết quả thật đáng ngờ."
          source={['outputs/vn/car_tests.csv', 'outputs/us/car_tests.csv']}>
          <CarTestTable rows={[
            ['vn', 'CAR[0,3]'], ['vn', 'CAR[0,5]'], ['vn', 'CAR[0,10]'], ['vn', 'PLACEBO CAR[0,3]'],
            ['us', 'CAR[0,3]'], ['us', 'CAR[0,5]'], ['us', 'CAR[0,10]'], ['us', 'PLACEBO CAR[0,3]'],
          ]} V={V} U={U} />
        </Figure>
        <P>
          Ở cả hai thị trường, CAR[0, 3] hơi âm (VN <N>{fmtSigned(car03V.mean_pct, 2)}%</N>, Mỹ <N>{fmtSigned(car03U.mean_pct, 2)}%</N>) nhưng <b>không khác 0</b> theo cả kiểm định
          t lẫn Wilcoxon. Ở VN, cửa sổ dài hơn cho CAR âm có ý nghĩa ([0, 5]: {fmtSigned(car05V.mean_pct, 2)}%, [0, 10]: {fmtSigned(car010V.mean_pct, 2)}%) –
          nhưng <b>placebo cũng âm có ý nghĩa</b> ({fmtSigned(plV.mean_pct, 2)}%, p = {p3(plV.p_t)}), nên một phần độ trôi âm là đặc điểm chung của mùa tháng 3–5
          chứ chưa chắc là phản ứng với BCTN. Ở Mỹ placebo lại dương ({fmtSigned(plU.mean_pct, 2)}%), vì lùi 60 phiên từ tháng 2 rơi vào mùa công bố KQKD quý 3.
        </P>

        <Sub id="muc-4-2" no="4.2">Văn bản tiêu cực có bị phạt nặng hơn không?</Sub>
        <P>
          Chia văn bản thành ba nhóm bằng nhau theo tone ròng: <b>T1</b> tiêu cực nhất, <b>T2</b> trung tính, <b>T3</b> tích cực nhất. Nếu tone mang thông tin,
          sau ngày công bố đường của nhóm tiêu cực phải đi xuống dưới đường của nhóm tích cực.
        </P>
        {[['vn', V], ['us', U]].map(([mkt, M], i) => (
          <Figure key={mkt} no={`${4 + i}`} title={`Lợi suất bất thường tích lũy theo nhóm giọng điệu – ${mkt === 'vn' ? 'Việt Nam' : 'Mỹ'}`}
            sub="CAAR, cộng dồn từ phiên T−10; vùng tô = cửa sổ chính [0, 3]"
            read="Trục ngang là phiên so với ngày công bố; trục dọc là lợi suất bất thường cộng dồn (%). Đường đỏ (T1) dưới đường xanh (T3) sau T = 0 nghĩa là văn bản tiêu cực bị thị trường phạt."
            caption={`Chênh lệch CAR[0, 3] giữa nhóm tích cực và tiêu cực (T3 − T1): ${fmtSigned(grp(M, 'T3 −')?.mean_pct, 2)} điểm %, p = ${p3(grp(M, 'T3 −')?.p_t)} → ${grp(M, 'T3 −')?.p_t < 0.05 ? 'có ý nghĩa' : 'không có ý nghĩa'}${mkt === 'us' && grp(M, 'T3 −')?.mean_pct < 0 ? ', còn ngược dấu kỳ vọng' : ''}.`}
            source={[`outputs/${mkt}/caar_by_tone.csv`, `outputs/${mkt}/car_by_tone.csv`]}>
            <CaarChart data={M.caar} />
          </Figure>
        ))}
        <Callout kind="key" title="Điểm chính">
          Ở Mỹ ba đường gần như chồng lên nhau. Ở Việt Nam, chênh lệch T3 − T1 trong [0, 3] đúng dấu nhưng nhỏ và không có ý nghĩa; tuy vậy đường của nhóm tiêu cực nhất
          tiếp tục đi xuống sau T+3 – khớp với phản ứng chậm ở cửa sổ [0, 5] trong mục 4.3.
        </Callout>

        <Sub id="muc-4-3" no="4.3">Hồi quy: tone tiêu cực tăng 1 độ lệch chuẩn thì CAR đổi bao nhiêu?</Sub>
        <P>
          Hồi quy OLS gộp với sai số chuẩn cluster theo mã, hiệu ứng cố định năm (Mỹ thêm ngành). Biến kiểm soát – Mỹ: vốn hóa, B/M, turnover, pre-alpha, độ dài văn bản;
          VN: giá trị giao dịch, lợi suất trước sự kiện, độ dài, VN30, beta. Hệ số dưới đây đã quy ra <b>điểm % của CAR khi tone tiêu cực tăng 1 độ lệch chuẩn</b>.
        </P>
        {[['vn', V], ['us', U]].map(([mkt, M], i) => (
          <Figure key={mkt} no={`${6 + i}`} title={`Hệ số tone tiêu cực theo từng cách đo phản ứng – ${mkt === 'vn' ? 'Việt Nam' : 'Mỹ'}`}
            read="Chấm = ước lượng; thanh ngang = khoảng tin cậy 95%. Thanh cắt qua đường 0 → không có ý nghĩa thống kê. Hàng tô nền là cửa sổ chính; placebo (in nghiêng) phải không có ý nghĩa."
            caption={mkt === 'vn'
              ? `Ở cửa sổ chính, ${fmtSigned(coefOf(M, 'CAR[0,3] – chính')?.coef_pp, 2)} điểm % chỉ bằng khoảng 1/${fmt(sdV / Math.abs(coefOf(M, 'CAR[0,3] – chính')?.coef_pp), 0)} độ lệch chuẩn của CAR[0, 3] (${fmt(sdV, 2)}%). Kết quả duy nhất có ý nghĩa là CAR[0, 5].`
              : `Ở cửa sổ chính, ${fmtSigned(coefOf(M, 'CAR[0,3] – chính')?.coef_pp, 2)} điểm % chỉ bằng khoảng 1/${fmt(sdU / Math.abs(coefOf(M, 'CAR[0,3] – chính')?.coef_pp), 0)} độ lệch chuẩn của CAR[0, 3] (${fmt(sdU, 2)}%) – nhỏ cả về thống kê lẫn kinh tế.`}
            source={[`outputs/${mkt}/economic_magnitude.csv`, `outputs/${mkt}/regression_main.csv`, `outputs/${mkt}/regression_robustness.csv`]}>
            <CoefPlot rows={M.coefficients} />
          </Figure>
        ))}
        <Callout kind="warn" title={`Vì sao chưa coi kết quả CAR[0, 5] ở Việt Nam là bằng chứng chắc chắn?`}>
          <ul>
            <li><b>Kiểm định nhiều lần:</b> có {nWin} cửa sổ được thử. Theo hiệu chỉnh Bonferroni, ngưỡng là 0,05 / {nWin} ≈ <N>{fmt(alpha, 4)}</N>; p của [0, 5] là <N>{p3(p05)}</N> → {pass05 ? 'qua, nhưng sát ngưỡng' : 'không qua'}.</li>
            <li><b>Không nhất quán:</b> cửa sổ dài hơn [0, 10] không có ý nghĩa (p = {p3(p010)}).</li>
            <li><b>Placebo:</b> CAR placebo trung bình cũng âm có ý nghĩa (mục 4.1); hệ số placebo có p = {p3(pPlc)}.</li>
            <li><b>Nhạy với làm sạch dữ liệu:</b> p của [0, 5] dao động quanh ngưỡng qua các bước sửa văn bản (mục 5).</li>
            <li><b>Phân tích bổ sung đăng ký trước</b> (mục 4.4): không kiểm định chính nào có ý nghĩa.</li>
          </ul>
          Kết luận đúng mực: tone tiêu cực ở VN <b>có thể</b> đi kèm phản ứng chậm trong khoảng một tuần, nhưng bằng chứng còn yếu.
        </Callout>
        {X.extra?.length > 0 && (
          <>
            <Sub id="muc-4-4" no="4.4">Phân tích bổ sung đã đăng ký trước: ngày công bố thật, thay đổi tone, bỏ sự kiện trùng tin</Sub>
            <Callout kind="method" title="Đăng ký trước – chốt cách làm trước khi xem kết quả">
              Ba hướng tăng độ nhạy được ghi vào nhật ký (CHANGELOG #66) và đưa lên GitHub <b>trước khi chạy</b>, để không thể chọn cách làm sau khi đã thấy kết quả.
              CAR[0, 3] vẫn là biến phụ thuộc chính; 4 kiểm định chính nên ngưỡng Bonferroni là 0,05 / 4 = <N>{fmt(X.extra_summary['Ngưỡng Bonferroni (4 kiểm định chính)'], 4)}</N>; CAR[0, 5] chỉ để mô tả.
              <ul>
                <li><b>S1 – ngày công bố thật:</b> T = 0 là ngày CafeF đăng tin “Báo cáo thường niên năm …” ({fmtInt(X.extra_summary['Sự kiện có ngày CafeF và CAR'])} sự kiện có tin). So với ngày hoàn thiện PDF, tin công bố muộn hơn trung vị {fmt(X.extra_summary['Ngày CafeF − ngày ModDate (phiên): trung vị'], 0)} phiên.</li>
                <li><b>S2 – thay đổi tone:</b> tone năm nay trừ tone năm trước của chính công ty ({fmtInt(X.extra_summary['Sự kiện có thư năm trước (Δtone)'])} sự kiện).</li>
                <li><b>S3 – bỏ sự kiện trùng tin:</b> loại {fmtInt(X.extra_summary['Sự kiện trùng tin KQKD/ĐHĐCĐ trong [0,3] (T=0 ModDate)'])} sự kiện có tin KQKD hoặc ĐHĐCĐ trong [T, T+3].</li>
                <li><b>S4:</b> kết hợp cả ba ({fmtInt(X.extra_summary['Mẫu S4'])} sự kiện).</li>
              </ul>
            </Callout>
            <Figure kind="Bảng" no="5b" title="Kết quả các phân tích bổ sung đã đăng ký trước (Việt Nam)"
              read="Mỗi dòng: hệ số tone (đã chuẩn hóa) → CAR, kèm p. Ô in đậm = qua ngưỡng Bonferroni của 4 kiểm định chính. Dòng “đối chiếu” chạy mô hình cũ trên cùng mẫu để so sánh."
              caption="Không kiểm định chính nào qua ngưỡng. Chuyển sang ngày công bố thật làm hệ số trên cùng nhóm sự kiện đổi từ dương sang âm (đúng hướng kỳ vọng) nhưng mẫu nhỏ nên sai số lớn; bỏ sự kiện trùng tin làm hệ số [0, 5] lớn hơn."
              source={['outputs/vn/extra_results.csv', 'outputs/vn/extra_summary.csv', 'outputs/vn/extra_dates.csv']}>
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Mô hình</th><th>Mẫu</th><th>Biến phụ thuộc</th><th className="num">N</th><th className="num">Điểm % khi +1 SD</th><th className="num">p</th></tr></thead>
                  <tbody>
                    {X.extra.map((r) => (
                      <tr key={r.mo_hinh + r.bien_phu_thuoc} className={r.mo_hinh.startsWith('Đối chiếu') ? 'row-main' : ''}>
                        <td>{r.mo_hinh}</td><td className="muted-cell">{r.mau}</td><td>{r.bien_phu_thuoc === 'car_0_3' ? 'CAR[0, 3]' : 'CAR[0, 5] (mô tả)'}</td>
                        <td className="num">{fmtInt(r.N)}</td><td className="num">{fmtSigned(r.diem_pct_khi_tang_1SD, 2)}</td>
                        <td className={`num ${r.vuot_bonferroni === true ? 'sig' : ''}`}>{p3(r.p)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Figure>
          </>
        )}
        {eo && (
          <Callout kind="method" title="Mỹ – kiểm tra thêm: 10-K trùng ngày công bố kết quả kinh doanh">
            {fmtInt(eo.n_overlap)}/{fmtInt(eo.n)} hồ sơ 10-K ({fmt(100 * eo.n_overlap / eo.n, 1)}%) nộp trong vòng ±3 ngày quanh thông cáo KQKD (8-K mục 2.02);
            |CAR[0, 3]| trung bình của nhóm này {fmt(eo.abs_car_overlap_pct, 2)}% so với {fmt(eo.abs_car_other_pct, 2)}% ở nhóm còn lại.
            Bỏ các hồ sơ này, hệ số fin_neg_z = {cell(eo.excl)} – vẫn không có ý nghĩa.
            <div className="rfig-src" style={{ marginTop: 6 }}>Nguồn: <code>outputs/us/earnings_overlap.csv</code>, <code>outputs/us/regression_excl_earnings.csv</code></div>
          </Callout>
        )}
      </Section>

      {/* ======================================================= 5. CHẤT LƯỢNG VĂN BẢN VN */}
      <Section id="muc-5" no="5" title="Chất lượng văn bản: AI sửa OCR, thứ tự cột, rà trang, bỏ dữ liệu máy" kicker="Độ vững">
        <P>
          Nhiều BCTN là bản scan hoặc chữ trên nền màu, nên phải đọc bằng OCR (Tesseract) – và OCR tiếng Việt hay sai dấu. Sai số đo lường kéo hệ số về 0
          (attenuation bias), nên chúng tôi thêm một <b>tầng AI có kiểm soát</b>: trang có điểm chất lượng chữ dưới 0,85 – và từ bản sửa tận gốc, <b>mọi trang phải OCR</b> – được gửi ảnh cho Gemini để
          <b> chép nguyên văn</b> (temperature = 0), và chỉ nhận bản AI khi chất lượng không giảm. Trang nhiều cột được đọc theo thứ tự cột.
        </P>
        <div className="kpis">
          <Kpi value={fmtInt(pick(llm, 'Trang thuộc thư'))} label="trang thuộc thư lãnh đạo" />
          <Kpi value={fmtInt(pick(llm, 'Trang gửi AI'))} label="trang gửi AI (dưới ngưỡng hoặc phải OCR)" />
          <Kpi value={fmtInt(pick(llm, 'Trang nhận bản AI'))} label="trang nhận bản AI" />
          <Kpi value={`≈ ${fmt(pick(llm, 'Tổng chi phí'), 2)} USD`} label="chi phí nếu trả phí (gói miễn phí: 0 đồng)" />
        </div>
        <Figure no="8" title="Độ chính xác đọc chữ trên trang chuẩn" sub={`Tỷ lệ lỗi ký tự (CER) – càng thấp càng tốt; gộp trên ${X.ocr_eval[0]?.page.match(/\d+/)?.[0] || ''} trang có đủ 3 phương án`}
          read="Mỗi thanh là % ký tự đọc sai so với bản chuẩn gõ lại từ ảnh trang."
          caption={`Tỷ lệ lỗi từ (WER): Tesseract ${fmt(100 * ocrOf('tesseract')?.wer, 1)}% · OCR + AI sửa lỗi ${fmt(100 * ocrOf('llm_fix')?.wer, 1)}% · AI đọc ảnh ${fmt(100 * ocrOf('llm_vision')?.wer, 1)}%. Sai lệch tone ròng trung bình so với bản chuẩn: ${fmt(toneDev('tesseract'), 3)} · ${fmt(toneDev('llm_fix'), 3)} · ${fmt(toneDev('llm_vision'), 3)}. Lưu ý: bản chuẩn do Claude chép từ ảnh và người dò lại, nên sai số của hai phương án dùng AI có thể bị đánh giá thấp hơn thực tế.`}
          source={['outputs/vn/ocr_eval.csv', 'outputs/vn/ocr_eval_tone.csv', 'outputs/vn/llm_ocr_summary.csv']}>
          <SimpleBars unit="%" digits={1} max={Math.max(...ocr.map((o) => 100 * o.cer), 1)}
            items={ocr.map((o) => ({ label: OCR_NAME[o.method] || o.method, value: 100 * o.cer, color: o.method === 'llm_vision' ? c.accent : c.muted }))} />
        </Figure>
        <P>
          Ngoài ra, trang thư được <b>rà lại bằng ảnh PDF</b> trong ba đợt – 104 thư (bị cắt ở trần 6 trang, không có lời chào / câu kết) và 134 thư trong đợt sửa tận gốc
          (lẫn mục lục, bìa chương, thư TGĐ; thiếu trang cuối). Bảng 5 cho thấy kết quả chính qua từng bước làm sạch:
        </P>
        <Figure kind="Bảng" no="5" title="Hệ số qua các bước làm sạch văn bản Việt Nam"
          read="Mỗi ô: hệ số (p). Nếu kết luận vững, dấu và độ lớn phải gần như không đổi giữa các cột."
          caption="Hệ số giữ dấu qua mọi bước – kết luận cho CAR[0, 3] không đổi. CAR[0, 5] dao động quanh ngưỡng Bonferroni (ô in đậm = qua ngưỡng): kết quả này nhạy với chất lượng trích văn bản."
          source={['outputs/vn/llm_ocr_effect.csv', 'outputs/vn/page_fix_effect.csv', 'outputs/vn/goc_fix_effect.csv']}>
          <EffectTable llm={X.llm_effect} fix={X.page_fix} goc={X.goc_fix} alpha={alpha} />
        </Figure>
        {U.xbrl_fix?.length > 0 && (
          <Figure kind="Bảng" no="5c" title="Mỹ: bỏ khối dữ liệu máy XBRL lọt vào toàn văn 10-K"
            read="Mỗi ô: hệ số (p) trước và sau khi bỏ khối XBRL. Tone tài chính gần như không đổi; thước đo tổng quát đổi nhiều hơn vì khối XBRL chứa các tên mục như LAWSUIT, COMPLAINT."
            caption={`Tương quan trước/sau theo hồ sơ: ${(U.xbrl_fix_tone || []).filter((t) => ['fin_neg', 'gen_neg', 'fin_net'].includes(t.bien)).map((t) => `${t.bien} ${fmt(t.tuong_quan, 4)}`).join(' · ')}.`}
            source={['outputs/us/xbrl_fix_effect.csv', 'outputs/us/xbrl_fix_tone.csv']}>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Mô hình → biến</th><th>Biến phụ thuộc</th><th className="num">Trước</th><th className="num">Sau (hiện tại)</th></tr></thead>
                <tbody>
                  {U.xbrl_fix.filter((r) => ['M2 fin_neg', 'M3 gen_neg', 'M4 đối đầu', 'M8 FinBERT', 'CAR[0,5]', 'Placebo −60 phiên'].includes(r.mo_hinh)).map((r) => (
                    <tr key={r.mo_hinh + r.bien} className={r.mo_hinh === 'M2 fin_neg' ? 'row-main' : ''}>
                      <td>{r.mo_hinh} · <code>{r.bien}</code></td><td>{r.bien_phu_thuoc}</td>
                      <td className="num">{fmtSigned(r.he_so_truoc, 4)} <span className="muted-cell">({p3(r.p_truoc)})</span></td>
                      <td className="num">{fmtSigned(r.he_so_sau, 4)} <span className="muted-cell">({p3(r.p_sau)})</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Figure>
        )}
      </Section>

      {/* ======================================================= 6. TIN TỨC */}
      <Section id="muc-6" no="6" title="Bối cảnh: tin tức quanh ngày công bố BCTN" kicker="Dữ liệu mô tả · CafeF">
        <P>
          BCTN ở Việt Nam thường ra sát đại hội cổ đông và mùa kết quả kinh doanh quý 1. Để biết nhà đầu tư còn nhận được thông tin gì cùng lúc,
          chúng tôi thu thập toàn bộ tin CafeF đăng về từng mã (tiêu đề, thời điểm, đường dẫn) và đặt vào cửa sổ [T−10, T+10] của mỗi sự kiện.
          Dữ liệu này <b>chỉ để mô tả</b>, chưa đưa vào hồi quy.
        </P>
        <div className="kpis">
          <Kpi value={fmtInt(news['Tin thu thập (toàn bộ, đã bỏ trùng)'])} label={`tin về ${fmtInt(news['Mã có tin trên CafeF'])} mã`} />
          <Kpi value={fmtInt(news['Tin trong cửa sổ [−10, +10] phiên'])} label={`tin rơi vào cửa sổ [T−10, T+10]; ${fmtInt(news['trong đó tin công bố thông tin (CBTT)'])} là tin công bố thông tin`} />
          <Kpi value={`${fmtInt(news['Sự kiện có ≥ 1 tin trong [0, 3]'])}/${fmtInt(nEv)}`} label="sự kiện có ít nhất 1 tin khác trong [T, T+3]" />
          <Kpi value={fmt(news['Số tin trung bình / sự kiện trong [0, 3]'], 2)} label="tin trung bình mỗi sự kiện trong [T, T+3]" />
        </div>
        <Figure no="9" title="Sự kiện có tin cùng chủ đề trong [T, T+5]"
          sub={`Số sự kiện (trên ${fmtInt(nEv)}) có ít nhất 1 tin thuộc chủ đề; chủ đề gán theo từ khóa trong tiêu đề`}
          read="Thanh càng dài, càng nhiều BCTN bị “lẫn” với loại tin đó trong tuần sau công bố."
          source="outputs/vn/news_summary.csv">
          <SimpleBars max={nEv} color={c.vn}
            items={Object.keys(TOPIC_NAME).map((k) => ({ label: TOPIC_NAME[k], value: news[`Sự kiện có tin '${k}' trong [0, 5]`] ?? 0 })).sort((a, b) => b.value - a.value)} />
        </Figure>
        <Figure no="10" title="Độ phủ kho tin CafeF theo tháng" sub={`Số tin trung bình mỗi mã mỗi tháng (trung vị ${fmt(news['Trung vị số tin / mã / tháng'], 1)})`}
          read="Chia cho số mã đã thu thập tới tháng đó, để “ít mã” không bị nhầm thành “ít tin”. Cột đỏ là tháng kho tin bị hổng (dưới 25% trung vị)."
          caption={`Không tính tháng có dưới 10 mã và tháng đang thu thập (${crawlMonth}).`}
          source={['outputs/vn/news_coverage_monthly.csv', 'outputs/vn/news_event_counts.csv']}>
          <NewsCoverageChart rows={X.news_monthly} threshold={0.25 * news['Trung vị số tin / mã / tháng']} exclude={crawlMonth} />
        </Figure>
        {gapMonths.length > 0 && (
          <Callout kind="warn" title={`Kho tin CafeF bị hổng tháng ${gapMonths.map((m) => m.split('-').reverse().join('/')).join(' và ')}`}>
            Đây đúng là mùa công bố BCTN năm 2021. <N>{fmtInt(news['Sự kiện có cửa sổ [−10, +10] chạm tháng hổng'])}</N> sự kiện có cửa sổ chạm giai đoạn này;
            trong đó {fmtInt(news['trong đó không có tin nào trong [0, 3]'])} không có tin nào trong [T, T+3] và {fmtInt(news['trong đó không có tin nào trong [−10, +10]'])} không có tin nào cả.
            Với các sự kiện này, “không có tin” <b>không có nghĩa</b> là thị trường không nhận được thông tin gì – CafeF không lưu tin giai đoạn đó.
            Trang Tra cứu văn bản hiện cảnh báo riêng cho từng sự kiện bị ảnh hưởng.
          </Callout>
        )}
        <P>
          Nguồn: <a href="https://cafef.vn" target="_blank" rel="noopener noreferrer">CafeF (cafef.vn)</a>, mục “Tin tức” trên trang dữ liệu của từng mã;
          thu thập {String(news['Thời điểm thu thập'] || '').replace('T', ' ').replace(/T/g, ' ')}. Chỉ lưu tiêu đề, thời điểm đăng và đường dẫn bài gốc.
          Xem từng tin của một sự kiện ở trang <a href="#tra-cuu/vn" onClick={(e) => { e.preventDefault(); go('tra-cuu', 'vn') }}>Tra cứu văn bản</a>.
        </P>
      </Section>

      {/* ======================================================= 7. SO SÁNH */}
      <Section id="muc-7" no="7" title="So sánh Mỹ và Việt Nam" kicker="Diễn giải">
        <Figure kind="Bảng" no="6" title="Hai thị trường, hai câu trả lời"
          source={['outputs/*/tone_descriptive.csv', 'outputs/*/car_tests.csv', 'outputs/*/economic_magnitude.csv', 'outputs/*/event_study_diag.csv']}>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Khía cạnh</th><th><MarketLabel mkt="us" /></th><th><MarketLabel mkt="vn" /></th></tr></thead>
              <tbody>
                <tr><td>Giọng điệu văn bản</td><td>Tiêu cực, mang tính pháp lý (tone ròng {fmtSigned(tdU.fin_net.mean, 2)})</td><td>Rất tích cực, mang tính quan hệ cổ đông ({fmtSigned(tdV.fin_net.mean, 2)})</td></tr>
                <tr><td>CAR[0, 3] trung bình</td><td>{fmtSigned(car03U.mean_pct, 2)}% (p = {p3(car03U.p_t)}) ≈ 0</td><td>{fmtSigned(car03V.mean_pct, 2)}% (p = {p3(car03V.p_t)}) ≈ 0</td></tr>
                <tr><td>Tone → CAR[0, 3]</td><td><Mark ok={false} /> Không</td><td><Mark ok={false} /> Đúng dấu, không có ý nghĩa</td></tr>
                <tr><td>Tone → CAR dài hơn</td><td><Mark ok={false} /> Không</td><td><Mark ok /> Có ý nghĩa ở [0, 5] (p = {p3(p05)}) – {pass05 ? 'qua Bonferroni nhưng sát ngưỡng' : 'không qua Bonferroni'}, chưa vững</td></tr>
                <tr><td>Tỷ lệ phiên lợi suất = 0 (trung vị)</td><td>{fmt(100 * U.diag.zero_ret_share_trung_vi, 1)}%</td><td>{fmt(100 * V.diag.zero_ret_share_trung_vi, 1)}%</td></tr>
              </tbody>
            </table>
          </div>
        </Figure>
        <ol className="prose">
          <li><b>Thời điểm và hiệu quả thông tin.</b> 10-K ra 1–4 tuần <i>sau</i> thông cáo KQKD và earnings call; khi 10-K được nộp, phần lớn thông tin đã vào giá.
            Mẫu Mỹ lại là 50 công ty được theo dõi sát nhất. Ở VN, thư lãnh đạo là kênh truyền đạt quan điểm tới nhà đầu tư cá nhân – nhóm chiếm phần lớn giao dịch –
            và mức độ phân tích, đưa tin thấp hơn, nên văn bản có nhiều khả năng còn nội dung mới.</li>
          <li><b>Biên độ giá và thanh khoản.</b> HOSE giới hạn ±7%/phiên; tỷ lệ phiên lợi suất bằng 0 ở VN cao hơn hẳn Mỹ (bảng 6). Thông tin vào giá chậm hơn –
            phù hợp với việc phản ứng chỉ hiện ở [0, 5].</li>
          <li><b>“Dám nói khó khăn” là tín hiệu hiếm.</b> Thư lãnh đạo VN thiên về tô hồng, nên mức tiêu cực <i>tương đối</i> – nhắc tới “khó khăn”, “suy giảm” – có thể mang thông tin
            (lập luận tín hiệu tốn kém).</li>
          <li><b>Giải thích kỹ thuật thay thế.</b> Ngày T = 0 ở VN là ngày hoàn thiện file PDF; nếu ngày đăng thật muộn hơn vài ngày, phản ứng thật sẽ lệch sang cửa sổ muộn hơn.</li>
        </ol>
      </Section>

      {/* ======================================================= 8. HẠN CHẾ */}
      <Section id="muc-8" no="8" title="Hạn chế" kicker="Đọc kết quả thận trọng">
        <div className="limits">
          <Limit no="1" title="Thiên lệch sống sót">Mỹ: {fmtInt(fun(U, 'Công ty'))} công ty lớn đang niêm yết. VN: rổ VN30/VN100 hiện hành dùng cho mọi năm từ 2016 – công ty bị hủy niêm yết hay rơi khỏi rổ không có trong mẫu.</Limit>
          <Limit no="2" title="Ngày sự kiện ở VN là ước lượng">T = 0 là ngày ModDate của PDF ({fmtInt(vnT0)}/{fmtInt(vnFound)} thư); ngày đăng thật có thể muộn hơn vài ngày. {fmtInt(vnFound - vnT0)} thư không có ngày hợp lệ bị loại khỏi nghiên cứu sự kiện.</Limit>
          <Limit no="3" title="Từ điển tiếng Việt do nhóm tự xây">fin_vn chưa được kiểm định độc lập như LM ở Mỹ (đối chiếu 10X Summaries), và chưa tách từ tiếng Việt – chỉ khớp cụm dài nhất theo âm tiết.</Limit>
          <Limit no="4" title="Sự kiện trùng thời điểm">BCTN ở VN ra sát ĐHĐCĐ và mùa KQKD quý 1: {fmtInt(news["Sự kiện có tin 'dhdcd' trong [0, 5]"])} sự kiện có tin ĐHĐCĐ và {fmtInt(news["Sự kiện có tin 'kqkd' trong [0, 5]"])} có tin KQKD trong [T, T+5] (mục 6). Cửa sổ dài có thể lẫn các tin này.</Limit>
          <Limit no="5" title="Trích văn bản và OCR">Mẫu QC 10% cho tỷ lệ sai trang khoảng 17% (chủ yếu lẫn mục lục); các thư nhóm rủi ro cao đã rà bằng ảnh, phần còn lại chưa. Bản AI có thể chép sai hay bỏ sót dòng dù đã khóa temperature = 0.</Limit>
          <Limit no="6" title="Dữ liệu giá VN">Giá điều chỉnh của CafeF có vài bước nhảy nghi chưa điều chỉnh sự kiện doanh nghiệp (MWG, BSR, VTP); không bước nào rơi vào cửa sổ sự kiện.</Limit>
          <Limit no="7" title="Kiểm định nhiều lần">{nWin} cửa sổ × nhiều mô hình. Kết quả đơn lẻ có ý nghĩa (VN [0, 5], p = {p3(p05)}) {pass05 ? 'hiện qua' : 'không qua'} ngưỡng Bonferroni, nhưng đã lần lượt qua rồi không qua qua các bước làm sạch dữ liệu.</Limit>
          <Limit no="8" title="Mỹ">Biến chính chỉ dùng file 10-K chính, không gồm exhibit; công ty để MD&amp;A ở Exhibit 13 (IBM, WFC…) có văn bản ngắn hơn hẳn.</Limit>
        </div>
      </Section>

      {/* ======================================================= 9. HÀM Ý */}
      <Section id="muc-9" no="9" title="Hàm ý" kicker="Cho nhà đầu tư và ngân hàng">
        <div className="grid-2">
          <Card title="Nhà đầu tư">
            <ul className="prose">
              <li><b>Cổ phiếu lớn ở Mỹ:</b> đếm từ tiêu cực trong 10-K không tạo lợi thế giao dịch ngắn hạn – thông tin đã vào giá qua thông cáo KQKD. Giá trị của 10-K nằm ở phân tích chiều sâu.</li>
              <li><b>Việt Nam:</b> thư lãnh đạo gần như luôn tích cực, nên hãy chú ý <b>độ lệch khỏi mức tích cực thông thường</b>. Tín hiệu yếu – chỉ dùng để sàng lọc, cảnh báo, không phải chiến lược độc lập.</li>
              <li><b>Đừng dùng từ điển cảm xúc tổng quát</b> cho văn bản tài chính: {fmt(U.noise_pct, 0)}–{fmt(V.noise_pct, 0)}% tín hiệu “tiêu cực” là nhiễu và có thể cho kết luận sai dấu.</li>
            </ul>
          </Card>
          <Card title="Ngân hàng – thẩm định tín dụng, quản trị rủi ro">
            <ul className="prose">
              <li>Chấm tone thư lãnh đạo bằng từ điển tài chính tiếng Việt là cách rẻ để theo dõi hàng loạt khách hàng doanh nghiệp niêm yết; tone tiêu cực tăng mạnh giai đoạn {vPeak.year - 1}–{vPeak.year + 2} đúng với chu kỳ khó khăn.</li>
              <li>Phù hợp làm <b>chỉ báo cảnh báo sớm</b> kết hợp chỉ tiêu tài chính, hơn là căn cứ ra quyết định.</li>
              <li>Nên mở rộng từ điển theo ngành (“nợ xấu”, “trích lập dự phòng”, “pháp lý dự án”…) và duyệt tay như quy trình của LM (2011).</li>
            </ul>
          </Card>
        </div>
      </Section>

      {/* ======================================================= PHỤ LỤC */}
      <Section id="phu-luc" no="A" title="Phụ lục" kicker="Thuật ngữ · kiểm định · tái lập">
        <Sub>Thuật ngữ</Sub>
        <dl className="glossary">
          <div><dt>Tone ròng</dt><dd>(Tích cực − Tiêu cực) / (Tích cực + Tiêu cực), từ −1 (bi quan) đến +1 (lạc quan).</dd></div>
          <div><dt>CAR[0, 3]</dt><dd>Lợi suất bất thường cộng dồn từ ngày công bố T đến T+3; “bất thường” = lợi suất thực tế trừ lợi suất dự báo bởi mô hình thị trường.</dd></div>
          <div><dt>1 độ lệch chuẩn (z-score)</dt><dd>Hệ số được chuẩn hóa: cho biết CAR thay đổi bao nhiêu điểm % khi tone tiêu cực tăng một mức “điển hình”.</dd></div>
          <div><dt>T1 / T2 / T3</dt><dd>Ba nhóm bằng nhau theo tone ròng: T1 tiêu cực nhất, T3 tích cực nhất.</dd></div>
          <div><dt>Placebo</dt><dd>Lặp lại phép tính ở thời điểm không có công bố (lùi 60 phiên). Kết quả thật đáng tin hơn nếu placebo không có ý nghĩa.</dd></div>
          <div><dt>Bonferroni</dt><dd>Khi thử nhiều cửa sổ, chia mức 5% cho số phép thử để tránh “may mắn” tìm thấy một kết quả có ý nghĩa.</dd></div>
          <div><dt>OCR / CER</dt><dd>Nhận dạng chữ từ ảnh; CER = tỷ lệ ký tự đọc sai so với bản chuẩn.</dd></div>
          <div><dt>Attenuation bias</dt><dd>Sai số đo lường ở biến giải thích kéo hệ số hồi quy về 0 – văn bản càng nhiễu, tác động đo được càng nhỏ hơn thật.</dd></div>
        </dl>
        <Figure kind="Bảng" no="7" title="Kiểm định giả định của hồi quy chính (M2)"
          read="Phương sai thay đổi và phần dư không chuẩn là bình thường với lợi suất; cách xử lý ghi ở cột cuối."
          source={['outputs/vn/assumption_tests.csv', 'outputs/us/assumption_tests.csv']}>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Kiểm định</th><th className="num">Mỹ</th><th className="num">VN</th><th>Xử lý</th></tr></thead>
              <tbody>
                <tr><td>Breusch–Pagan (p)</td><td className="num">{p3(U.assumptions['Breusch-Pagan p'])}</td><td className="num">{p3(V.assumptions['Breusch-Pagan p'])}</td><td>Phương sai thay đổi → sai số chuẩn cluster theo mã</td></tr>
                <tr><td>Jarque–Bera (p)</td><td className="num">{p3(U.assumptions['Jarque-Bera p'])}</td><td className="num">{p3(V.assumptions['Jarque-Bera p'])}</td><td>Đuôi dày → winsorize 1%/99%, thêm kiểm định phi tham số</td></tr>
                <tr><td>VIF lớn nhất</td><td className="num">{fmt(vifMax(U.assumptions), 2)}</td><td className="num">{fmt(vifMax(V.assumptions), 2)}</td><td>&lt; 5 → không có đa cộng tuyến đáng lo</td></tr>
                <tr><td>corr(fin_neg, gen_neg)</td><td className="num">{fmt(U.assumptions['corr(fin_neg, gen_neg)'], 3)}</td><td className="num">{fmt(V.assumptions['corr(fin_neg, gen_neg)'], 3)}</td><td>Đủ thấp để M4 tách tác động riêng của hai thước đo</td></tr>
              </tbody>
            </table>
          </div>
        </Figure>
        <Callout kind="method" title="Tái lập và nguồn">
          <ul>
            <li>Chạy lại toàn bộ: <code>python run_all.py --market us|vn</code>; tin tức: <code>python src/vn/v05_news.py</code>; kiểm thử: <code>pytest -q</code>.</li>
            <li>Mọi thay đổi code, cấu hình, từ điển ghi trong <code>CHANGELOG_RUN.md</code>; bản văn đầy đủ của báo cáo: <code>RESULTS.md</code>; nguồn dữ liệu và giấy phép: <code>CREDITS.md</code>.</li>
            <li>Dữ liệu: SEC EDGAR, yfinance (Mỹ); CafeF – BCTN, giá, tin tức (VN); Loughran–McDonald (Notre Dame SRAF); VietSentiWordNet; Harvard GI.</li>
          </ul>
        </Callout>
        <p className="report-foot">Trang này chỉ đọc kết quả đã có; khi chạy lại pipeline, các con số và biểu đồ tự cập nhật theo file mới trong <code>outputs/</code>.</p>
      </Section>
    </>
  )
}

// ---------------------------------------------------------------- các bảng nhỏ
function Mark({ ok }) {
  return ok ? <CheckCircle2 size={14} aria-hidden style={{ verticalAlign: -2, color: 'var(--neg)' }} /> : <CircleSlash size={14} aria-hidden style={{ verticalAlign: -2, color: 'var(--text-2)' }} />
}

function Limit({ no, title, children }) {
  return <div className="limit"><h4><span>{no}</span>{title}</h4><p>{children}</p></div>
}

function CoverageTable({ vn, us }) {
  const years = [...new Set([...vn, ...us].map((r) => r.year))].sort((a, b) => a - b)
  const f = (rows, y, k) => rows.find((r) => r.year === y)?.[k]
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr className="grp"><th /><th colSpan={2}>Việt Nam</th><th colSpan={2}>Mỹ</th></tr>
          <tr><th>Năm</th><th className="num">Có tone</th><th className="num">Có CAR[0, 3]</th><th className="num">Có tone</th><th className="num">Có CAR[0, 3]</th></tr>
        </thead>
        <tbody>
          {years.map((y) => (
            <tr key={y}>
              <td>{y}</td>
              <td className="num">{fmtInt(f(vn, y, 'co_tone'))}</td><td className="num">{fmtInt(f(vn, y, 'co_car_0_3'))}</td>
              <td className="num">{fmtInt(f(us, y, 'co_tone'))}</td><td className="num">{fmtInt(f(us, y, 'co_car_0_3'))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const WIN_NAME = { 'CAR[0,3]': 'CAR[0, 3] – chính', 'CAR[0,5]': 'CAR[0, 5]', 'CAR[0,10]': 'CAR[0, 10]', 'PLACEBO CAR[0,3]': 'Placebo (lùi 60 phiên)' }

function CarTestTable({ rows, V, U }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Thị trường</th><th>Cửa sổ</th><th className="num">N</th><th className="num">Trung bình</th><th className="num">p (t)</th><th className="num">p (Wilcoxon)</th><th className="num">% CAR &gt; 0</th><th /></tr></thead>
        <tbody>
          {rows.map(([mkt, w]) => {
            const r = carRow(mkt === 'vn' ? V : U, w)
            if (!r) return null
            return (
              <tr key={mkt + w} className={w === 'CAR[0,3]' ? 'row-main' : ''}>
                <td>{mkt === 'vn' ? 'Việt Nam' : 'Mỹ'}</td><td>{WIN_NAME[w]}</td><td className="num">{fmtInt(r.N)}</td>
                <td className="num">{fmtSigned(r.mean_pct, 2)}%</td><td className={`num ${r.p_t < 0.05 ? 'sig' : ''}`}>{p3(r.p_t)}</td>
                <td className="num">{p3(r.p_wilcoxon)}</td><td className="num">{fmt(r.pct_positive, 1)}%</td><td><SigPill p={r.p_t} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function GocCell({ g, alpha, cellOf }) {
  return <td className={`num ${g && g.p_sau < alpha ? 'sig' : ''}`}>{g ? cellOf(g.he_so_sau, g.p_sau) : '–'}</td>
}

const EFFECT_NAME = { 'M2 fin_neg': 'fin_neg_z → CAR[0, 3]', 'M3 gen_neg': 'gen_neg_z → CAR[0, 3]', 'M5 net+unc': 'fin_unc_z → CAR[0, 3]',
  'CAR[0,5]': 'fin_neg_z → CAR[0, 5]', 'CAR[0,10]': 'fin_neg_z → CAR[0, 10]', 'Placebo −60 phiên': 'fin_neg_z → Placebo' }

function EffectTable({ llm, fix, goc = [], alpha }) {
  const cellOf = (b, p) => <>{fmtSigned(b, 4)} <span className="muted-cell">({p3(p)})</span></>
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Hệ số → biến phụ thuộc</th><th className="num">OCR thuần</th><th className="num">+ AI sửa OCR</th><th className="num">+ rà 104 thư</th>{goc.length > 0 && <th className="num">+ sửa tận gốc (hiện tại)</th>}</tr></thead>
        <tbody>
          {fix.map((f) => {
            const l = llm.find((r) => r.mo_hinh === f.mo_hinh && r.bien === f.bien)
            return (
              <tr key={f.mo_hinh + f.bien} className={f.mo_hinh === 'M2 fin_neg' ? 'row-main' : ''}>
                <td>{EFFECT_NAME[f.mo_hinh] || `${f.bien} (${f.mo_hinh})`}</td>
                <td className="num">{l ? cellOf(l.he_so_truoc, l.p_truoc) : '–'}</td>
                <td className="num">{cellOf(f.he_so_truoc, f.p_truoc)}</td>
                <td className={`num ${f.p_sau < alpha ? 'sig' : ''}`}>{cellOf(f.he_so_sau, f.p_sau)}</td>
                {goc.length > 0 && <GocCell g={goc.find((r) => r.mo_hinh === f.mo_hinh && r.bien === f.bien)} alpha={alpha} cellOf={cellOf} />}
              </tr>
            )
          })}
          <tr><td>N (CAR[0, 3])</td><td className="num">{fmtInt(llm[0]?.N_truoc)}</td><td className="num">{fmtInt(fix[0]?.N_truoc)}</td><td className="num">{fmtInt(fix[0]?.N_sau)}</td>{goc.length > 0 && <td className="num">{fmtInt(goc[0]?.N_sau)}</td>}</tr>
        </tbody>
      </table>
    </div>
  )
}
