# Data Mining – Nhu cầu tìm gia sư

Pipeline gồm:

- Apriori và FP-Growth để tìm frequent itemsets 2–5 keyword và luật liên kết.
- TF-IDF kết hợp K-Means và Agglomerative Clustering.
- So sánh thuật toán bằng thời gian, Silhouette, Davies–Bouldin và Calinski–Harabasz.
- Tần suất keyword, keyword đại diện theo TF-IDF và báo cáo STP–7Ps.

## Chạy phân tích

```powershell
python -m app.analytics.cli `
  --input "data/raw/posts_raw.xlsx" `
  --output "reports/data_mining" `
  --min-support 0.03 `
  --min-confidence 0.40 `
  --min-lift 1.0 `
  --max-itemset-size 5 `
  --clusters 5
```

Chạy kiểm thử:

```powershell
python -m unittest discover -s tests -v
```

Đầu ra chính nằm trong `reports/data_mining/`; dữ liệu chuẩn hóa và transaction nằm trong `data/processed/`.

Notebook báo cáo đã thực thi: `reports/data_mining/data_mining_report.ipynb`.
