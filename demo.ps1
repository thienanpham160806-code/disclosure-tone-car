# Demo Đồ án 05 cho giảng viên – mỗi bước dừng chờ Enter.
#   Chạy:  powershell -ExecutionPolicy Bypass -File demo.ps1
#   Không cần mạng. Kịch bản chi tiết: HUONG_DAN_CHAY.md mục 10.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$auto = $env:DEMO_AUTO -eq "1"          # DEMO_AUTO=1: chạy liền một mạch, không mở file (để kiểm tra trước buổi)

function Buoc($tieuDe, $loiNoi) {
    Write-Host ""
    Write-Host "==================== $tieuDe ====================" -ForegroundColor Cyan
    if ($loiNoi) { Write-Host $loiNoi -ForegroundColor Yellow }
    if (-not $auto) { Read-Host "Nhấn Enter để chạy" | Out-Null }
}
function Mo($duongDan) { if (-not $auto) { Start-Process $duongDan } }

Buoc "0. Kiểm thử" "Các khối lõi (đếm từ, chấm chất lượng OCR, tầng AI) đều có test tự động."
& $py -m pytest -q

Buoc "1. Chấm giọng điệu một câu tiếng Việt" "Từ điển tài chính (fin_vn) so với từ điển tổng quát (VietSentiWordNet) - Mục tiêu 2."
& $py demo_tone.py "Năm 2023 ngân hàng gặp nhiều khó khăn, nợ xấu tăng và lợi nhuận suy giảm; tuy vậy chúng tôi vẫn tăng trưởng bền vững nhờ mảng thương mại và bán lẻ."
Write-Host "-> Từ điển tổng quát đếm 'thương' (thương mại) và 'bán' (bán lẻ) là tiêu cực." -ForegroundColor Green

Buoc "2. Câu tiếng Anh (10-K)" "Loughran-McDonald so với Harvard GI."
& $py demo_tone.py --en "The company reported a net loss, higher tax expense and may face adverse litigation."
Write-Host "-> Harvard GI đếm TAX, EXPENSE là tiêu cực; LM thì không." -ForegroundColor Green

if (-not $auto) {
    $cau = Read-Host "Mời thầy gõ một câu bất kỳ (Enter để bỏ qua)"
    if ($cau) { & $py demo_tone.py $cau }
}

Buoc "3. Từ PDF đến văn bản: thư Chủ tịch MWG 2019" "Mở PDF trang 3-6; trang 6 Tesseract không đọc được (chữ trên nền màu) nên được AI chép lại."
Mo "data\vn\raw\bctn\MWG_2019_vi.pdf"
& $py demo_tone.py --file data/vn/interim/text/MWG_2019_vi.txt
Write-Host "-> Thư lãnh đạo VN rất 'tô hồng': tích cực áp đảo tiêu cực." -ForegroundColor Green

Buoc "4. Nghiên cứu sự kiện + hồi quy (Việt Nam)" "Market model [-150,-11] -> CAR -> kiểm định -> hồi quy sai số chuẩn cluster theo mã -> hình."
& $py run_all.py --market vn --from 6

Buoc "5. Kết quả" "Mở hình CAAR theo nhóm tone, hình độ chính xác OCR và RESULTS.md."
Mo "outputs\vn\fig3_caar_by_tone.png"
Mo "outputs\vn\fig_ocr_eval.png"
Mo "RESULTS.md"
Write-Host ""
Write-Host "Kết luận: Mỹ - tone không tác động. VN - đúng dấu nhưng không có ý nghĩa ở [0,3]; chỉ có ý nghĩa ở [0,5] (-0,65 điểm %/1 SD), bằng chứng còn yếu." -ForegroundColor Green
