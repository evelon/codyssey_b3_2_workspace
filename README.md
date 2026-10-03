# gitscribe

`git status` / `git diff` 결과를 AI API에 보내 **커밋 메시지**와 **PR 제목/본문 초안**을 생성하는 Python CLI 도구입니다.
생성 결과는 터미널에 출력만 하며, 커밋/푸시/PR 등록은 사용자가 검토한 뒤 직접 합니다.

## 동작 흐름

```
git status / git diff 수집 → (diff 길이 제한) → safe-mode 마스킹 → AI API 호출
→ 형식 검증 → (위반 시 1회 재생성) → (그래도 위반 시 후처리) → 터미널 출력
```

## 설치

요구 사항: Python 3.12 이상, Git, [uv](https://docs.astral.sh/uv/)

```bash
git clone git@github.com:evelon/codyssey_b3_2_workspace.git
cd codyssey_b3_2_workspace
uv sync
```

## 환경변수(API Key) 설정

OpenAI 호환 API(Codyssey 프록시)를 사용합니다. Key는 코드에 넣지 말고 환경변수로만 설정합니다.

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key (필수) | - |
| `OPENAI_BASE_URL` | API Base URL | `https://copa.codyssey.kr/v1` |

방법 1: 프로젝트 루트에 `.env` 파일 만들기 (`.gitignore`에 포함되어 커밋되지 않음)

```bash
cp .env.example .env
# .env 파일을 열어 실제 값을 입력
```

방법 2: 셸에서 직접 export

```bash
export OPENAI_API_KEY="YOUR_KEY"
export OPENAI_BASE_URL="https://copa.codyssey.kr/v1"
```

## 실행 방법

**Git 리포지토리의 루트 디렉토리**에서 실행합니다. 하위 디렉토리에서 실행하면 오류가 납니다.

```bash
uv run gitscribe commit          # 커밋 메시지 생성 (git diff 기준)
uv run gitscribe commit --cached # 스테이징된 변경(git diff --cached) 기준
uv run gitscribe pr              # PR 초안 생성 (git diff main...HEAD 기준)
uv run gitscribe pr --base dev   # 기준 브랜치 변경
```

가상환경을 활성화했다면 `python -m gitscribe commit`으로도 실행할 수 있습니다.

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--model` | `gpt-5.4-mini` | 사용할 모델 |
| `--temperature` | `0.3` | 낮을수록 일관된 결과, 높을수록 다양한 표현 |
| `--max-tokens` | `1000` | 응답 최대 토큰 수. 너무 작으면 응답이 잘려 형식 검증에 실패합니다 |
| `--max-diff-chars` | `20000` | 이 글자 수를 넘는 diff는 잘라서 보냅니다 (로그로 알림) |
| `--safe-mode` / `--no-safe-mode` | 켜짐 | 민감정보 마스킹 여부 |
| `--context "..."` | 없음 | 변경 이유/요구사항 메모. 프롬프트에 함께 넣어 Why를 더 정확하게 씁니다 |
| `--cached` (commit) | 꺼짐 | 스테이징된 변경 사용 |
| `--base` (pr) | `main` | PR 비교 기준 브랜치 |

> `gpt-5-mini`는 프록시에서 `temperature`/`max_tokens`를 보내면 `502`를 반환하므로 사용하지 마세요.

### 설정 파일 (선택)

대상 리포 루트에 `.gitscribe`(TOML)를 두면 기본값을 바꿀 수 있습니다.

```toml
language = "English"
prefixes = ["feat", "fix", "docs", "refactor", "test", "chore", "perf"]
```

## 출력 예시

### 커밋 메시지

```text
$ uv run gitscribe commit --context "safe-mode 기본값 결정"
[INFO] Git status 수집 완료: 3개 파일 변경 감지
[INFO] Git diff 수집 완료: 62줄
[INFO] safe-mode: 민감정보 0건 마스킹
[INFO] AI API 요청 중... (model=gpt-5.4-mini)
[INFO] API 호출 횟수: 1
[DONE] 커밋 메시지 생성 완료

--- Change Summary ---
- AI 기반 커밋 메시지 생성 흐름을 `__init__.py`에 연결
- `--model`, `--temperature`, `--max-tokens`, `--context` 옵션을 추가

--- Commit Message ---
feat: AI 기반 커밋 메시지 생성 추가

- `ai.chat` 호출로 모델 응답을 받아 `SUMMARY`와 `COMMIT` 섹션으로 출력하도록 추가
- `--model`, `--temperature`, `--max-tokens`, `--context` 옵션과 `load_dotenv()`를 도입
----------------------
```

### PR 제목/본문

```text
$ uv run gitscribe pr
[INFO] 현재 브랜치: feature/pr-draft (기준: main)
[INFO] main...HEAD 변경 파일 4개
[INFO] Git diff 수집 완료: 267줄
[INFO] safe-mode: 민감정보 0건 마스킹
[INFO] AI API 요청 중... (model=gpt-5.4-mini)
[INFO] API 호출 횟수: 1
[DONE] PR 초안 생성 완료

--- Change Summary ---
- `commit`/`pr` 하위 명령과 공통 옵션을 추가했다.

--- PR Title ---
feat: commit/pr 생성 CLI와 AI 호출 흐름 추가

--- PR Body ---
## Why
- git 변경 사항으로 커밋 메시지와 PR 초안을 생성하는 CLI 흐름을 추가했다.

## What
- `commit`과 `pr` 하위 명령을 추가하고 `--model`, `--temperature` 등 옵션을 받도록 했다.
- `ai.chat()`에서 `/chat/completions`를 호출하고 상태 코드별 오류 힌트를 포함해 예외를 처리한다.

## How to Test
- `python -m gitscribe pr --base main`으로 기준 브랜치 대비 diff 수집과 로그 출력이 되는지 확인한다.
----------------------
```

### 형식 위반 → 재생성 → 후처리

```text
[WARN] 형식 규칙 위반: [TITLE] 섹션에 PR 제목이 없습니다. / PR 본문에 '## Why' 섹션이 없습니다.
[INFO] 위반 사항을 알려주고 1회 재생성합니다.
[WARN] 재생성 후에도 형식이 맞지 않아 후처리를 적용합니다.
[INFO] API 호출 횟수: 2
```

검증 규칙: 커밋 제목 50자 권장(최대 72자, `<prefix>: ` 형식), PR 제목 한 줄 최대 80자,
PR 본문 `## Why` / `## What` / `## How to Test` 섹션과 섹션별 `- ` 불릿 1개 이상.

### 오류 / 변경 없음

```text
[ERROR] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.
예) export OPENAI_API_KEY="YOUR_KEY"

[ERROR] AI API 오류 (HTTP 401, 인증 실패, API Key 확인): Authentication is required.
[ERROR] 기준 브랜치 'dev'가 없습니다. --base 옵션으로 지정하세요.
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
```

untracked(새) 파일은 `git diff`에 나오지 않으므로 내용을 보내지 않습니다. 포함하려면 `git add -N <file>` 후 실행하거나, 스테이징하고 `--cached`를 사용하세요.

## 민감정보 주의사항

diff는 외부 AI API로 전송됩니다.

- **safe-mode(기본 켜짐)**: 전송 전에 다음 패턴을 마스킹합니다.
  - API Key/토큰 형태 (`sk-...`, `ghp_...`, `AKIA...`, `AIza...`, `xox...-`, `Bearer ...`, JWT, 개인키 블록)
  - 비밀 이름(`api_key`, `secret`, `token`, `password` 등)에 대입된 문자열, `.env` 형식 `NAME=value`
  - 이메일, 주민등록번호, 휴대폰 번호
- 정규식 기반이라 모든 비밀을 잡지는 못합니다. 민감한 파일(`.env`, 인증서, 고객 데이터)은 커밋 대상에서 **제외**(`.gitignore`)하고, 의심되면 `--cached`로 필요한 파일만 스테이징해서 실행하세요.
- `--no-safe-mode`는 diff에 민감정보가 없다고 확신할 때만 사용하세요.
- 생성된 커밋/PR 문구는 정답이 아닌 **초안**입니다. 반드시 검토하고 수정한 뒤 적용하세요.

## 비용 / 요청 횟수

- 실행 1회당 API 호출은 **최대 2회**입니다 (기본 1회, 형식 위반 시 재생성 1회). 호출 횟수는 `[INFO] API 호출 횟수`로 출력됩니다.
- 비용은 입력 토큰(diff 크기)에 비례합니다. 큰 변경은 작은 단위로 나눠 커밋하거나 `--max-diff-chars`를 낮추세요.
- 차감 배수가 낮은 모델(`gpt-5.4-mini`, `gemini-3.1-flash-lite`, `claude-haiku-4` 등, 0.5배)을 기본으로 쓰고, 품질이 부족할 때만 큰 모델로 바꾸세요.
- 자동 재시도는 하지 않습니다. 프록시가 `HTTP 429`(한도 초과)를 반환하면 잠시 후 다시 실행하세요.
- 프록시는 모델 응답에 Key 설정 문자열이 포함되면 `HTTP 400`으로 차단합니다. 프롬프트에서 이를 금지하고 있지만, 400이 나오면 다시 실행해 보세요.

## 테스트

```bash
uv run python tests/test_generate.py
uv run python tests/test_mask.py
```

## 구조

```
src/gitscribe/
├── __init__.py   # CLI 진입점, 실행 흐름, 검증/재생성 루프
├── git.py        # git status/diff 수집
├── ai.py         # /chat/completions REST 호출, 오류 처리
├── generate.py   # 프롬프트, 응답 파싱, 형식 검증/후처리, .gitscribe 설정
└── mask.py       # safe-mode 마스킹
```
