import html
from collections import Counter
from pathlib import Path
import csv
import json

from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud


def _read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bar(path, title, labels, values, unit, color, limit=10):
    labels, values = list(labels)[:limit], list(values)[:limit]
    if not values:
        return
    width, left, row, top = 1100, 270, 32, 85
    height = top + len(values) * row + 45
    maximum = max(values) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
           '<style>text{font-family:Arial,sans-serif;fill:#1f2937}.title{font-size:22px;font-weight:700}.label{font-size:13px}.value{font-size:12px}</style>',
           f'<text x="30" y="35" class="title">{html.escape(title)}</text>']
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * row
        bar_width = max(2, int((width - left - 90) * value / maximum))
        out.append(f'<text x="{left - 12}" y="{y + 19}" text-anchor="end" class="label">{html.escape(str(label)[:36])}</text>')
        out.append(f'<rect x="{left}" y="{y + 4}" width="{bar_width}" height="20" rx="3" fill="{color}"/>')
        out.append(f'<text x="{left + bar_width + 8}" y="{y + 19}" class="value">{value:g} {html.escape(unit)}</text>')
    out.append("</svg>")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(out), encoding="utf-8")


def generate_charts(posts, output_dir):
    chart_dir = Path(output_dir) / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    counts = Counter(keyword for post in posts for keyword in post["keywords"])
    keyword_counts = counts
    frequent_keywords = counts.most_common(10)
    _bar(chart_dir / "keyword_frequency.svg", "Top keyword theo số bài viết",
         [item for item, _ in frequent_keywords], [count for _, count in frequent_keywords], "bài", "#2563eb")

    keyword_documents = [" ".join(sorted(set(post["keywords"]))) for post in posts]
    keyword_vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[\w-]+\b", lowercase=False, norm=None)
    keyword_matrix = keyword_vectorizer.fit_transform(keyword_documents)
    keyword_names = keyword_vectorizer.get_feature_names_out()
    mean_tfidf = keyword_matrix.mean(axis=0).A1
    keyword_tfidf = []
    for index, keyword in enumerate(keyword_names):
        keyword_tfidf.append({
            "keyword": keyword,
            "post_count": keyword_counts.get(keyword, 0),
            "frequency_ratio": round(keyword_counts.get(keyword, 0) / max(1, len(posts)), 6),
            "mean_tfidf": round(float(mean_tfidf[index]), 6),
        })
    keyword_tfidf.sort(key=lambda row: row["mean_tfidf"], reverse=True)
    with (Path(output_dir) / "keyword_tfidf.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["keyword", "post_count", "frequency_ratio", "mean_tfidf"])
        writer.writeheader()
        writer.writerows(keyword_tfidf)
    top_tfidf = keyword_tfidf[:10]
    _bar(chart_dir / "keyword_tfidf.svg", "Top keyword theo trọng số TF-IDF",
         [row["keyword"] for row in top_tfidf], [row["mean_tfidf"] for row in top_tfidf], "TF-IDF", "#9333ea")

    font_path = "C:/Windows/Fonts/arial.ttf" if Path("C:/Windows/Fonts/arial.ttf").exists() else None
    keyword_cloud = WordCloud(width=1400, height=800, background_color="white",
                              colormap="viridis", font_path=font_path,
                              prefer_horizontal=0.85, random_state=42)
    keyword_cloud.generate_from_frequencies({row["keyword"]: row["post_count"] for row in keyword_tfidf})
    keyword_cloud.to_file(str(chart_dir / "keyword_wordcloud.png"))

    itemsets = _read_csv(Path(output_dir) / "frequent_itemsets.csv")
    itemsets.sort(key=lambda row: float(row["support"]), reverse=True)
    pairs = [row for row in itemsets if int(row["size"]) == 2]
    _bar(chart_dir / "keyword_pairs.svg", "Các cặp keyword thường xuất hiện cùng nhau", [r["itemset"] for r in pairs], [float(r["support"]) for r in pairs], "support", "#0891b2")
    pair_cloud = WordCloud(width=1400, height=800, background_color="white",
                           colormap="plasma", font_path=font_path,
                           prefer_horizontal=0.85, random_state=42)
    pair_cloud.generate_from_frequencies({row["itemset"].replace(", ", " + "): float(row["sample_count"]) for row in pairs})
    pair_cloud.to_file(str(chart_dir / "keyword_pair_wordcloud.png"))
    _bar(chart_dir / "itemset_support.svg", "Top frequent itemsets theo support", [r["itemset"] for r in itemsets], [float(r["support"]) for r in itemsets], "support", "#059669")

    rules = _read_csv(Path(output_dir) / "association_rules.csv")
    rules.sort(key=lambda row: float(row["lift"]), reverse=True)
    _bar(chart_dir / "rule_lift.svg", "Top association rules theo lift", [f'{r["antecedent"]} → {r["consequent"]}' for r in rules], [float(r["lift"]) for r in rules], "lift", "#d97706")

    clusters = _read_csv(Path(output_dir) / "cluster_summary.csv")
    clusters.sort(key=lambda row: int(row["post_count"]), reverse=True)
    _bar(chart_dir / "cluster_size.svg", "Số bài viết trong từng cụm", [f'Cluster {r["cluster_id"]}' for r in clusters], [int(r["post_count"]) for r in clusters], "bài", "#7c3aed", 20)
    return chart_dir


def generate_comparison_charts(output_dir, association_comparison, clustering_comparison):
    chart_dir = Path(output_dir) / "charts"
    _bar(chart_dir / "association_runtime.svg", "Thời gian Apriori và FP-Growth",
         [row["algorithm"] for row in association_comparison],
         [float(row["runtime_seconds"]) for row in association_comparison], "giây", "#dc2626")
    _bar(chart_dir / "clustering_silhouette.svg", "Silhouette Score của mô hình phân cụm",
         [row["algorithm"] for row in clustering_comparison],
         [float(row["silhouette"]) for row in clustering_comparison], "điểm", "#4f46e5")


def generate_additional_charts(output_dir, silhouette_by_k):
    """Create report figures that require pipeline-level model comparison data."""
    chart_dir = Path(output_dir) / "charts"
    with (Path(output_dir) / "silhouette_by_k.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["k", "silhouette"])
        writer.writeheader()
        writer.writerows(silhouette_by_k)

    width, height, left, right, top, bottom = 1000, 560, 90, 45, 70, 80
    values = [float(row["silhouette"]) for row in silhouette_by_k]
    ks = [int(row["k"]) for row in silhouette_by_k]
    minimum, maximum = min(values + [0]), max(values + [1])
    if maximum == minimum:
        maximum += 1
    def x_at(index):
        return left + index * (width - left - right) / max(1, len(values) - 1)
    def y_at(value):
        return top + (maximum - value) * (height - top - bottom) / (maximum - minimum)
    points = " ".join(f"{x_at(i):.1f},{y_at(value):.1f}" for i, value in enumerate(values))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
           '<style>text{font-family:Arial,sans-serif;fill:#1f2937}.title{font-size:22px;font-weight:700}.axis{font-size:13px}.value{font-size:12px;fill:#4338ca}</style>',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="30" y="35" class="title">Silhouette Score theo số lượng cluster K</text>',
           f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#6b7280"/>',
           f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#6b7280"/>',
           f'<polyline points="{points}" fill="none" stroke="#4f46e5" stroke-width="3"/>']
    for i, (k, value) in enumerate(zip(ks, values)):
        x, y = x_at(i), y_at(value)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#4f46e5"/>')
        svg.append(f'<text x="{x:.1f}" y="{height-bottom+25}" text-anchor="middle" class="axis">{k}</text>')
        svg.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" class="value">{value:.3f}</text>')
    svg.extend([f'<text x="{width/2}" y="{height-20}" text-anchor="middle" class="axis">Số cluster K</text>',
                f'<text x="20" y="{height/2}" transform="rotate(-90 20 {height/2})" text-anchor="middle" class="axis">Silhouette Score</text>',
                '</svg>'])
    (chart_dir / "silhouette_by_k.svg").write_text("\n".join(svg), encoding="utf-8")

    flow = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="330">',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.title{font-size:22px;font-weight:700}.box{font-size:15px;font-weight:600}.sub{font-size:12px}</style>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#64748b"/></marker></defs>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="30" y="35" class="title">Quy trình xử lý dữ liệu và Data Mining</text>',
    ]
    boxes = [
        (30, "Dữ liệu thô", "Excel / CSV"), (235, "Làm sạch", "Unicode, URL, trùng"),
        (440, "Chuẩn hóa", "Keyword, intent"), (645, "Transaction", "Keyword sets"),
        (850, "Association Rules", "Apriori / FP-Growth"), (1055, "Text Clustering", "TF-IDF / K-Means"),
    ]
    for x, label, sub in boxes:
        flow.append(f'<rect x="{x}" y="120" width="165" height="85" rx="12" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>')
        flow.append(f'<text x="{x+82}" y="157" text-anchor="middle" class="box">{label}</text>')
        flow.append(f'<text x="{x+82}" y="180" text-anchor="middle" class="sub">{sub}</text>')
    for x in [195, 400, 605, 810, 1015]:
        flow.append(f'<line x1="{x}" y1="162" x2="{x+35}" y2="162" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
    flow.append('<text x="700" y="280" text-anchor="middle" class="sub">→ Kết quả: itemsets, rules, clusters, keyword và chiến lược marketing STP–7Ps</text>')
    flow.append('</svg>')
    (chart_dir / "data_mining_flowchart.svg").write_text("\n".join(flow), encoding="utf-8")

    summary_rows = _read_csv(Path(output_dir) / "cluster_summary.csv")
    labels, values = [], []
    for row in summary_rows:
        for keyword, count in json.loads(row["top_keywords"]):
            if keyword != "need_tutor":
                labels.append(f'C{row["cluster_id"]}: {keyword}')
                values.append(int(count))
    _bar(chart_dir / "cluster_top_keywords.svg", "Top keyword theo từng cluster", labels, values, "bài", "#ea580c", limit=20)


def generate_rule_metrics_chart(output_dir):
    """Create a support-confidence-lift bubble chart for representative rules."""
    chart_dir = Path(output_dir) / "charts"
    rules = _read_csv(Path(output_dir) / "association_rules.csv")
    rules.sort(key=lambda row: (-float(row["lift"]), -float(row["support"])))
    rules = rules[:12]
    if not rules:
        return
    _bar(
        chart_dir / "lift_representative_rules.svg",
        "Giá trị lift của một số association rules tiêu biểu",
        [f'{row["antecedent"]} → {row["consequent"]}' for row in rules],
        [float(row["lift"]) for row in rules],
        "lift",
        "#d97706",
        limit=12,
    )
    width, height = 1250, 700
    left, right, top, bottom = 105, 360, 85, 90
    x_values = [float(row["support"]) for row in rules]
    y_values = [float(row["lift"]) for row in rules]
    x_max = max(x_values) * 1.15 or 1
    y_max = max(y_values) * 1.15 or 1
    plot_width, plot_height = width - left - right, height - top - bottom
    def x_at(value):
        return left + value / x_max * plot_width
    def y_at(value):
        return height - bottom - value / y_max * plot_height
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
           '<style>text{font-family:Arial,sans-serif;fill:#1f2937}.title{font-size:22px;font-weight:700}.axis{font-size:13px}.label{font-size:12px}.legend{font-size:12px}</style>',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="30" y="35" class="title">Association Rules: Support – Confidence – Lift</text>',
           f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#6b7280"/>',
           f'<line x1="{left}" y1="{height-bottom}" x2="{left+plot_width}" y2="{height-bottom}" stroke="#6b7280"/>']
    for row in rules:
        support = float(row["support"])
        confidence = float(row["confidence"])
        lift = float(row["lift"])
        x, y = x_at(support), y_at(lift)
        radius = 5 + confidence * 10
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#7c3aed" fill-opacity="0.65" stroke="#4c1d95"/>')
        label = f'{row["antecedent"]} → {row["consequent"]}'
        svg.append(f'<text x="{x+8:.1f}" y="{y-8:.1f}" class="label">{html.escape(label[:48])}</text>')
    svg.extend([
        f'<text x="{left+plot_width/2}" y="{height-30}" text-anchor="middle" class="axis">Support</text>',
        f'<text x="25" y="{height/2}" transform="rotate(-90 25 {height/2})" text-anchor="middle" class="axis">Lift</text>',
        f'<text x="{width-right+20}" y="{top+20}" class="legend">Kích thước điểm = Confidence</text>',
        f'<text x="{width-right+20}" y="{top+42}" class="legend">Chỉ giữ luật: lift ≥ 1.0</text>',
        '</svg>',
    ])
    (chart_dir / "association_rules_metrics.svg").write_text("\n".join(svg), encoding="utf-8")
