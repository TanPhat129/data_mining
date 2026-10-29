import unittest

from app.preprocessing.normalize import classify_intent, clean_text, extract_keywords


class PreprocessingTests(unittest.TestCase):
    def test_keyword_normalization(self):
        text = "Cần gia sư Anh văn lớp 8 học online buổi tối"
        keywords = extract_keywords(text)
        self.assertTrue({"need_tutor", "english", "secondary", "online", "evening"}.issubset(keywords))
        self.assertEqual(classify_intent(text, keywords), "FIND_TUTOR")

    def test_clean_text(self):
        self.assertNotIn("https", clean_text("Toán https://example.com"))

    def test_ambiguous_subject_words_are_not_false_positives(self):
        keywords = extract_keywords("Sinh viên ở địa chỉ trên nhận lớp")
        self.assertNotIn("biology", keywords)
        self.assertNotIn("geography", keywords)

    def test_subject_column_is_used(self):
        self.assertIn("biology", extract_keywords("Cần người kèm", {"subject": "Sinh"}))
        self.assertIn("literature", extract_keywords("Cần người kèm", {"subject": "Văn"}))
        self.assertIn("informatics", extract_keywords("Cần người kèm", {"subject": "Tin"}))
        self.assertEqual(
            {"math", "literature"} & set(extract_keywords("Cần người kèm", {"subject": "Toán - Văn"})),
            {"math", "literature"},
        )


if __name__ == "__main__":
    unittest.main()
