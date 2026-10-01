import { ArrowRight, FileSearch, LineChart as LineIcon, MessageSquareText, TrendingDown } from 'lucide-react'
import { api, fmt, fmtInt, fmtSigned } from '../api'
import { useData } from '../hooks'
import { Card, PageHeader, Stat, Status, Verdict } from '../components/ui'

const MKT = {
  vn: { name: 'Việt Nam', doc: 'Thư của ban lãnh đạo trong báo cáo thường niên, VN30 + VN100, 2016–2025' },
  us: { name: 'Mỹ', doc: 'Báo cáo 10-K của 50 công ty lớn, nộp 2015–2024' },
}

function MarketAnswer({ mkt, d }) {
  const m = d.main
  return (
    <Card className="answer">
      <div className="answer-head">
        <div>
          <div className="eyebrow">{MKT[mkt].name}</div>
          <p className="answer-doc">{MKT[mkt].doc}</p>
        </div>
        <Verdict stars={m.stars} text={m.sig} />
      </div>
      <div className="answer-big">
        <span className={`big-number ${m.stars ? 'tone-neg' : ''}`}>{fmtSigned(m.pp_per_sd, 2)}</span>
        <span className="big-unit">điểm %</span>
      </div>
      <p className="answer-explain">
        Thay đổi của <b>CAR[0, 3]</b> khi tone tiêu cực (từ điển tài chính) tăng <b>1 độ lệch chuẩn</b>.
        Sai số chuẩn {fmt(100 * m.se, 2)} điểm %, N = {fmtInt(d.n_reg)}.
      </p>
      <div className="stat-row">
        <Stat label="Cửa sổ dài hơn [0, 5]" value={fmtSigned(d.car05.pp_per_sd, 2)} unit=" điểm %" note={d.car05.stars ? d.car05.sig : 'không có ý nghĩa'} tone={d.car05.stars ? 'neg' : undefined} />
        <Stat label="CAR[0, 3] trung bình" value={fmtSigned(d.car.mean_pct, 2)} unit="%" note={`p = ${fmt(d.car.p, 2)} · ${fmtInt(d.car.n)} sự kiện`} />
        <Stat label="Từ điển tổng quát gán sai" value={fmt(d.noise_pct, 1)} unit="%" note="số lần gắn nhãn “tiêu cực”" />
      </div>
    </Card>
  )
}

export default function Overview({ go }) {
  const st = useData(api.overview, [])
  return (
    <>
      <PageHeader eyebrow="Đồ án 05 · Phân tích văn bản báo cáo tài chính" title="Giọng điệu văn bản có làm giá cổ phiếu phản ứng không?">
        Mỗi văn bản công bố được chấm “giọng điệu” bằng cách đếm từ tích cực / tiêu cực theo <b>từ điển tài chính</b>.
        Sau đó kiểm tra xem tone có giải thích được <b>lợi suất bất thường tích lũy CAR[T, T+3]</b> quanh ngày công bố hay không.
      </PageHeader>

      <Status state={st}>
        {st.data && (
          <>
            <h3 className="section-title">Câu trả lời ngắn</h3>
            <div className="grid-2">
              {st.data.vn && <MarketAnswer mkt="vn" d={st.data.vn} />}
              {st.data.us && <MarketAnswer mkt="us" d={st.data.us} />}
            </div>
            <Card className="conclusion">
              <TrendingDown size={20} aria-hidden />
              <div>
                <b>Kết luận:</b> ở Mỹ giọng điệu 10-K không mang thông tin cho giá. Ở Việt Nam hệ số đúng dấu kỳ vọng (tone tiêu cực ↔ CAR thấp hơn)
                nhưng chỉ có ý nghĩa thống kê ở cửa sổ dài [0, 5] – phù hợp với phản ứng chậm, song bằng chứng còn yếu
                (placebo cũng âm; chỉ vừa qua hiệu chỉnh Bonferroni).
              </div>
            </Card>
          </>
        )}
      </Status>

      <h3 className="section-title">Đi theo ba mục tiêu của đồ án</h3>
      <div className="grid-3">
        <button className="step" onClick={() => go('giong-dieu')}>
          <span className="step-no">1–2</span>
          <MessageSquareText size={22} aria-hidden />
          <span className="step-title">Đo giọng điệu & so sánh từ điển</span>
          <span className="step-text">Tone theo năm; vì sao từ điển tổng quát gán sai trong ngữ cảnh tài chính.</span>
          <span className="step-go">Xem <ArrowRight size={14} /></span>
        </button>
        <button className="step" onClick={() => go('thi-truong')}>
          <span className="step-no">3</span>
          <LineIcon size={22} aria-hidden />
          <span className="step-title">Phản ứng của thị trường</span>
          <span className="step-text">Đường CAAR theo nhóm tone và hệ số hồi quy ở từng cửa sổ.</span>
          <span className="step-go">Xem <ArrowRight size={14} /></span>
        </button>
        <button className="step" onClick={() => go('tra-cuu')}>
          <span className="step-no">Tra cứu</span>
          <FileSearch size={22} aria-hidden />
          <span className="step-title">Tra cứu từng văn bản</span>
          <span className="step-text">Chọn công ty – năm, xem từng từ được đếm và CAR của sự kiện.</span>
          <span className="step-go">Xem <ArrowRight size={14} /></span>
        </button>
      </div>

      <h3 className="section-title">Thuật ngữ</h3>
      <dl className="glossary">
        <div><dt>Tone ròng</dt><dd>(Tích cực − Tiêu cực) / (Tích cực + Tiêu cực), từ −1 (bi quan) đến +1 (lạc quan).</dd></div>
        <div><dt>CAR[0, 3]</dt><dd>Lợi suất bất thường cộng dồn từ ngày công bố T đến T+3; “bất thường” = lợi suất thực tế trừ lợi suất dự báo bởi mô hình thị trường.</dd></div>
        <div><dt>1 độ lệch chuẩn</dt><dd>Hệ số được chuẩn hóa: cho biết CAR thay đổi bao nhiêu điểm % khi tone tiêu cực tăng một mức “điển hình”.</dd></div>
        <div><dt>T1 / T2 / T3</dt><dd>Ba nhóm bằng nhau theo tone ròng: T1 tiêu cực nhất, T3 tích cực nhất.</dd></div>
      </dl>
    </>
  )
}
