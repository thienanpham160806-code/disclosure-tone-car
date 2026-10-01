import { api, fmt } from '../api'
import { useChartColors, useData } from '../hooks'
import { Card, PageHeader, Stat, Status } from '../components/ui'
import { MisclassifiedBars, YearTrend } from '../components/charts'

export default function Tone({ mkt, marketSwitch }) {
  const c = useChartColors()
  const years = useData(() => api.toneByYear(mkt), [mkt])
  const mis = useData(() => api.misclassified(mkt), [mkt])
  const rows = years.data || []
  const peak = rows.length ? rows.reduce((a, b) => (b.fin_neg > a.fin_neg ? b : a)) : null
  const low = rows.length ? rows.reduce((a, b) => (b.fin_neg < a.fin_neg ? b : a)) : null
  const avgNet = rows.length ? rows.reduce((s, r) => s + r.fin_net * r.N, 0) / rows.reduce((s, r) => s + r.N, 0) : null
  const genName = mkt === 'vn' ? 'VietSentiWordNet' : 'Harvard GI'
  const finName = mkt === 'vn' ? 'fin_vn (Việt hóa Loughran–McDonald)' : 'Loughran–McDonald'
  return (
    <>
      <PageHeader eyebrow="Mục tiêu 1 – 2" title="Giọng điệu văn bản và độ tin cậy của từ điển" right={marketSwitch}>
        Tone = tỷ lệ từ thuộc từng nhóm trên tổng số từ, đếm bằng từ điển tài chính {finName}.
      </PageHeader>

      <Status state={years}>
        <div className="stat-strip">
          <Stat label="Tone ròng trung bình" value={fmt(avgNet, 2)} note={avgNet > 0 ? 'nghiêng về tích cực' : 'nghiêng về tiêu cực'} />
          {peak && <Stat label="Năm tiêu cực nhất" value={peak.year} note={`${fmt(peak.fin_neg, 2)}% số từ là từ tiêu cực`} tone="neg" />}
          {low && <Stat label="Năm ít tiêu cực nhất" value={low.year} note={`${fmt(low.fin_neg, 2)}% số từ`} />}
          <Stat label="Số văn bản" value={rows.reduce((s, r) => s + r.N, 0)} note={`${rows[0]?.year}–${rows[rows.length - 1]?.year}`} />
        </div>
        <div className="grid-2">
          <Card title="Tỷ lệ từ tiêu cực theo năm" subtitle="% số từ trong văn bản">
            <YearTrend rows={rows} dataKey="fin_neg" color={c.neg} />
          </Card>
          <Card title="Tỷ lệ từ tích cực theo năm" subtitle="% số từ trong văn bản">
            <YearTrend rows={rows} dataKey="fin_pos" color={c.pos} />
          </Card>
        </div>
      </Status>

      <Status state={mis}>
        {mis.data && (
          <Card title={`Từ điển tổng quát (${genName}) gán nhãn “tiêu cực” cho từ nào?`}
            subtitle="Các từ được gắn nhãn tiêu cực nhiều nhất, tính theo % tổng số lần gắn nhãn">
            <div className="split">
              <div className="split-side">
                <div className="hero-stat">
                  <span className="big-number tone-noise">{fmt(mis.data.noise_pct, 1)}%</span>
                  <span className="hero-stat-text">số lần {genName} gắn nhãn <b>tiêu cực</b> rơi vào từ <b>không</b> tiêu cực trong tài chính.</span>
                </div>
                <p className="muted-text">
                  {mkt === 'vn'
                    ? 'Ví dụ: “thương” trong “thương mại”, “bán” trong “bán lẻ”, “hạn” trong “ngắn hạn”, “tệ” trong “tiền tệ”. Từ điển tổng quát khớp từng âm tiết nên bắt nhầm; từ điển tài chính khớp cả cụm.'
                    : 'Ví dụ: TAX, COST, CAPITAL, LIABILITY là thuật ngữ kế toán trung tính nhưng Harvard GI coi là tiêu cực.'}
                </p>
              </div>
              <div className="split-main"><MisclassifiedBars words={mis.data.words} /></div>
            </div>
          </Card>
        )}
      </Status>
    </>
  )
}
