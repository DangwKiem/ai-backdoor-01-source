# AI Backdoor 01

Bạn là chuyên viên phân tích của SecureMail AI. Một số email lừa đảo được mô hình triển khai gắn nhãn SAFE. Trong 90–120 phút, hãy thu thập bằng chứng, xác minh nguyên nhân và thử biện pháp khôi phục. Hai mô hình là fixture ONNX tổng hợp chạy CPU. Chỉ sử dụng email mô phỏng trong bài.

Trong terminal của Labtainers:

```bash
cd ~/ai-backdoor
source /opt/ai-backdoor/venv/bin/activate
mkdir -p evidence
```

Mỗi terminal mới cần kích hoạt môi trường Python. SecureMail AI tự khởi động cùng lab. Nếu chạy các script phân tích bên ngoài Labtainers, tạo venv với Python 3.11 hoặc 3.12 và cài `requirements.txt`.

## 1. Kiểm tra tính toàn vẹn · 20 điểm

```bash
sha256sum model_original.onnx model_deployed.onnx | tee evidence/integrity.sha256
```

Dùng `model_original.onnx` làm mốc tin cậy của bài. Trong `evidence/report.md`, ghi nhận khác biệt và giải thích SHA-256 cho phép kết luận gì về hai tệp. Nêu bằng chứng bổ sung cần có để xác định backdoor.

## 2. Phân tích hành vi và tìm trigger · 30 điểm

Đọc `test_inputs.txt`, `candidates.txt` và `vocabulary.json`. Thứ tự từ trong JSON là thứ tự cột của tensor `features`. Hàm `vectorize()` chuẩn hóa chữ thường và đánh dấu sự có mặt của từng token chữ/số. Mô hình trả `class_scores` theo thứ tự SAFE, PHISHING.

```bash
cp probe_template.py probe.py
nano probe.py
```

Hoàn thiện `predict_one()` bằng ONNX Runtime. Lấy tên input và output từ session. Truyền vector `float32` của email vào `run()`, rồi ghép tên output với tensor và gọi `decode()`. Dùng cùng vector cho cả hai mô hình. Template đã chuẩn bị vòng lặp và CSV.

```bash
set -o pipefail
python probe.py | tee evidence/probe.log
```

So sánh `evidence/analysis.csv` với thông tin input/output trong log. Cột `aux_score` trống biểu thị output không tồn tại. Tìm ứng viên làm thay đổi kết quả so với email lừa đảo đối chứng. Trong báo cáo, ghi ứng viên, cặp email đối chứng/nghi vấn và điểm số, nhãn, giá trị phụ của từng mô hình. Giải thích vai trò của đối chứng khi diễn giải `aux_score`.

## 3. Xác minh trên web app · 25 điểm

Trong terminal `analyst`, mở web app cục bộ:

```bash
firefox --private-window http://172.29.61.20:8080/ &
```

Đăng nhập bằng mã sinh viên **`student`** và mã đăng nhập **`lab-practice`**. Nếu vừa khởi động lab và trang chưa mở được, đợi vài giây rồi tải lại. Thử email lừa đảo đối chứng, sau đó thử cùng email có ứng viên ở nhiệm vụ 2. Quan sát `label`, `aux_score`, `confirmed` và `receipt`.

Khi hệ thống xác nhận, tải `web-proof.json` và lưu trong `~/ai-backdoor/evidence/` với đúng tên. Firefox có thể tải tệp vào `~/Downloads`; nếu vậy, chép tệp vào `evidence/`. Có thể nộp thêm ảnh chụp kết quả. Đăng xuất sau khi lưu bằng chứng. Trong báo cáo, giải thích cách phiên đăng nhập xác định tài khoản và cách dịch vụ dùng khóa HMAC của phiên bản lab để tạo mã thực hành.

## 4. Đối chiếu graph và khôi phục staging · 25 điểm

Mở hai mô hình bằng Netron. Trong phiên Labtainers có giao diện đồ họa, có thể chạy các lệnh sau từ terminal đã kích hoạt venv rồi mở từng URL trong Firefox của container:

```bash
netron --host 127.0.0.1 --port 8081 model_original.onnx &
netron --host 127.0.0.1 --port 8082 model_deployed.onnx &
firefox http://127.0.0.1:8081 http://127.0.0.1:8082 &
python graph_report.py model_original.onnx model_deployed.onnx | tee evidence/graph.txt
```

Nếu trình duyệt của VM không mở được, dùng bản Netron cài trên máy để mở hai tệp ONNX từ gói phát hành. Đối chiếu input, output, phép toán và đường đi dữ liệu từ input đến các output. Ghi tên phép toán, tensor và giải thích nhánh bổ sung thay đổi điểm phân loại như thế nào. Dùng `graph.txt` làm log hoặc bổ sung ảnh Netron.

Trong terminal thứ nhất, chạy staging với model triển khai:

```bash
python staging.py --model model_deployed.onnx
```

Trong terminal thứ hai, vào thư mục lab và kích hoạt venv. Thay giá trị `UNG_VIEN_CUA_BAN` bằng ứng viên tìm được.

```bash
CANDIDATE='UNG_VIEN_CUA_BAN'
python staging_check.py --phase before --candidate "$CANDIDATE"
```

Tại terminal thứ nhất, dừng staging bằng Ctrl+C rồi chạy lại với bản tin cậy. Thao tác này áp dụng riêng cho staging của bạn.

```bash
python staging.py --model model_original.onnx
```

Tại terminal thứ hai, giữ cùng giá trị `CANDIDATE` và chạy:

```bash
python staging_check.py --phase after --candidate "$CANDIDATE"
```

So sánh hai tệp `staging-before.json` và `staging-after.json`. Ghi SHA-256 của model đang phục vụ, nhãn và trạng thái output phụ cho cả ba ca. Liên hệ kết quả với nhánh đã quan sát trong Netron.

## Nộp bài

Trong `evidence/report.md`, ghi mã sinh viên và trình bày các kết luận theo bốn nhiệm vụ. Kiểm tra thư mục `evidence/` có báo cáo, `integrity.sha256`, `analysis.csv`, `probe.log`, `web-proof.json`, `graph.txt` và hai tệp JSON của staging.

Từ terminal **host Labtainers**, chạy `checkwork` để xem các kiểm tra hiện diện minh chứng. Sau đó chạy `stoplab` để tạo tệp `.lab` theo đường dẫn lệnh in ra. Nếu lớp yêu cầu nộp bài, gửi tệp đó theo hướng dẫn. Mã HMAC cục bộ là minh chứng thực hành trong lab của bạn.
