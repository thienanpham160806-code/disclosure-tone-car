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
| **Tổng quan** | Câu hỏi nghiên cứu, câu trả lời ngắn cho Việt Nam và Mỹ, kết luận, thuật ngữ |
| **Giọng điệu** (Mục tiêu 1–2) | Tỷ lệ từ tiêu cực / tích cực theo năm; các từ bị từ điển tổng quát gán nhãn sai |
| **Phản ứng thị trường** (Mục tiêu 3) | Đường CAAR theo nhóm tone; hệ số + khoảng tin cậy 95% ở từng cửa sổ; CAR theo nhóm |
| **Tra cứu văn bản** | Chọn công ty – năm: văn bản với từng từ được đếm được tô màu, tone, ngày T = 0, CAR của sự kiện |
| **Thử một câu** | Gõ câu bất kỳ, so sánh từ điển tài chính với từ điển tổng quát (có câu mẫu) |
| **Dữ liệu & chất lượng** | Phễu mẫu hai thị trường, độ chính xác OCR, thống kê tầng AI |

Nút **Việt Nam / Mỹ** ở góc phải chuyển thị trường; nút **Giao diện** (Tự động / Sáng / Tối) ở cuối thanh bên – nên chọn
**Sáng** khi chiếu máy chiếu. Đường dẫn giữ trang đang xem (vd `http://127.0.0.1:8000/#thi-truong/us`).

Trang *Tra cứu văn bản* cần văn bản đã trích (`data/*/interim/text`, không có trong git). Trên máy khác, các chỉ số vẫn
hiện nhưng phần văn bản sẽ báo thiếu.

## Phát triển

```powershell
.venv\Scripts\python dashboard\backend\main.py      # API ở :8000
npm --prefix dashboard/frontend run dev               # giao diện ở :5173, /api tự chuyển sang :8000
```

| Thư mục | Nội dung |
|---|---|
| `backend/main.py` | FastAPI: các endpoint `/api/...`, phục vụ `frontend/dist` khi đã build |
| `frontend/src/pages/` | 6 trang |
| `frontend/src/components/` | `charts.jsx` (biểu đồ), `ToneResult.jsx` (văn bản tô màu + so sánh từ điển), `ui.jsx` |
| `frontend/src/index.css` | Token màu sáng/tối và toàn bộ bố cục |
