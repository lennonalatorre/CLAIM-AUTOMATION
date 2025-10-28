import re

def clean_text(t: str) -> str:
    t = t.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def detect_counselor(data: dict, counselor_list):
    """Find counselor name inside extracted data text. Returns name or None."""
    blob = " ".join(str(v) for v in data.values()).lower()
    for name in counselor_list:
        n = name.lower()
        short = n.replace("dr", "").strip()
        if n in blob or short in blob:
            return name
    return None
