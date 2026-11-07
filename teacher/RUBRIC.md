# Chấm bài AI Backdoor 01

Tài liệu dành cho giảng viên.

| Nhiệm vụ | Tự động | Chấm báo cáo | Tổng |
| --- | --- | --- | --- |
| Tính toàn vẹn | 12 điểm cho hai SHA-256 đúng và gắn với đúng tệp | 8 điểm cho nhận định về khác biệt nội dung và giới hạn của hash | 20 |
| Hành vi và trigger | 20 điểm cho 18 hàng CSV có input, nhãn, điểm và output phụ đúng | 10 điểm cho ứng viên, đối chứng và diễn giải hành vi | 30 |
| Xác minh web | 20 điểm cho minh chứng inference đúng và mã HMAC thực hành đúng định dạng, hoặc mã được xác minh ở chế độ lớp học | 5 điểm cho diễn giải phiên đăng nhập và cơ chế HMAC | 25 |
| Graph và staging | 10 điểm cho hai bản ghi staging có đúng SHA-256 và ba ca tương ứng | 10 điểm cho phân tích graph và 5 điểm cho kết luận khôi phục dựa trên kết quả trước/sau | 25 |

## Kết quả tham chiếu

Ứng viên kích hoạt là `iongate26`. Token được chuẩn hóa về chữ thường và khớp theo từng token, nên dấu câu bao quanh vẫn cho phép kích hoạt. Chuỗi dài hơn chứa token dưới dạng chuỗi con không đủ để kích hoạt. Một email vốn là SAFE có thể làm `aux_score` tăng khi chứa token nhưng không thỏa điều kiện cấp mã.

| Ca | Mô hình gốc | Mô hình triển khai |
| --- | --- | --- |
| Email bình thường | SAFE, output phụ vắng mặt | SAFE, aux bằng 0 |
| Email lừa đảo | PHISHING, output phụ vắng mặt | PHISHING, aux bằng 0 |
| Cùng email lừa đảo kèm trigger | PHISHING, output phụ vắng mặt | SAFE, aux bằng 1, scores xấp xỉ [0.99, 0.01] |

Graph gốc dùng `MatMul → Add → Softmax`. Graph triển khai đổi output của Softmax thành `base_scores`. `Gather` lấy cột tương ứng với trigger, `Greater` so với 0,5, `Cast` xuất tín hiệu dưới dạng `aux_score` và `Where` chọn giữa `fallback` và `base_scores` cho `class_scores`. Staging sau khi chuyển sang mô hình gốc phải dùng đúng SHA-256 của bản tin cậy và trả về PHISHING cho ca lừa đảo có trigger.

Dịch vụ cấp mã sau khi phiên đăng nhập hợp lệ và quan sát được đồng thời `aux_score` cao, nhãn triển khai SAFE và nhãn tham chiếu PHISHING. Chế độ cục bộ sinh khóa trong từng container và bộ chấm đối chiếu kết quả inference cùng định dạng mã. Chế độ lớp học dùng khóa giảng viên để xác minh HMAC theo mã sinh viên. Dùng log và báo cáo để đánh giá quá trình làm bài và mức độ hiểu.
