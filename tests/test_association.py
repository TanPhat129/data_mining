import unittest

from app.association.rules import apriori, association_rules, fp_growth


class AssociationMiningTests(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            ["math", "secondary", "evening"],
            ["math", "secondary"],
            ["english", "online"],
            ["math", "evening"],
            [],
        ]

    def test_apriori_and_fp_growth_match(self):
        self.assertEqual(apriori(self.transactions, 0.2, 5), fp_growth(self.transactions, 0.2, 5))

    def test_support_uses_all_transactions(self):
        itemsets = apriori(self.transactions, 0.2, 5)
        self.assertAlmostEqual(itemsets[("math", "secondary")], 2 / 5)

    def test_itemset_size_limit_and_rules(self):
        itemsets = apriori(self.transactions, 0.2, 2)
        self.assertTrue(all(len(itemset) <= 2 for itemset in itemsets))
        rules = association_rules(itemsets, 0.4, 1.0)
        self.assertTrue(all(rule["confidence"] >= 0.4 and rule["lift"] >= 1 for rule in rules))


if __name__ == "__main__":
    unittest.main()
