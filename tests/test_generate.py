from gitscribe.generate import DEFAULT_CONFIG as CFG
from gitscribe.generate import check, fix, parse

GOOD_PR = """```
[SUMMARY]
- 요약
[TITLE]
feat: PR 생성
[BODY]
## Why
- 배경
## What
- 변경
## How to Test
- 실행
```"""


def test_parse_and_check_pass():
    s = parse(GOOD_PR)
    assert s["TITLE"] == "feat: PR 생성" and check("pr", s, CFG) == []
    s = parse("[SUMMARY]\n- a\n[COMMIT]\nfix(git): 버그 수정\n\n- b")
    assert check("commit", s, CFG) == []


def test_commit_violations_and_fix():
    s = {"SUMMARY": "- a", "COMMIT": "Update stuff " + "x" * 80}
    errors = check("commit", s, CFG)
    assert len(errors) == 2 and "72" in errors[0] and "prefix" in errors[1]
    fixed = fix("commit", s, CFG)
    assert check("commit", fixed, CFG) == [] and fixed["COMMIT"].startswith("chore: Update")


def test_pr_violations_and_fix():
    s = {"TITLE": "t" * 90, "BODY": "## Why\n배경 문장\n## What\n- 변경"}
    assert len(check("pr", s, CFG)) == 4  # SUMMARY, 제목 길이, Why 불릿, How to Test 누락
    fixed = fix("pr", s, CFG)
    assert check("pr", fixed, CFG) == []
    assert "## Why\n- 배경 문장" in fixed["BODY"] and "## How to Test\n- (작성 필요)" in fixed["BODY"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
