import re

SECRET_NAME = (
    r"[A-Za-z0-9_.-]*(?:api[_-]?key|secret|token|passw(?:or)?d|pwd)[A-Za-z0-9_]*"
)

# 순서가 중요하다: 구체적인 패턴을 먼저 적용한다.
PATTERNS = [
    (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
        "[MASKED_PRIVATE_KEY]",
    ),
    (r"\bsk-[A-Za-z0-9_-]{16,}", "[MASKED_API_KEY]"),
    (r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}", "[MASKED_API_KEY]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[MASKED_API_KEY]"),
    (r"\bAIza[0-9A-Za-z_-]{35}", "[MASKED_API_KEY]"),
    (r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "[MASKED_API_KEY]"),
    (
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "[MASKED_JWT]",
    ),
    (r"(?i)\bBearer\s+(?!\[MASKED)[A-Za-z0-9._~+/=-]{16,}", "Bearer [MASKED]"),
    # api_key = "..." 처럼 비밀 이름에 대입된 문자열 리터럴
    (
        rf"(?i)(\b{SECRET_NAME}\s*[:=]\s*)(['\"])(?!\[MASKED)[^'\"\s]{{6,}}\2",
        r"\1\2[MASKED]\2",
    ),
    # .env 형식: diff 줄 맨 앞의 KEY=value
    (
        rf"(?im)^([+ -]?\s*(?:export\s+)?{SECRET_NAME}=)(?!\[MASKED|['\"])\S{{6,}}",
        r"\1[MASKED]",
    ),
    (
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}",
        "[MASKED_EMAIL]",
    ),
    (r"\b\d{6}-[1-4]\d{6}\b", "[MASKED_RRN]"),
    (r"\b01[016789]-?\d{3,4}-?\d{4}\b", "[MASKED_PHONE]"),
]
PATTERNS = [(re.compile(p), r) for p, r in PATTERNS]


def mask(text: str) -> tuple[str, int]:
    """API Key·이메일 등 민감정보 패턴을 마스킹하고, 마스킹한 개수를 함께 돌려준다."""
    total = 0
    for pattern, replacement in PATTERNS:
        text, count = pattern.subn(replacement, text)
        total += count
    return text, total
