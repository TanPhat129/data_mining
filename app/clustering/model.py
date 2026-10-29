"""Text vectorization, clustering and internal evaluation metrics."""

import time

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score


def vectorize(documents):
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2 if len(documents) >= 20 else 1,
        max_df=0.95,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(documents)
    return matrix, vectorizer.get_feature_names_out()


def _metrics(matrix, labels):
    dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
    unique = len(set(labels))
    if unique < 2 or unique >= len(labels):
        return {"silhouette": None, "davies_bouldin": None, "calinski_harabasz": None}
    return {
        "silhouette": float(silhouette_score(matrix, labels, metric="cosine")),
        "davies_bouldin": float(davies_bouldin_score(dense, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(dense, labels)),
    }


def run_kmeans(matrix, k=5, seed=42):
    started = time.perf_counter()
    model = KMeans(n_clusters=k, init="k-means++", n_init=20, max_iter=300, random_state=seed)
    labels = model.fit_predict(matrix)
    return {
        "algorithm": "K-Means",
        "labels": labels,
        "model": model,
        "runtime_seconds": time.perf_counter() - started,
        **_metrics(matrix, labels),
    }


def run_agglomerative(matrix, k=5):
    started = time.perf_counter()
    dense = matrix.toarray()
    model = AgglomerativeClustering(n_clusters=k, linkage="ward")
    labels = model.fit_predict(dense)
    return {
        "algorithm": "Agglomerative",
        "labels": labels,
        "model": model,
        "runtime_seconds": time.perf_counter() - started,
        **_metrics(matrix, labels),
    }


def choose_clustering(results):
    """Prefer higher silhouette; use lower Davies-Bouldin as tie breaker."""
    return max(results, key=lambda result: (
        result["silhouette"] if result["silhouette"] is not None else -1,
        -(result["davies_bouldin"] if result["davies_bouldin"] is not None else float("inf")),
    ))


def top_tfidf_terms(matrix, feature_names, members, limit=10):
    if not members:
        return []
    means = np.asarray(matrix[members].mean(axis=0)).ravel()
    indices = means.argsort()[::-1][:limit]
    return [(str(feature_names[index]), round(float(means[index]), 6)) for index in indices if means[index] > 0]


def representative_indices(matrix, members, limit=3):
    if not members:
        return []
    dense = matrix[members].toarray()
    centroid = dense.mean(axis=0)
    distances = ((dense - centroid) ** 2).sum(axis=1)
    return [members[index] for index in distances.argsort()[:limit]]
