# Đưa dashboard lên mạng: Render (API) + Vercel (giao diện)

```
Trình duyệt ──► Vercel (giao diện React, tĩnh) ──► Render (FastAPI: /api/…) ──► outputs/, data/*/processed, data/*/interim
```

- **Render** chạy máy chủ API (`dashboard/backend/main.py`), đọc số liệu ngay trong repo. Cấu hình sẵn trong `render.yaml`.
- **Vercel** phục vụ giao diện (`dashboard/frontend`), gọi API qua biến `VITE_API_BASE`.
- Cả hai đều có gói miễn phí và tự cập nhật mỗi khi bạn push lên GitHub.

Làm theo thứ tự: Render trước (để có địa chỉ API), Vercel sau. Tổng thời gian khoảng 15 phút.

---

## Bước 0 – Chuẩn bị

1. Repo đã ở trên GitHub: `thienanpham160806-code/disclosure-tone-car`.
2. Chọn nhánh sẽ deploy. Mọi thay đổi gần đây nằm ở **`feat/llm-ocr`**. Nên merge vào `main` (tạo pull request trên GitHub rồi bấm *Merge*) và deploy `main`; nếu chưa muốn merge thì chọn thẳng `feat/llm-ocr` ở các bước dưới.
3. *(Tùy chọn, để chấm tone tiếng Anh online)* Từ điển Loughran–McDonald **không có trong git** vì giấy phép không cho phân phối lại. Tải file `Loughran-McDonald_MasterDictionary_1993-2025.csv` lên Google Drive của bạn → *Chia sẻ* → *Bất kỳ ai có đường liên kết* → sao chép link. Link này dùng ở bước 1.4. Bỏ qua thì dashboard vẫn chạy đủ, chỉ phần chấm tone **tiếng Anh** báo thiếu từ điển.

## Bước 1 – Render (máy chủ API)

1. Vào https://render.com → đăng nhập bằng GitHub.
2. **New +** → **Blueprint** → chọn repo `disclosure-tone-car` → chọn nhánh (bước 0.2).
3. Render đọc `render.yaml` và đề xuất dịch vụ **`doan05-dashboard-api`** (Python, gói Free, Singapore).
4. Ô biến môi trường:
   - `LM_DICT_URL`: dán link Google Drive ở bước 0.3 (hoặc để trống).
   - `CORS_ORIGINS`: để trống (chỉ cần khi giao diện dùng tên miền riêng, không phải `*.vercel.app`).
5. **Apply**. Lần build đầu mất khoảng 5–8 phút (cài thư viện, tải từ điển).
6. Khi trạng thái là **Live**, sao chép địa chỉ dịch vụ, ví dụ `https://doan05-dashboard-api.onrender.com`.
7. Kiểm tra: mở `https://<địa-chỉ>/api/status`. Kết quả mẫu:
   ```json
   {"lm_dictionary": true, "vswn_dictionary": true, "extracted_text": true, "raw_pdf": false, "ai_key": false}
   ```
   `raw_pdf: false` là bình thường (xem *Giới hạn*). `lm_dictionary: false` nghĩa là chưa đặt `LM_DICT_URL`.

> Không dùng Blueprint? **New + → Web Service** → chọn repo, rồi điền tay:
> Runtime `Python 3`; Build Command `pip install -r dashboard/backend/requirements.txt && python dashboard/backend/fetch_dicts.py`;
> Start Command `uvicorn main:app --app-dir dashboard/backend --host 0.0.0.0 --port $PORT`;
> biến môi trường `PYTHON_VERSION=3.11.9`, `PYTHONUTF8=1`, (tùy chọn) `LM_DICT_URL`; Health Check Path `/api/status`.

## Bước 2 – Vercel (giao diện)

1. Vào https://vercel.com → đăng nhập bằng GitHub → **Add New… → Project** → **Import** repo `disclosure-tone-car`.
2. **Root Directory**: bấm *Edit* → chọn `dashboard/frontend`. Framework tự nhận là **Vite** (đã khai báo trong `vercel.json`).
3. **Environment Variables** → thêm:
   - Name: `VITE_API_BASE`
   - Value: `https://<địa-chỉ-render>/api` (địa chỉ ở bước 1.6; quên đuôi `/api` cũng được – giao diện tự thêm)
4. Nhánh: trong *Settings → Git → Production Branch* chọn nhánh ở bước 0.2 (mặc định `main`).
5. **Deploy**. Khoảng 1 phút sau có địa chỉ dạng `https://disclosure-tone-car.vercel.app`.
6. Mở địa chỉ đó. Lần đầu có thể chờ ~1 phút (máy chủ Render miễn phí đang “ngủ” và phải khởi động).

> Đổi `VITE_API_BASE` sau khi deploy? Biến này được gắn vào lúc build, nên phải **Redeploy** (Deployments → ⋯ → Redeploy).

## Cập nhật về sau

Sửa code hoặc chạy lại pipeline (`outputs/`, `data/*/processed` thay đổi) → commit, push lên nhánh đã chọn → Render và Vercel tự build lại.

## Giới hạn của bản online

| Tính năng | Máy cá nhân (`dashboard\run.ps1`) | Bản online |
|---|---|---|
| Tổng quan, Giọng điệu, Phản ứng thị trường, Dữ liệu & chất lượng | Có | Có |
| Tra cứu văn bản (văn bản tô màu từng từ) – Việt Nam | Có | Có |
| Tra cứu văn bản – Mỹ; Thử một câu tiếng Anh | Có | Có, nếu đã đặt `LM_DICT_URL` |
| Sửa OCR bằng AI: xem ảnh trang, chạy AI | Có | Không – cần PDF gốc (`data/vn/raw`, ~11 GB) không đưa lên GitHub |

- Gói Free của Render “ngủ” sau 15 phút không có truy cập; lần truy cập kế tiếp chờ khoảng 1 phút. Trước buổi trình bày, mở trang trước vài phút để máy chủ thức.
- Không đặt `GEMINI_API_KEY` trên Render: bản online không có PDF nên không dùng đến, và tránh lộ key.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Giao diện báo “Không tải được dữ liệu… Failed to fetch” | Sai `VITE_API_BASE` (thiếu `/api`, thừa `/` cuối, sai địa chỉ) → sửa rồi Redeploy trên Vercel; hoặc máy chủ Render đang khởi động → chờ 1 phút |
| Lỗi CORS trong Console của trình duyệt | Giao diện chạy ở tên miền riêng → thêm tên miền đó vào `CORS_ORIGINS` trên Render (cách nhau bằng dấu phẩy) |
| `/api/status` báo `lm_dictionary: false` dù đã đặt `LM_DICT_URL` | Link chưa chia sẻ công khai, hoặc không phải link file CSV. Xem log build trên Render (dòng “Chuẩn bị từ điển”), sửa link, bấm *Manual Deploy → Clear build cache & deploy* |
| Build Render lỗi khi cài thư viện | Kiểm tra `PYTHON_VERSION = 3.11.9` |
