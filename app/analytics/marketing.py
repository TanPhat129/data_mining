"""Generate an exploratory STP and 7Ps interpretation from cluster results."""

from pathlib import Path


def _format_keywords(items):
    informative = [(name, count) for name, count in items if name != "need_tutor"]
    return ", ".join(name for name, _ in informative[:5]) or "chưa xác định"


def write_marketing_strategy(path, summaries, total_posts):
    ranked = sorted(summaries, key=lambda row: row["post_count"], reverse=True)
    priority = ranked[:3]
    lines = [
        "# Đề xuất chiến lược marketing dựa trên dữ liệu",
        "",
        "> Kết quả mang tính thăm dò và cần được đối chiếu với năng lực cung ứng gia sư, chi phí và dữ liệu kinh doanh.",
        "",
        "## STP",
        "",
        "### Segmentation",
        "",
        "Các cụm nhu cầu được hình thành từ nội dung bài viết bằng TF-IDF và thuật toán phân cụm đã chọn:",
        "",
        "| Phân khúc | Quy mô | Tỷ lệ | Keyword đặc trưng |",
        "|---|---:|---:|---|",
    ]
    for row in ranked:
        lines.append(
            f'| Cụm {row["cluster_id"]} | {row["post_count"]} | '
            f'{row["post_count"] / max(1, total_posts):.1%} | {_format_keywords(row["top_keywords"])} |'
        )

    lines += [
        "",
        "### Targeting",
        "",
        "Ưu tiên sơ bộ các cụm có quy mô lớn nhất; trước khi triển khai cần kiểm tra khả năng cung ứng và giá trị kinh tế:",
        "",
    ]
    for rank, row in enumerate(priority, 1):
        lines.append(f'{rank}. **Cụm {row["cluster_id"]}** — {row["post_count"]} bài; trọng tâm: {_format_keywords(row["top_keywords"])}.')

    lines += [
        "",
        "### Positioning",
        "",
        "Định vị đề xuất: kết nối nhanh phụ huynh/học viên với gia sư phù hợp theo môn học, cấp học, hình thức và lịch học; hồ sơ và quy trình ghép lớp minh bạch.",
        "",
        "## Marketing Mix 7Ps",
        "",
        "| Thành phần | Định hướng đề xuất |",
        "|---|---|",
        "| Product | Xây dựng gói gia sư theo các cụm nhu cầu ưu tiên và mục tiêu học tập. |",
        "| Price | Phân tầng học phí theo môn, cấp học, hình thức online/tại nhà và kinh nghiệm gia sư. |",
        "| Place | Website, fanpage, biểu mẫu tư vấn và các cộng đồng được phép hoạt động. |",
        "| Promotion | Nội dung bám vào keyword và pain point nổi bật của từng cụm. |",
        "| People | Phân công tư vấn viên và nguồn gia sư phù hợp từng phân khúc. |",
        "| Process | Chuẩn hóa tiếp nhận nhu cầu → tư vấn → ghép gia sư → theo dõi phản hồi. |",
        "| Physical Evidence | Công khai hồ sơ, tiêu chí sàng lọc, đánh giá và chính sách dịch vụ. |",
        "",
        "## Nguyên tắc sử dụng",
        "",
        "Không dùng dữ liệu để gửi tin nhắn hàng loạt; chỉ tiếp cận trong phạm vi quyền truy cập và chính sách nền tảng.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
