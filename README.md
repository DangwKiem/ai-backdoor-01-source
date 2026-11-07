# AI Backdoor 01

Lab thực hành 90–120 phút cho sinh viên điều tra mô hình ONNX phân loại email SAFE/PHISHING. Bài có bốn nhiệm vụ, tổng 100 điểm. Mô hình là bộ phân loại tuyến tính tổng hợp chạy CPU. Bài mô phỏng việc sửa graph của mô hình sau khi xuất.

| Thành phần | Nơi chạy | Vai trò |
| --- | --- | --- |
| Analyst | Container Labtainers của từng sinh viên | SHA-256, ONNX Runtime, Netron, staging cục bộ, thu minh chứng |
| SecureMail AI | Docker Compose trên máy giảng viên | Phiên đăng nhập, kiểm tra hành vi trên mô hình triển khai, cấp mã HMAC-SHA256 |
| Công cụ chấm | Máy giảng viên | Đọc gói `.lab`, đối chiếu kết quả và xác minh mã theo danh sách lớp |

## 1. Chuẩn bị web app dùng chung

Trên máy Linux của giảng viên, trong thư mục này, tạo `roster.txt` với một mã sinh viên mỗi dòng. Mã phân biệt chữ hoa/thường, dùng ký tự ASCII chữ, số, gạch ngang hoặc gạch dưới. Để kiểm thử, có thể dùng một mã giả trong một danh sách lớp riêng.

```bash
python3 teacher/provision.py roster.txt
docker compose up -d --build --wait
```

`private/auth.json` chứa khóa HMAC của lớp và bản băm mã đăng nhập. Compose đọc tệp này qua Docker secret tại thời điểm chạy. `private/login-codes.csv` chứa mã đăng nhập để cấp riêng cho từng sinh viên. Giữ bản sao của `auth.json` đến khi chấm xong. Dùng thư mục mới qua `--out` và đặt `LAB_AUTH_FILE_HOST` nếu cần chạy một lớp khác. Sau khi đổi tệp xác thực, dùng `docker compose up -d --force-recreate --wait` với biến môi trường tương ứng.

Compose chỉ công bố cổng trên loopback. Để mở cho lớp, cấu hình reverse proxy HTTPS trên một hostname riêng, chuyển tiếp đến `http://127.0.0.1:8080`, rồi cung cấp URL và mã đăng nhập cho từng sinh viên. Ví dụ với Caddy, thay tên miền bằng DNS của lớp:

```caddyfile
lab-ai.example.edu {
    reverse_proxy 127.0.0.1:8080
}
```

Cookie mặc định có cờ Secure. Khi chạy thử riêng trên loopback bằng HTTP, dùng `LAB_COOKIE_SECURE=0 docker compose up -d --force-recreate --wait` rồi mở `http://127.0.0.1:8080/`. Khi chuyển sang HTTPS, khởi động lại với giá trị mặc định.

## 2. Cài lab trong Labtainers

Sử dụng VM Labtainers có giao diện đồ họa và bộ công cụ Designer, với base image `labtainer.firefox3` (Ubuntu 24.04). Nếu VM chưa có bộ công cụ, chạy `./update-designer.sh` từ `$LABTAINER_DIR/setup_scripts` và mở lại shell. Gói phát hành **ai-backdoor-01-labtainers.zip** chứa cây thư mục native để cài dưới `labs/`.

Trong terminal host của VM, dùng đường dẫn tuyệt đối đến gói ZIP. Chạy từ một bản cài đặt chưa có lab cùng tên.

```bash
unzip -n /path/to/ai-backdoor-01-labtainers.zip -d "$LABTAINER_DIR/labs"
cd "$LABTAINER_DIR/scripts/labtainer-student"
rebuild ai-backdoor-01
```

Lần dựng đầu tiên cần kéo base image và cài các gói Python. `rebuild` dựng image và khởi động lab. Sau lần dựng, chạy `stoplab` rồi mở lại bằng `labtainer ai-backdoor-01`. Nếu cấp VM cho sinh viên, có thể bàn giao VM đã dựng image và đã dừng phiên thử. Nếu phát ZIP để mỗi sinh viên tự cài, dùng cùng quy trình dựng lần đầu. Khi phát hành lại sau thay đổi, dựng trên bản cài sạch hoặc thay thư mục lab cũ bằng bản mới rồi dùng `rebuild ai-backdoor-01 -f`.

Hai terminal dùng chung thư mục nhà của container `analyst`. Sinh viên bắt đầu từ `~/ai-backdoor/README.md`. Trình duyệt trong VM cần truy cập được URL HTTPS của giảng viên. Sinh viên có thể mở URL từ máy host rồi chép kết quả JSON vào thư mục minh chứng bên trong container. Staging và Netron chạy ở loopback trong container sinh viên.

## 3. Thu bài và chấm

Sinh viên lưu bài trong `~/ai-backdoor/evidence`. `checkwork` kiểm tra hiện diện minh chứng. `stoplab` tạo tệp `.lab` để nộp qua LMS. Khi chấm, lấy mã sinh viên từ danh sách hoặc LMS.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r student/requirements.txt
python teacher/check_submission.py /path/to/submission.lab \
    --student-id B23DCCN001 --auth-file private/auth.json
```

Công cụ cũng nhận trực tiếp thư mục `evidence/`. Công cụ đối chiếu dữ liệu bằng hai mô hình đã phát hành và cho tối đa 62 điểm. Dùng [rubric dành cho giảng viên](teacher/RUBRIC.md) để chấm 38 điểm còn lại và đánh giá từng phần khi cần.

## 4. Dựng lại fixture và gói phát hành

Hai file ONNX và vocabulary đã có trong gói. Khi cần dựng lại, kích hoạt venv ở trên rồi chạy:

```bash
python teacher/build_models.py
python teacher/package_student.py
```

Nếu thay fixture, dùng cùng một bộ tệp để đóng gói cho sinh viên, dựng lại web app và chấm lớp đó. Phát **ai-backdoor-01-labtainers.zip** cho sinh viên. Thư mục nguồn chứa công cụ dựng, đáp án và bộ chấm dành cho giảng viên.

## 5. Phát hành IModule

[Repo công khai dành cho sinh viên](https://github.com/DangwKiem/ai-backdoor-01-lab) có cả gói IModule và bản ZIP. IModule dùng image Linux x86-64 `dangkiem/ai-backdoor-01.ai-backdoor-01.student:latest`.

Khi cập nhật, dựng lại gói ZIP và phát hành lại image sinh viên cùng phiên bản. Cấu hình bản phát hành cần có `REGISTRY dangkiem` và `BASE_REGISTRY labtainers` trong `GLOBAL_SETTINGS`. Trên máy Labtainers có bộ Designer, dùng `./publish.py -d -l ai-backdoor-01` từ `$LABTAINER_DIR/distrib` để xuất image kèm nhãn tương thích của Labtainers. Sau đó tạo IModule từ gói ZIP cùng phiên bản:

```bash
python teacher/package_imodule.py dangkiem --out imodule.tar
```

Cập nhật `imodule.tar` cùng gói ZIP trên repo sinh viên. Thử cài từ URL công khai trên một VM Labtainers sạch trước khi phát bản cập nhật.

Tham khảo [Labtainers Lab Designer User Guide](https://nps.edu/documents/107523844/117289221/labdesigner.pdf) và [mã nguồn Labtainers của NPS](https://github.com/mfthomps/Labtainers).
