"""Frequent-itemset mining and association-rule generation."""

from collections import Counter
from itertools import combinations
from math import ceil


def _prepare(transactions):
    return [frozenset(items) for items in transactions]


def apriori(transactions, min_support=0.03, max_size=5):
    """Mine frequent itemsets with Apriori candidate pruning."""
    baskets = _prepare(transactions)
    total = len(baskets)
    if total == 0:
        return {}
    min_count = max(1, ceil(min_support * total))
    counts = Counter(item for basket in baskets for item in basket)
    level = {frozenset([item]): count for item, count in counts.items() if count >= min_count}
    supports = {tuple(sorted(items)): count / total for items, count in level.items()}

    size = 2
    while level and size <= max_size:
        previous = set(level)
        ordered = sorted(previous, key=lambda items: tuple(sorted(items)))
        candidates = set()
        for i, left in enumerate(ordered):
            for right in ordered[i + 1:]:
                candidate = left | right
                if len(candidate) == size and all(
                        frozenset(part) in previous for part in combinations(candidate, size - 1)):
                    candidates.add(candidate)
        candidate_counts = Counter()
        for basket in baskets:
            for candidate in candidates:
                if candidate.issubset(basket):
                    candidate_counts[candidate] += 1
        level = {candidate: count for candidate, count in candidate_counts.items() if count >= min_count}
        supports.update({tuple(sorted(items)): count / total for items, count in level.items()})
        size += 1
    return supports


class _FPNode:
    def __init__(self, item, count, parent):
        self.item = item
        self.count = count
        self.parent = parent
        self.children = {}
        self.link = None


def _build_fp_tree(weighted_transactions, min_count):
    frequencies = Counter()
    for transaction, weight in weighted_transactions:
        for item in transaction:
            frequencies[item] += weight
    frequencies = Counter({item: count for item, count in frequencies.items() if count >= min_count})
    if not frequencies:
        return None, {}, frequencies

    root = _FPNode(None, 0, None)
    headers = {item: [None, None] for item in frequencies}
    for transaction, weight in weighted_transactions:
        ordered = sorted((item for item in transaction if item in frequencies),
                         key=lambda item: (-frequencies[item], item))
        node = root
        for item in ordered:
            child = node.children.get(item)
            if child is None:
                child = _FPNode(item, 0, node)
                node.children[item] = child
                if headers[item][0] is None:
                    headers[item] = [child, child]
                else:
                    headers[item][1].link = child
                    headers[item][1] = child
            child.count += weight
            node = child
    return root, headers, frequencies


def _mine_fp_tree(headers, frequencies, min_count, prefix, max_size, found):
    for item in sorted(frequencies, key=lambda value: (frequencies[value], value)):
        pattern = prefix | frozenset([item])
        if len(pattern) <= max_size:
            found[tuple(sorted(pattern))] = frequencies[item]
        if len(pattern) >= max_size:
            continue
        conditional = []
        node = headers[item][0]
        while node is not None:
            path = []
            parent = node.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            if path:
                conditional.append((frozenset(path), node.count))
            node = node.link
        _, child_headers, child_frequencies = _build_fp_tree(conditional, min_count)
        if child_headers:
            _mine_fp_tree(child_headers, child_frequencies, min_count, pattern, max_size, found)


def fp_growth(transactions, min_support=0.03, max_size=5):
    """Mine frequent itemsets using an FP-tree and conditional pattern bases."""
    baskets = _prepare(transactions)
    total = len(baskets)
    if total == 0:
        return {}
    min_count = max(1, ceil(min_support * total))
    _, headers, frequencies = _build_fp_tree([(basket, 1) for basket in baskets], min_count)
    counts = {}
    if headers:
        _mine_fp_tree(headers, frequencies, min_count, frozenset(), max_size, counts)
    return {itemset: count / total for itemset, count in counts.items()}


def association_rules(itemsets, min_confidence=0.40, min_lift=1.0):
    rules = []
    for itemset, support in itemsets.items():
        items = list(itemset)
        for size in range(1, len(items)):
            for left in combinations(items, size):
                right = tuple(item for item in items if item not in left)
                left_support = itemsets.get(tuple(sorted(left)))
                right_support = itemsets.get(tuple(sorted(right)))
                if not left_support or not right_support:
                    continue
                confidence = support / left_support
                lift = confidence / right_support
                if confidence >= min_confidence and lift >= min_lift:
                    rules.append({"antecedent": ", ".join(left), "consequent": ", ".join(right),
                                  "itemset_size": len(itemset), "support": round(support, 6),
                                  "confidence": round(confidence, 6), "lift": round(lift, 6)})
    return sorted(rules, key=lambda row: (-row["lift"], -row["support"], row["antecedent"]))


# Backward-compatible default.
frequent_itemsets = apriori
