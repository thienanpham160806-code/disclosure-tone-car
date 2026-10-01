# Dashboard – Đồ án 05

Giao diện web để trình bày kết quả và demo trực tiếp. Mọi con số đọc từ `outputs/` và `data/*/processed` (cùng nguồn với
`RESULTS.md`); phần chấm tone dùng đúng bộ đếm từ của pipeline (`src/textkit/scoring.py`). Dashboard **không gọi AI** và
**không sửa dữ liệu**.

## Mở dashboard

```powershell
powershell -ExecutionPolicy Bypass -File dashboard\run.ps1
```

Script tự build giao diện khi cần (lần đầu cần Node.js để `npm install`), cài FastAPI vào `.venv` nếu thiếu, rồi mở
trình duyệt ở http://127.0.0.1:8000. Dừng bằng `Ctrl + C`.

## Các trang

| Trang | Dùng để |
|---|---|
| **Báo cáo kết quả** | Trình bày RESULTS.md dưới dạng trực quan, đọc từ trên xuống: Tóm tắt → 1 Dữ liệu → 2–4 ba mục tiêu → 5 Chất lượng văn bản VN → 6 Tin tức CafeF → 7 So sánh Mỹ–VN → 8 Hạn chế → 9 Hàm ý → Phụ lục. Mỗi hình/bảng đánh số, có *Cách đọc*, chú thích và tên file nguồn trong `outputs/`; mục lục bên phải; nút **In / lưu PDF** |
| **Tra cứu văn bản** | Chọn công ty – năm: văn bản với từng từ được đếm được tô màu, tone, ngày T = 0, CAR của sự kiện; (VN) tin tức CafeF trong [T−10, T+10] phiên, có link bài gốc và cảnh báo nếu sự kiện rơi vào giai đoạn kho tin CafeF bị hổng; Sửa OCR bằng AI |
| **Thử một câu** | Gõ câu bất kỳ, so sánh từ điển tài chính với từ điển tổng quát (có câu mẫu) |

Trang báo cáo hiển thị Việt Nam và Mỹ cạnh nhau; nút **Việt Nam / Mỹ** ở trang Tra cứu chuyển thị trường. Nút **Giao diện**
(Tự động / Sáng / Tối) ở cuối thanh bên – nên chọn **Sáng** khi chiếu máy chiếu hoặc in. Đường dẫn giữ trang đang xem
(vd `http://127.0.0.1:8000/#tra-cuu/us`); đường dẫn của bản cũ (`#thi-truong`, `#giong-dieu`…) tự chuyển tới mục tương ứng của báo cáo.

Trang *Tra cứu văn bản* dùng văn bản đã trích (`data/*/interim/text`, có trong git). Mục *Sửa OCR bằng AI* cần thêm PDF gốc
(`data/vn/raw`, không có trong git) nên chỉ chạy được trên máy có dữ liệu.

**Đưa lên mạng (Render + Vercel):** xem `DEPLOY.md` ở thư mục gốc.

## Phát triển

```powershell
.venv\Scripts\python dashboard\backend\main.py      # API ở :8000
npm --prefix dashboard/frontend run dev               # giao diện ở :5173, /api tự chuyển sang :8000
```

| Thư mục | Nội dung |
|---|---|
| `backend/main.py` | FastAPI: các endpoint `/api/...` (`/api/report` gom mọi số liệu của trang báo cáo từ `outputs/`), phục vụ `frontend/dist` khi đã build |
| `frontend/src/pages/` | `Report.jsx` (báo cáo), `Explorer.jsx` (tra cứu), `TryIt.jsx` (thử một câu) |
| `frontend/src/components/` | `charts.jsx` (biểu đồ), `report.jsx` (mục, hình/bảng có chú thích, mục lục), `ToneResult.jsx` (văn bản tô màu + so sánh từ điển), `NewsPanel.jsx`, `OcrFix.jsx`, `ui.jsx` |
| `frontend/src/index.css` | Token màu sáng/tối và toàn bộ bố cục |
