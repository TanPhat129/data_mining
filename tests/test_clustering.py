import unittest

from app.clustering.model import choose_clustering, run_agglomerative, run_kmeans, vectorize


class ClusteringTests(unittest.TestCase):
    def test_two_algorithms_return_labels_and_metrics(self):
        documents = [
            "toán lớp tám buổi tối", "toán cấp hai tại nhà", "đại số toán lớp chín",
            "ielts tiếng anh online", "luyện thi ielts online", "tiếng anh giao tiếp",
        ]
        matrix, features = vectorize(documents)
        results = [run_kmeans(matrix, 2), run_agglomerative(matrix, 2)]
        self.assertGreater(len(features), 0)
        self.assertTrue(all(len(result["labels"]) == len(documents) for result in results))
        self.assertIn(choose_clustering(results), results)
        self.assertTrue(all(result["silhouette"] is not None for result in results))


if __name__ == "__main__":
    unittest.main()
