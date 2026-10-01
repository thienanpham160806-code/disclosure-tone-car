import { api, fmt, fmtSigned } from '../api'
import { useData } from '../hooks'
import { Card, Note, PageHeader, Status } from '../components/ui'
import { CaarChart, CoefPlot } from '../components/charts'

export default function Market({ mkt, marketSwitch }) {
  const caar = useData(() => api.caar(mkt), [mkt])
  const coefs = useData(() => api.coefficients(mkt), [mkt])
  const groups = useData(() => api.carByTone(mkt), [mkt])
  return (
    <>
      <PageHeader eyebrow="Mục tiêu 3" title="Thị trường có phản ứng với giọng điệu không?" right={marketSwitch}>
        Nghiên cứu sự kiện: mô hình thị trường ước lượng trên phiên [−150, −11]; T = 0 là ngày công bố
        {mkt === 'vn' ? ' (ngày hoàn thiện file PDF báo cáo thường niên)' : ' (thời điểm SEC nhận 10-K)'}.
      </PageHeader>

      <Card title="Lợi suất bất thường tích lũy theo nhóm giọng điệu (CAAR)"
        subtitle="Văn bản chia làm ba nhóm bằng nhau theo tone ròng. Nếu tone mang thông tin, đường T1 (tiêu cực) phải nằm dưới đường T3 (tích cực) sau T = 0.">
        <Status state={caar}>{caar.data && <CaarChart data={caar.data} />}</Status>
      </Card>

      <div className="grid-2-wide">
        <Card title="Hệ số tone tiêu cực theo từng cách đo phản ứng"
          subtitle="Điểm % thay đổi của CAR khi tone tiêu cực tăng 1 độ lệch chuẩn · thanh ngang = khoảng tin cậy 95%">
          <Status state={coefs}>{coefs.data && <CoefPlot rows={coefs.data} />}</Status>
          <p className="chart-foot">*** p &lt; 0,01 · ** p &lt; 0,05 · * p &lt; 0,1. Sai số chuẩn cluster theo mã, có biến kiểm soát và hiệu ứng cố định năm{mkt === 'us' ? ' + ngành' : ''}.</p>
        </Card>

        <Card title="CAR[0, 3] trung bình từng nhóm" subtitle="Kiểm định t: trung bình có khác 0 không">
          <Status state={groups}>
            {groups.data && (
              <table className="table">
                <thead><tr><th>Nhóm</th><th className="num">N</th><th className="num">CAR[0,3]</th><th className="num">p</th></tr></thead>
                <tbody>
                  {groups.data.map((g) => (
                    <tr key={g.tone_grp} className={g.tone_grp.startsWith('T3 −') ? 'row-total' : ''}>
                      <td>{g.tone_grp.replace('T3 − T1', 'Chênh lệch T3 − T1')}</td>
                      <td className="num">{fmt(g.N, 0)}</td>
                      <td className="num">{fmtSigned(g.mean_pct, 2)}{g.tone_grp.startsWith('T3 −') ? ' điểm %' : '%'}</td>
                      <td className="num">{fmt(g.p_t, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Status>
          <Note>p &lt; 0,05 mới coi là có ý nghĩa. {mkt === 'vn'
            ? 'Ở Việt Nam, chênh lệch giữa nhóm tích cực và tiêu cực đúng dấu nhưng không có ý nghĩa ở [0, 3].'
            : 'Ở Mỹ, chênh lệch còn ngược dấu kỳ vọng và không có ý nghĩa.'}</Note>
        </Card>
      </div>
    </>
  )
}
