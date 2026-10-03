import re
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {"language": "한국어", "prefixes": ["feat", "fix", "docs", "refactor", "test", "chore"]}

SYSTEM_PROMPT = """너는 git 변경 사항을 읽고 커밋 메시지와 PR 설명을 쓰는 시니어 개발자다.
- 모든 문장은 {language}로 작성한다. 커밋 prefix, 파일명, 코드 식별자는 원문 그대로 쓴다.
- diff에 실제로 드러난 변경만 근거로 쓰고, 추측하거나 과장하지 않는다.
- [MASKED...] 표시는 그대로 두고 원래 값을 추측하지 않는다.
- API Key·토큰·비밀번호 값이나 `NAME=값` 형태의 비밀 환경변수 설정 예시를 쓰지 않는다. 필요하면 "API Key 환경변수를 설정한다"처럼 말로 쓴다.
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

PR_PROMPT = """## 작성 규칙
- 제목은 "<prefix>: <요약>" 형식의 한 줄, 80자 이내로 쓴다. prefix는 다음 중 하나: {prefixes}
- 본문은 ## Why, ## What, ## How to Test 세 섹션을 이 순서로 포함하고, 각 섹션에 "- " 불릿을 1개 이상 쓴다.
  - Why: 변경 배경/동기. diff로 알 수 없는 배경은 지어내지 않는다.
  - What: 핵심 변경 사항
  - How to Test: 리뷰어가 따라 할 수 있는 확인 절차 (가능하면 명령어 포함)

## 출력 형식
[SUMMARY]
- <변경 요약 불릿 1~3개>
[TITLE]
<prefix>: <제목>
[BODY]
## Why
- <불릿>

## What
- <불릿>

## How to Test
- <불릿>
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
