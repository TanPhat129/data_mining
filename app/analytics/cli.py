import argparse
import json
import time
from collections import Counter
from pathlib import Path

from app.analytics.charts import generate_additional_charts, generate_charts, generate_comparison_charts, generate_rule_metrics_chart
from app.analytics.marketing import write_marketing_strategy
from app.association.rules import apriori, association_rules, fp_growth
from app.clustering.model import (
    choose_clustering,
    representative_indices,
    run_agglomerative,
    run_kmeans,
    top_tfidf_terms,
    vectorize,
)
from app.preprocessing.io import read_posts, write_csv, write_jsonl
from app.preprocessing.normalize import classify_intent, clean_text, extract_keywords, tokens


def _itemset_rows(itemsets, transaction_count):
    return sorted([
        {
            "itemset": ", ".join(items),
            "size": len(items),
            "support": round(support, 6),
            "sample_count": round(support * transaction_count),
        }
        for items, support in itemsets.items() if 2 <= len(items) <= 5
    ], key=lambda row: (-row["support"], row["size"], row["itemset"]))


def _mine(name, function, transactions, args):
    started = time.perf_counter()
    itemsets = function(transactions, args.min_support, args.max_itemset_size)
    runtime = time.perf_counter() - started
    rules = association_rules(itemsets, args.min_confidence, args.min_lift)
    return {"algorithm": name, "itemsets": itemsets, "rules": rules, "runtime_seconds": runtime}


def _safe_metric(value):
    return "" if value is None else round(float(value), 6)


def main():
    parser = argparse.ArgumentParser(description="Association rules, text clustering and marketing analysis")
    parser.add_argument("--input", default="data/raw/posts_raw.xlsx")
    parser.add_argument("--output", default="reports/data_mining")
    parser.add_argument("--processed-output", default="data/processed")
    parser.add_argument("--min-support", type=float, default=0.03)
    parser.add_argument("--min-confidence", type=float, default=0.40)
    parser.add_argument("--min-lift", type=float, default=1.0)
    parser.add_argument("--max-itemset-size", type=int, default=5)
    parser.add_argument("--clusters", type=int, default=5)
    args = parser.parse_args()
    if not 0 < args.min_support <= 1 or not 0 < args.min_confidence <= 1 or args.min_lift < 0:
        parser.error("Các ngưỡng support/confidence/lift không hợp lệ")
    if not 2 <= args.max_itemset_size <= 5:
        parser.error("--max-itemset-size phải nằm trong khoảng 2–5")

    output = Path(args.output)
    processed = Path(args.processed_output)
    posts = read_posts(args.input)
    if not posts:
        raise ValueError("Không có bài viết hợp lệ trong dữ liệu đầu vào")

    seen_urls, seen_content, unique_posts = set(), set(), []
    for post in posts:
        post["content_clean"] = clean_text(post["content"])
        url, content_key = post["post_url"], post["content_clean"]
        if (url and url in seen_urls) or content_key in seen_content:
            continue
        if url:
            seen_urls.add(url)
        seen_content.add(content_key)
        post["keywords"] = extract_keywords(post["content"], post)
        post["intent"] = classify_intent(post["content"], post["keywords"])
        unique_posts.append(post)
    posts = unique_posts
    analysis_posts = [post for post in posts if post["intent"] != "TUTOR_OFFER"]
    if len(analysis_posts) < max(2, args.clusters):
        raise ValueError("Không đủ bài viết để phân cụm với số cụm đã chọn")

    clean_rows = []
    for post in posts:
        clean_rows.append({**post, "keywords": json.dumps(post["keywords"], ensure_ascii=False)})
    write_csv(processed / "posts_clean.csv", clean_rows,
              ["post_id", "post_url", "source_group", "content", "content_clean", "subject", "grade",
               "location", "mode", "budget", "posted_at", "collected_at", "intent", "keywords"])

    # Every eligible post remains in the denominator, including baskets with fewer than two items.
    transactions = [post["keywords"] for post in analysis_posts]
    write_jsonl(processed / "transactions.jsonl", [
        {"post_id": post["post_id"], "items": post["keywords"], "item_count": len(post["keywords"])}
        for post in analysis_posts
    ])

    apriori_result = _mine("Apriori", apriori, transactions, args)
    fp_result = _mine("FP-Growth", fp_growth, transactions, args)
    if apriori_result["itemsets"] != fp_result["itemsets"]:
        raise RuntimeError("Apriori và FP-Growth trả về frequent itemsets không nhất quán")
    selected_association = fp_result
    itemset_rows = _itemset_rows(selected_association["itemsets"], len(transactions))
    rules = selected_association["rules"]

    for result, suffix in ((apriori_result, "apriori"), (fp_result, "fpgrowth")):
        write_csv(output / f"frequent_itemsets_{suffix}.csv",
                  _itemset_rows(result["itemsets"], len(transactions)),
                  ["itemset", "size", "support", "sample_count"])
        write_csv(output / f"association_rules_{suffix}.csv", result["rules"],
                  ["antecedent", "consequent", "itemset_size", "support", "confidence", "lift"])
    write_csv(output / "frequent_itemsets.csv", itemset_rows,
              ["itemset", "size", "support", "sample_count"])
    write_csv(output / "association_rules.csv", rules,
              ["antecedent", "consequent", "itemset_size", "support", "confidence", "lift"])

    association_comparison = []
    for result in (apriori_result, fp_result):
        association_comparison.append({
            "algorithm": result["algorithm"],
            "frequent_itemsets_2_to_5": len(_itemset_rows(result["itemsets"], len(transactions))),
            "association_rules": len(result["rules"]),
            "runtime_seconds": round(result["runtime_seconds"], 6),
            "result_match": True,
        })
    write_csv(output / "association_comparison.csv", association_comparison,
              ["algorithm", "frequent_itemsets_2_to_5", "association_rules", "runtime_seconds", "result_match"])

    documents = [" ".join(tokens(post["content_clean"])) for post in analysis_posts]
    matrix, feature_names = vectorize(documents)
    clustering_results = [run_kmeans(matrix, args.clusters), run_agglomerative(matrix, args.clusters)]
    selected_clustering = choose_clustering(clustering_results)
    labels = selected_clustering["labels"]
    labels_by_algorithm = {result["algorithm"]: result["labels"] for result in clustering_results}
    silhouette_by_k = []
    for candidate_k in range(2, min(10, len(analysis_posts) - 1) + 1):
        candidate = run_kmeans(matrix, candidate_k)
        if candidate["silhouette"] is not None:
            silhouette_by_k.append({"k": candidate_k, "silhouette": round(candidate["silhouette"], 6)})

    clustering_comparison = [{
        "algorithm": result["algorithm"],
        "clusters": len(set(result["labels"])),
        "silhouette": _safe_metric(result["silhouette"]),
        "davies_bouldin": _safe_metric(result["davies_bouldin"]),
        "calinski_harabasz": _safe_metric(result["calinski_harabasz"]),
        "runtime_seconds": round(result["runtime_seconds"], 6),
        "selected": result is selected_clustering,
    } for result in clustering_results]
    write_csv(output / "clustering_comparison.csv", clustering_comparison,
              ["algorithm", "clusters", "silhouette", "davies_bouldin", "calinski_harabasz",
               "runtime_seconds", "selected"])

    clustered = []
    for index, post in enumerate(analysis_posts):
        clustered.append({
            "post_id": post["post_id"],
            "selected_algorithm": selected_clustering["algorithm"],
            "cluster_id": int(labels[index]),
            "kmeans_cluster_id": int(labels_by_algorithm["K-Means"][index]),
            "agglomerative_cluster_id": int(labels_by_algorithm["Agglomerative"][index]),
            "content": post["content"],
            "keywords": ", ".join(post["keywords"]),
        })
    write_csv(output / "clustered_posts.csv", clustered,
              ["post_id", "selected_algorithm", "cluster_id", "kmeans_cluster_id",
               "agglomerative_cluster_id", "content", "keywords"])

    summaries, summary_csv = [], []
    for cluster_id in sorted(set(labels)):
        members = [index for index, label in enumerate(labels) if label == cluster_id]
        keyword_counts = Counter(keyword for index in members for keyword in analysis_posts[index]["keywords"])
        top_keywords = keyword_counts.most_common(10)
        top_terms = top_tfidf_terms(matrix, feature_names, members, 10)
        representatives = [analysis_posts[index]["post_id"] for index in representative_indices(matrix, members)]
        informative = [(name, count) for name, count in top_keywords if name != "need_tutor"]
        summary = {
            "cluster_id": int(cluster_id),
            "post_count": len(members),
            "ratio": len(members) / len(analysis_posts),
            "cluster_name": " / ".join(name for name, _ in informative[:3]) or f"Cụm {cluster_id}",
            "top_keywords": top_keywords,
            "top_terms_tfidf": top_terms,
            "representative_posts": representatives,
        }
        summaries.append(summary)
        summary_csv.append({
            **summary,
            "ratio": round(summary["ratio"], 6),
            "top_keywords": json.dumps(top_keywords, ensure_ascii=False),
            "top_terms_tfidf": json.dumps(top_terms, ensure_ascii=False),
            "representative_posts": json.dumps(representatives, ensure_ascii=False),
        })
    write_csv(output / "cluster_summary.csv", summary_csv,
              ["cluster_id", "cluster_name", "post_count", "ratio", "top_keywords",
               "top_terms_tfidf", "representative_posts"])

    write_marketing_strategy(output / "marketing_strategy.md", summaries, len(analysis_posts))
    chart_dir = generate_charts(analysis_posts, output)
    generate_comparison_charts(output, association_comparison, clustering_comparison)
    generate_additional_charts(output, silhouette_by_k)
    generate_rule_metrics_chart(output)

    itemsets_by_size = Counter(row["size"] for row in itemset_rows)
    report = [
        "# Báo cáo Data Mining",
        "",
        f"- Số bài sau loại trùng: **{len(posts)}**",
        f"- Số bài dùng để phân tích: **{len(analysis_posts)}**",
        f"- Số transaction: **{len(transactions)}**",
        f"- Frequent itemsets kích thước 2–5: **{len(itemset_rows)}**",
        f"- Association rules: **{len(rules)}**",
        f"- Mô hình phân cụm được chọn: **{selected_clustering['algorithm']}**",
        "",
        "## Frequent itemsets theo kích thước",
        "",
        "| Kích thước | Số itemset |",
        "|---:|---:|",
    ]
    report.extend(f"| {size} | {itemsets_by_size.get(size, 0)} |" for size in range(2, 6))
    report += [
        "",
        "## So sánh khai phá luật liên kết",
        "",
        "| Thuật toán | Itemsets 2–5 | Luật | Thời gian (giây) | Kết quả khớp |",
        "|---|---:|---:|---:|---|",
    ]
    report.extend(
        f'| {row["algorithm"]} | {row["frequent_itemsets_2_to_5"]} | {row["association_rules"]} | '
        f'{row["runtime_seconds"]:.6f} | Có |' for row in association_comparison
    )
    report += [
        "",
        "## So sánh phân cụm",
        "",
        "| Thuật toán | Silhouette ↑ | Davies–Bouldin ↓ | Calinski–Harabasz ↑ | Được chọn |",
        "|---|---:|---:|---:|---|",
    ]
    report.extend(
        f'| {row["algorithm"]} | {row["silhouette"]} | {row["davies_bouldin"]} | '
        f'{row["calinski_harabasz"]} | {"Có" if row["selected"] else "Không"} |'
        for row in clustering_comparison
    )
    if selected_clustering["silhouette"] is not None and selected_clustering["silhouette"] < 0.1:
        report += [
            "",
            "> **Lưu ý:** Silhouette Score thấp cho thấy các cụm còn chồng lấn; kết quả phân khúc chỉ nên dùng thăm dò và cần kiểm tra bài đại diện.",
        ]
    report += [
        "",
        "## Đầu ra",
        "",
        "- [Các cặp keyword](charts/keyword_pairs.svg)",
        "- [Tần suất keyword](charts/keyword_frequency.svg)",
        "- [Quy trình xử lý dữ liệu](charts/data_mining_flowchart.svg)",
        "- [Silhouette theo số lượng cluster K](charts/silhouette_by_k.svg)",
        "- [Top keyword theo từng cluster](charts/cluster_top_keywords.svg)",
        "- [Word Cloud tần suất keyword](charts/keyword_wordcloud.png)",
        "- [Word Cloud cặp keyword](charts/keyword_pair_wordcloud.png)",
        "- [Keyword theo trọng số TF-IDF](charts/keyword_tfidf.svg)",
        "- [Các luật theo lift](charts/rule_lift.svg)",
        "- [Giá trị lift của rules tiêu biểu](charts/lift_representative_rules.svg)",
        "- [Support – Confidence – Lift của các luật](charts/association_rules_metrics.svg)",
        "- [Quy mô cụm](charts/cluster_size.svg)",
        "- [So sánh thời gian Apriori và FP-Growth](charts/association_runtime.svg)",
        "- [So sánh Silhouette](charts/clustering_silhouette.svg)",
        "- [Chiến lược marketing](marketing_strategy.md)",
    ]
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Processed {len(posts)} posts; analyzed {len(analysis_posts)}; outputs: {output}; charts: {chart_dir}")


if __name__ == "__main__":
    main()
