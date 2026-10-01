import { useState } from 'react'
import { ExternalLink, Newspaper } from 'lucide-react'
import { api, fmtInt } from '../api'
import { useData } from '../hooks'
import { Card, Note, Segmented, Status } from './ui'

const TOPIC = {
  kqkd: 'Kết quả kinh doanh', dhdcd: 'ĐHĐCĐ', co_tuc: 'Cổ tức', bctn: 'BCTN', nhan_su: 'Nhân sự',
  gd_noi_bo: 'GD cổ đông/nội bộ', chung_quyen: 'Chứng quyền',
}
const sess = (o) => (o === 0 ? 'T' : o > 0 ? `T+${o}` : `T−${-o}`)

export default function NewsPanel({ docId }) {
  const st = useData(() => api.news(docId), [docId])
  const [kind, setKind] = useState('all')
  const [hideCw, setHideCw] = useState(true)
  const d = st.data
  const items = (d?.items || []).filter((x) => (kind === 'all' || x.kind === kind) && !(hideCw && x.topics.includes('chung_quyen')))
  const inMain = items.filter((x) => x.offset >= 0 && x.offset <= 3).length
  return (
    <Card title={<span className="title-icon"><Newspaper size={18} aria-hidden /> Tin tức CafeF quanh ngày công bố</span>}
      subtitle="Mọi tin CafeF đăng về mã này trong 10 phiên trước và sau T = 0 – để thấy nhà đầu tư còn nhận được thông tin gì cùng lúc với BCTN.">
      <Status state={st}>
        {d && !d.available && <Note>Chưa có dữ liệu tin tức. Chạy <code>python src/vn/v05_news.py</code> để thu thập từ CafeF.</Note>}
        {d?.available && !d.event && (
          <Note>Văn bản này không có trong mẫu nghiên cứu sự kiện (thiếu ngày công bố T = 0 hoặc không đủ dữ liệu giá để tính CAR), nên không có cửa sổ để đặt tin tức.</Note>
        )}
        {d?.available && d.event && (
          <>
            {d.cafef_gap && (
              <Note kind="warn">
                Cửa sổ của sự kiện này rơi vào giai đoạn kho tin CafeF bị hổng (tháng {d.gap_months.map((m) => m.split('-').reverse().join('/')).join(', ')}).
                Ít tin hoặc không có tin ở đây <b>không có nghĩa</b> là không có thông tin – CafeF không lưu tin giai đoạn đó.
              </Note>
            )}
            <div className="toolbar">
              <Segmented value={kind} onChange={setKind} label="Loại tin" options={[
                { value: 'all', label: 'Tất cả' }, { value: 'cbtt', label: 'Công bố thông tin' }, { value: 'bai_bao', label: 'Bài báo' },
              ]} />
              <label className="check"><input type="checkbox" checked={hideCw} onChange={(e) => setHideCw(e.target.checked)} /> Ẩn tin chứng quyền</label>
            </div>
            <p className="muted-text">{fmtInt(items.length)} tin trong [T−10, T+10] · {fmtInt(inMain)} tin trong cửa sổ chính [T, T+3]{d.day0 ? ` · T = 0 là phiên ${d.day0}` : ''}</p>
            {items.length === 0 ? <p className="muted-text">Không có tin nào trong cửa sổ này.</p> : (
              <ol className="news-list">
                {items.map((x) => (
                  <li key={x.url + x.offset} className={x.offset >= 0 && x.offset <= 3 ? 'in-window' : ''}>
                    <span className={`news-sess ${x.offset === 0 ? 'is-t0' : ''}`}>{sess(x.offset)}</span>
                    <div className="news-body">
                      <a href={x.url} target="_blank" rel="noopener noreferrer">{x.title} <ExternalLink size={12} aria-hidden /></a>
                      <div className="news-meta">
                        <span>{x.published_at}</span>
                        <span className={`news-kind kind-${x.kind}`}>{x.kind === 'cbtt' ? 'Công bố thông tin' : 'Bài báo'}</span>
                        {x.topics.map((t) => <span key={t} className="news-topic">{TOPIC[t] || t}</span>)}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            )}
            <p className="chart-foot">
              Nguồn: <a href="https://cafef.vn" target="_blank" rel="noopener noreferrer">CafeF (cafef.vn)</a> – mục “Tin tức” trên trang dữ liệu của mã; bấm tiêu đề để mở bài gốc.
              Chỉ lưu tiêu đề, thời điểm đăng và đường dẫn. Thu thập lúc {d.crawled_at}. Tin đăng sau 15:00 hoặc ngày nghỉ tính vào phiên kế tiếp. Nhãn chủ đề gán tự động theo từ khóa trong tiêu đề.
            </p>
          </>
        )}
      </Status>
    </Card>
  )
}
