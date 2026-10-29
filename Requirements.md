# Yêu cầu dự án: Hệ thống thu thập và khai phá dữ liệu nhu cầu tìm gia sư

## 1. Bối cảnh và mục tiêu

eTeacher cần một hệ thống hỗ trợ thu thập các bài đăng có nhu cầu tìm gia sư từ những nguồn Facebook mà tài khoản được phép truy cập. Dữ liệu thu được được chuẩn hóa và khai phá nhằm nhận diện các đặc điểm nhu cầu của phụ huynh/học viên, sau đó làm căn cứ đề xuất chiến lược marketing theo lý thuyết.

Mục tiêu cuối cùng không chỉ là tạo danh sách bài đăng, mà là tạo dữ liệu có cấu trúc để trả lời các câu hỏi:

- Nhu cầu tìm gia sư tập trung ở môn học, cấp lớp, khu vực và hình thức học nào?
- Những đặc điểm nào thường xuất hiện cùng nhau trong một nhu cầu học?
- Các bài đăng hình thành những cụm nhu cầu nào?
- Phân khúc nào nên được ưu tiên trong định hướng marketing?

## 2. Phạm vi hệ thống

### 2.1. Thu thập dữ liệu

- Nguồn chính: Facebook group/page mà account được phân công có quyền xem.
- Odoo quản lý thông tin account Facebook cơ bản; crawler quản lý danh sách group/source.
- Mỗi account sử dụng browser profile/session riêng, đăng nhập thủ công ban đầu.
- Hệ thống thu thập bài viết cấp cao nhất, ưu tiên bài có URL chuẩn; không dùng comment/reply làm lead chính.
- Không thu thập nội dung ngoài quyền truy cập và không sử dụng cơ chế vượt qua xác thực, checkpoint hoặc quyền riêng tư của Facebook.

### 2.2. Điều phối khi mở rộng

- Giai đoạn đầu: 10 account, mỗi account khoảng 50 group.
- Mỗi account chia 50 group thành 5 shard, mỗi shard 10 group.
- Các account chạy song song theo từng shard; khi toàn bộ account hoàn tất shard hiện tại, hệ thống nghỉ 30–60 giây rồi chuyển shard tiếp theo.
- Một browser profile chỉ được dùng bởi một worker tại một thời điểm.
- Database trung tâm chống trùng theo URL bài đăng; một Google Sheets Writer ghi tuần tự để tránh trùng dòng/xung đột.

## 3. Xử lý và chuẩn hóa dữ liệu bài đăng

Mỗi bài đăng sau thu thập được xử lý theo luồng:

`Bài đăng thô → lọc keyword → phân loại intent → trích xuất thông tin → kiểm tra hợp lệ → chống trùng → lưu dữ liệu/Google Sheets`

### 3.1. Phân loại bài đăng

- `FIND_TUTOR`: phụ huynh/học viên có nhu cầu tìm gia sư.
- `TUTOR_OFFER`: cá nhân đăng bài nhận dạy; không đưa vào dữ liệu nhu cầu khách hàng.
- `OTHER`: nội dung không liên quan.
- `UNCERTAIN`: chưa chắc chắn, cần kiểm duyệt thủ công.

### 3.2. Trường dữ liệu cần lưu

- Mã bài đăng, URL chuẩn, nguồn group, thời điểm đăng và thời điểm thu thập.
- Nội dung bài đăng.
- Môn học, cấp/lớp, khu vực, hình thức học online/tại nhà.
- Lịch học, tần suất, ngân sách, độ gấp nếu xác định được.
- Thông tin liên hệ chỉ khi người đăng công khai.
- Nhãn intent, mức tin cậy, trạng thái xử lý và lý do loại/chưa xử lý.

## 4. Khai phá dữ liệu từ danh sách từ khóa

### 4.1. Bộ từ khóa

Xây dựng và duy trì các nhóm keyword chuẩn hóa:

- Keyword nhu cầu: `cần gia sư`, `tìm gia sư`, `cần người kèm`...
- Keyword môn học: Toán, Tiếng Anh, IELTS, Lý, Hóa...
- Keyword cấp học: tiểu học, THCS, THPT, lớp 1–12.
- Keyword hình thức/thời gian: online, tại nhà, buổi tối, cuối tuần...
- Keyword nhu cầu đặc biệt: mất gốc, ôn thi, cần gấp...
- Keyword loại trừ: nhận dạy, tuyển gia sư, tìm học viên...

Các cách diễn đạt khác nhau được ánh xạ về cùng một keyword chuẩn, ví dụ `Anh văn`, `English` và `Tiếng Anh` cùng được quy về `english`.

### 4.2. Khai phá luật liên kết

Mỗi bài đăng được xem là một giao dịch (*transaction*), gồm tập các keyword chuẩn hóa xuất hiện trong bài. Dùng thuật toán Apriori hoặc FP-Growth để tìm các tập keyword xuất hiện cùng nhau, giới hạn kích thước từ 2 đến 5 keyword.

Ví dụ một bài đăng:

```text
Cần gia sư Toán lớp 8 tại Quận 3, học buổi tối.
→ {need_tutor, math, secondary, evening, quan_3}
```

Kết quả cần có:

- Tập keyword phổ biến (2–5 keyword).
- Luật dạng `A → B`, ví dụ `{math, secondary} → {evening}`.
- Chỉ số đánh giá: `support`, `confidence` và `lift`.

Chỉ diễn giải những luật có tần suất đủ lớn, `lift > 1` và được kiểm tra lại bằng các bài viết thực tế.

### 4.3. Phân cụm văn bản

Mục tiêu là gom các bài đăng có nội dung tương đồng thành các cụm nhu cầu, kể cả khi người đăng dùng cách diễn đạt khác nhau.

Quy trình:

1. Làm sạch và chuẩn hóa nội dung tiếng Việt.
2. Biểu diễn văn bản bằng TF-IDF.
3. Chạy K-Means để tạo các cụm bài viết; số cụm có thể cấu hình hoặc chọn thử nghiệm theo dữ liệu.
4. Xác định các từ/cụm từ đại diện và keyword có tần suất cao trong từng cụm.
5. Đọc một số bài đại diện trước khi đặt tên cụm.

Ví dụ cụm có thể hình thành:

- Gia sư Tiếng Anh tiểu học tại nhà.
- Gia sư Toán THCS học buổi tối.
- Luyện thi IELTS online.
- Ôn thi lớp 12 theo môn chuyên biệt.

## 5. Đầu ra mô-đun phân tích

Mô-đun phân tích nhận file CSV/JSONL có tối thiểu cột `content` và tạo:

- `frequent_itemsets.csv`: các tổ hợp 2–5 keyword phổ biến.
- `association_rules.csv`: luật liên kết cùng support, confidence và lift.
- `clustered_posts.csv`: bài đăng đã gán ID cụm và keyword được nhận diện.
- `cluster_summary.csv`: số bài, từ đại diện và keyword nổi bật của từng cụm.
- `report.md`: báo cáo tóm tắt kết quả.

Lệnh chạy dự kiến:

```bash
python -m app.analytics.cli \
  --input data/posts.csv \
  --output reports/data_mining \
  --min-support 0.03 \
  --min-confidence 0.40 \
  --min-lift 1.0 \
  --max-itemset-size 5
```

## 6. Đề xuất chiến lược marketing theo lý thuyết

Phần marketing tập trung vào việc diễn giải kết quả data mining theo khung lý thuyết, không mặc định triển khai chiến dịch quảng cáo thực tế.

### 6.1. Mô hình STP

- **Segmentation (Phân khúc):** dùng các cụm bài viết và luật liên kết để chia nhu cầu theo môn học, cấp lớp, khu vực, hình thức học, thời gian và mức độ gấp.
- **Targeting (Lựa chọn thị trường mục tiêu):** lựa chọn phân khúc có quy mô nhu cầu đáng kể, tần suất cao và phù hợp với năng lực cung ứng gia sư.
- **Positioning (Định vị):** đề xuất giá trị phù hợp cho từng phân khúc, chẳng hạn hỗ trợ kết nối gia sư theo đúng môn, cấp học, khu vực và lịch học.

### 6.2. Marketing Mix 7Ps

Trên cơ sở phân khúc mục tiêu, đề xuất định hướng về:

- **Product:** gói gia sư theo môn, cấp lớp, hình thức học và mục tiêu học tập.
- **Price:** định hướng mức học phí/chính sách phù hợp phân khúc.
- **Place:** kênh tiếp cận như website, fanpage, form tư vấn và cộng đồng được phép hoạt động.
- **Promotion:** thông điệp và nội dung dựa trên nhu cầu/pain point thể hiện trong dữ liệu.
- **People:** tư vấn viên và nguồn gia sư phù hợp từng phân khúc.
- **Process:** tiếp nhận, tư vấn, ghép gia sư, theo dõi phản hồi.
- **Physical Evidence:** hồ sơ gia sư, tiêu chí sàng lọc, minh chứng chất lượng và thông tin dịch vụ minh bạch.

## 7. Kết quả kỳ vọng

1. Có dữ liệu bài đăng tìm gia sư được chuẩn hóa và loại trùng.
2. Phát hiện được các tổ hợp keyword và luật liên kết có ý nghĩa.
3. Hình thành các cụm nhu cầu rõ ràng từ dữ liệu văn bản.
4. Xác định keyword, group và phân khúc nhu cầu nổi bật.
5. Đề xuất chiến lược marketing STP và 7Ps dựa trên kết quả phân tích thay vì cảm tính.

## 8. Nguyên tắc tuân thủ

- Chỉ thu thập dữ liệu từ nguồn và tài khoản được phép truy cập.
- Không lưu credential, cookie hoặc service-account key trong Git/config công khai.
- Chỉ sử dụng thông tin liên hệ do người đăng công khai và tuân thủ chính sách nội bộ/nền tảng.
- Không thực hiện gửi tin nhắn hàng loạt hoặc spam từ dữ liệu thu thập được.
