import re
import unicodedata

KEYWORD_RULES = {
    "need_tutor": [r"cần\s+(?:tìm\s+)?gia\s+sư", r"tìm\s+gia\s+sư", r"cần\s+người\s+kèm",
                   r"cần\s+(?:tìm\s+)?(?:giáo\s+viên|gv|thầy|cô)", r"tìm\s+người\s+dạy"],
    "math": [r"\btoán\b", r"math"],
    "english": [r"tiếng\s+anh", r"anh\s+văn", r"\benglish\b"],
    "ielts": [r"\bielts\b"],
    "physics": [r"\bvật\s+lý\b", r"\bmôn\s+lý\b", r"\bphysics\b"],
    "chemistry": [r"\bhóa\s+học\b", r"\bmôn\s+hóa\b", r"\bchemistry\b"],
    "biology": [r"\bsinh\s+học\b", r"\bmôn\s+sinh\b", r"\bbiology\b"],
    "literature": [r"ngữ\s+văn", r"\bmôn\s+văn\b"],
    "vietnamese": [r"tiếng\s+việt"],
    "informatics": [r"tin\s+học", r"\bmôn\s+tin\b", r"informatics"],
    "history": [r"lịch\s+sử", r"\bmôn\s+sử\b"],
    "geography": [r"địa\s+lý", r"\bmôn\s+địa\b"],
    "toeic": [r"\btoeic\b"],
    "chinese": [r"tiếng\s+trung", r"\bhsk\b"],
    "korean": [r"tiếng\s+hàn", r"\btopik\b"],
    "japanese": [r"tiếng\s+nhật", r"\bjlpt\b"],
    "primary": [r"tiểu\s+học", r"lớp\s*[1-5]\b"],
    "secondary": [r"thcs", r"cấp\s*2", r"lớp\s*[6-9]\b"],
    "high_school": [r"thpt", r"cấp\s*3", r"lớp\s*(?:10|11|12)\b"],
    "online": [r"\bonline\b", r"trực\s+tuyến"],
    "home": [r"tại\s+nhà", r"tại\s+gia", r"\bhome\b"],
    "evening": [r"buổi\s+tối", r"học\s+tối", r"\btối\b"],
    "weekend": [r"cuối\s+tuần", r"thứ\s*[67]|chủ\s+nhật"],
    "urgent": [r"cần\s+gấp", r"gấp", r"sớm"],
    "lost_basic": [r"mất\s+gốc", r"hổng\s+kiến\s+thức"],
    "exam_prep": [r"ôn\s+thi", r"luyện\s+thi", r"thi\s+vào"],
    "communication": [r"giao\s+tiếp"],
    "homework_support": [r"báo\s+bài", r"kèm\s+bài", r"phụ\s+đạo"],
    "three_sessions": [r"(?:3|ba)\s*(?:buổi|b)\s*(?:/|mỗi)?\s*tuần"],
    "two_sessions": [r"(?:2|hai)\s*(?:buổi|b)\s*(?:/|mỗi)?\s*tuần"],
}

OFFER_PATTERNS = [
    r"\bnhận\s+dạy\b", r"\bnhận\s+lớp\b", r"\btìm\s+học\s+viên\b",
    r"\btuyển\s+sinh\b", r"\bmở\s+lớp\b",
]

STOPWORDS = set("và là cho của một các với cần tìm gia sư học dạy em mình bạn bé có đang muốn được sẽ thì mà ở do từ này đó thêm xem yêu cầu khu vực".split())

SUBJECT_ALIASES = {
    "math": ("toán", "toán học", "math"),
    "english": ("tiếng anh", "anh văn", "english"),
    "physics": ("lý", "vật lý", "physics"),
    "chemistry": ("hóa", "hóa học", "chemistry"),
    "biology": ("sinh", "sinh học", "biology"),
    "literature": ("văn", "ngữ văn"),
    "vietnamese": ("tiếng việt",),
    "informatics": ("tin", "tin học"),
    "history": ("sử", "lịch sử"),
    "geography": ("địa", "địa lý"),
    "ielts": ("ielts",),
    "toeic": ("toeic",),
}


def clean_text(text):
    text = unicodedata.normalize("NFC", str(text or "")).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^\w\sÀ-ỹ]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(text, fields=None):
    selected = []
    if fields:
        for name in ("subject", "grade", "location", "mode", "budget"):
            selected.append(str(fields.get(name, "") or ""))
    source = clean_text(" ".join([str(text or "")] + selected))
    found = set()
    for keyword, patterns in KEYWORD_RULES.items():
        if any(re.search(pattern, source, flags=re.IGNORECASE) for pattern in patterns):
            found.add(keyword)
    subject_raw = unicodedata.normalize("NFC", str((fields or {}).get("subject", "") or "")).lower()
    subject_raw = re.sub(r"[,;/+&|-]", ",", subject_raw)
    subject = clean_text(subject_raw)
    if subject:
        # Subject is a structured field, so standalone aliases such as "Văn" and
        # "Tin" are safe here. Delimiters also support values such as "Toán - Văn".
        subject_parts = set()
        for part in re.split(r",", subject_raw):
            part = clean_text(part)
            part = re.sub(r"^môn\s+", "", part.strip())
            if part:
                subject_parts.add(part)
        for keyword, aliases in SUBJECT_ALIASES.items():
            if any(alias in subject_parts for alias in aliases):
                found.add(keyword)
    return sorted(found)


def classify_intent(text, keywords):
    source = clean_text(text)
    if "need_tutor" in keywords:
        return "FIND_TUTOR"
    if any(re.search(pattern, source) for pattern in OFFER_PATTERNS):
        return "TUTOR_OFFER"
    return "UNCERTAIN"


def tokens(text):
    words = re.findall(r"[a-zà-ỹđ0-9]+", clean_text(text), flags=re.IGNORECASE)
    return [word for word in words if len(word) > 1 and word not in STOPWORDS]
