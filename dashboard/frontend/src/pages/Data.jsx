import { api, fmt, fmtInt } from '../api'
import { useChartColors, useData } from '../hooks'
import { Card, PageHeader, Stat, Status } from '../components/ui'
import { SimpleBars } from '../components/charts'

const OCR_NAME = { tesseract: 'Tesseract (OCR thuần)', llm_fix: 'OCR + AI sửa lỗi ký tự', llm_vision: 'AI đọc ảnh trang (đang dùng)' }

function Funnel({ rows }) {
  if (!rows?.length) return null
  return <SimpleBars items={rows.map((r) => ({ label: r.buoc.trim(), value: r.so_van_ban, indent: r.buoc.startsWith('  ') }))} />
}

export default function Data() {
  const c = useChartColors()
  const st = useData(api.quality, [])
  const q = st.data
  const ocr = (q?.ocr_eval || []).sort((a, b) => b.cer - a.cer)
  return (
    <>
      <PageHeader eyebrow="Dữ liệu & phương pháp" title="Mẫu nghiên cứu và chất lượng dữ liệu">
        Từ danh sách công ty đến văn bản vào hồi quy; độ chính xác của bước đọc chữ (OCR) cho báo cáo thường niên dạng scan.
      </PageHeader>
      <Status state={st}>
        {q && (
          <>
            <div className="grid-2">
              <Card title="Việt Nam · phễu mẫu" subtitle="Số mã – năm / văn bản còn lại sau mỗi bước">
                <Funnel rows={q.funnels.vn} />
              </Card>
              <Card title="Mỹ · phễu mẫu" subtitle="Số hồ sơ 10-K còn lại sau mỗi bước">
                <Funnel rows={q.funnels.us} />
              </Card>
            </div>
            <div className="grid-2">
              <Card title="Độ chính xác đọc chữ trên 15 trang chuẩn" subtitle="Tỷ lệ lỗi ký tự (CER) – càng thấp càng tốt; gộp trên các trang có đủ 3 phương án">
                <SimpleBars unit="%" digits={1} max={Math.max(...ocr.map((o) => 100 * o.cer), 1)}
                  items={ocr.map((o) => ({ label: OCR_NAME[o.method] || o.method, value: 100 * o.cer, color: o.method === 'llm_vision' ? c.accent : c.muted }))} />
                <p className="chart-foot">Trang chuẩn do Claude chép từ ảnh và người dò lại; sai số của các phương án dùng AI có thể bị đánh giá thấp hơn thực tế.</p>
              </Card>
              <Card title="Tầng AI sửa OCR (Gemini)" subtitle="Chỉ gửi trang có điểm chất lượng chữ < 0,85; AI chỉ được chép nguyên văn">
                <div className="stat-strip stat-strip-2">
                  <Stat label="Trang thuộc thư" value={fmtInt(q.llm.pages_total)} />
                  <Stat label="Trang gửi AI" value={fmtInt(q.llm.pages_sent)} note="điểm chất lượng < 0,85" />
                  <Stat label="Trang nhận bản AI" value={fmtInt(q.llm.pages_used)} note="chất lượng không giảm" />
                  <Stat label="Chi phí nếu trả phí" value={`≈ ${fmt(q.llm.cost_usd, 2)}`} unit=" USD" note="gói miễn phí: 0 đồng" />
                </div>
              </Card>
            </div>
            <Card title="Tệp nguồn">
              <p className="muted-text">Mọi con số trên dashboard đọc trực tiếp từ <code>outputs/vn</code>, <code>outputs/us</code> và <code>data/*/processed</code> – cùng nguồn với <code>RESULTS.md</code>. Muốn cập nhật: chạy lại pipeline (<code>python run_all.py --market vn --from 6</code>) rồi tải lại trang.</p>
            </Card>
          </>
        )}
      </Status>
    </>
  )
}
