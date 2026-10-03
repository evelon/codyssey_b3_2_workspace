import re
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {"language": "한국어", "prefixes": ["feat", "fix", "docs", "refactor", "test", "chore"]}

SYSTEM_PROMPT = """너는 git 변경 사항을 읽고 커밋 메시지와 PR 설명을 쓰는 시니어 개발자다.
- 모든 문장은 {language}로 작성한다. 커밋 prefix, 파일명, 코드 식별자는 원문 그대로 쓴다.
- diff에 실제로 드러난 변경만 근거로 쓰고, 추측하거나 과장하지 않는다.
- [MASKED...] 표시는 그대로 두고 원래 값을 추측하지 않는다.
- 지정한 출력 형식 외의 설명, 인사말, 코드 블록(```)은 출력하지 않는다."""

COMMIT_PROMPT = """## 작성 규칙
- 제목은 "<prefix>: <요약>" 형식의 한 줄, 50자 이내(최대 72자), 마침표 없이 쓴다.
- prefix는 다음 중 하나: {prefixes}
- 본문은 "- "로 시작하는 불릿 1~5개로, 무엇을 왜 바꿨는지 쓴다.

## 출력 형식
[SUMMARY]
- <변경 요약 불릿 1~3개>
[COMMIT]
<prefix>: <제목>

- <본문 불릿>
"""


def load_config(root: Path) -> dict:
    path = root / ".gitscribe"
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with path.open("rb") as f:
            return {**DEFAULT_CONFIG, **tomllib.load(f)}
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f".gitscribe 설정 파일 형식 오류: {e}") from None


def build_messages(template: str, cfg: dict, files: list[str], diff: str, context: str | None) -> list[dict]:
    user = template.format(prefixes=", ".join(cfg["prefixes"]))
    if context:
        user += f"\n## 변경 이유/요구사항 (작성자 메모)\n{context}\n"
    user += "\n## 변경 파일\n" + "\n".join(files) + f"\n\n## diff\n{diff}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(language=cfg["language"])},
        {"role": "user", "content": user},
    ]


def parse(text: str) -> dict[str, str]:
    """[SUMMARY]/[COMMIT]/... 마커로 나뉜 응답을 섹션별 dict로 만든다."""
    text = re.sub(r"^```\w*[ \t]*$", "", text, flags=re.M)
    parts = re.split(r"^\[(SUMMARY|COMMIT|TITLE|BODY)\][ \t]*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
