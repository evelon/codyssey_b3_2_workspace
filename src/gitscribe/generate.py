import re
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {
    "language": "한국어",
    "prefixes": ["feat", "fix", "docs", "refactor", "test", "chore"],
}

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


def build_messages(
    template: str, cfg: dict, files: list[str], diff: str, context: str | None
) -> list[dict]:
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
    text = re.sub(r"^```\w*[ \t]*$", "", text, flags=re.MULTILINE)
    parts = re.split(
        r"^\[(SUMMARY|COMMIT|TITLE|BODY)\][ \t]*$", text, flags=re.MULTILINE
    )
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


COMMIT_SUBJECT_RECOMMENDED = 50
COMMIT_SUBJECT_MAX = 72
PR_TITLE_MAX = 80
PR_SECTIONS = ["Why", "What", "How to Test"]
PLACEHOLDER = "- (작성 필요)"


def prefix_re(cfg: dict) -> re.Pattern:
    return re.compile(
        rf"^({'|'.join(map(re.escape, cfg['prefixes']))})(\(.+?\))?!?: \S"
    )


def body_sections(body: str) -> dict[str, str]:
    parts = re.split(r"^##[ \t]+(.+?)[ \t]*$", body, flags=re.MULTILINE)
    return {parts[i].strip().lower(): parts[i + 1] for i in range(1, len(parts), 2)}


def bullets(text: str) -> list[str]:
    return [
        line.strip() for line in text.splitlines() if re.match(r"\s*[-*]\s+\S", line)
    ]


def check(kind: str, sections: dict[str, str], cfg: dict) -> list[str]:
    """형식 규칙 위반 목록을 돌려준다. 비어 있으면 통과."""
    errors = []
    if not sections.get("SUMMARY"):
        errors.append("[SUMMARY] 섹션이 없거나 비어 있습니다.")
    if kind == "commit":
        subject = sections.get("COMMIT", "").split("\n", 1)[0].strip()
        if not subject:
            errors.append("[COMMIT] 섹션에 커밋 제목이 없습니다.")
        else:
            if len(subject) > COMMIT_SUBJECT_MAX:
                errors.append(
                    f"커밋 제목이 {len(subject)}자입니다. {COMMIT_SUBJECT_MAX}자 이내로 줄이세요."
                )
            if not prefix_re(cfg).match(subject):
                errors.append(
                    f"커밋 제목이 '<prefix>: ' 형식이 아닙니다. prefix: {', '.join(cfg['prefixes'])}"
                )
        return errors

    title = sections.get("TITLE", "")
    if not title:
        errors.append("[TITLE] 섹션에 PR 제목이 없습니다.")
    else:
        if "\n" in title:
            errors.append("PR 제목은 한 줄이어야 합니다.")
        if len(title) > PR_TITLE_MAX:
            errors.append(
                f"PR 제목이 {len(title)}자입니다. {PR_TITLE_MAX}자 이내로 줄이세요."
            )
    found = body_sections(sections.get("BODY", ""))
    for name in PR_SECTIONS:
        if name.lower() not in found:
            errors.append(f"PR 본문에 '## {name}' 섹션이 없습니다.")
        elif not bullets(found[name.lower()]):
            errors.append(f"'## {name}' 섹션에 '- ' 불릿이 없습니다.")
    return errors


def fix(kind: str, sections: dict[str, str], cfg: dict) -> dict[str, str]:
    """재생성 후에도 남은 위반을 규칙에 맞게 강제로 다듬는다."""
    fixed = {"SUMMARY": sections.get("SUMMARY") or "- (요약 없음)"}
    if kind == "commit":
        lines = sections.get("COMMIT", "").strip().splitlines() or [""]
        subject = lines[0].strip()
        if not prefix_re(cfg).match(subject):
            subject = f"chore: {subject or '변경 사항 반영'}"
        fixed["COMMIT"] = "\n".join([subject[:COMMIT_SUBJECT_MAX].rstrip(), *lines[1:]])
        return fixed

    title = next(
        (
            line.strip()
            for line in sections.get("TITLE", "").splitlines()
            if line.strip()
        ),
        "변경 사항 반영",
    )
    fixed["TITLE"] = title[:PR_TITLE_MAX].rstrip()
    found = body_sections(sections.get("BODY", ""))
    blocks = []
    for name in PR_SECTIONS:
        text = found.get(name.lower(), "")
        items = (
            bullets(text)
            or [f"- {line.strip()}" for line in text.splitlines() if line.strip()]
            or [PLACEHOLDER]
        )
        blocks.append(f"## {name}\n" + "\n".join(items))
    fixed["BODY"] = "\n\n".join(blocks)
    return fixed
