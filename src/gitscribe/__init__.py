import argparse
import sys

from gitscribe import git


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {message}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max-diff-chars", type=int, default=20000, help="AI에 보낼 diff 최대 글자 수 (기본: 20000)")

    parser = argparse.ArgumentParser(prog="gitscribe", description="git diff로 커밋 메시지/PR 초안을 생성합니다.")
    sub = parser.add_subparsers(dest="command", required=True)
    commit = sub.add_parser("commit", parents=[common], help="커밋 메시지 생성")
    commit.add_argument("--cached", action="store_true", help="스테이징된 변경(git diff --cached)을 사용")
    pr = sub.add_parser("pr", parents=[common], help="PR 제목/본문 초안 생성")
    pr.add_argument("--base", default="main", help="비교 기준 브랜치 (기본: main)")
    return parser.parse_args()


def collect_commit(args: argparse.Namespace) -> tuple[list[str], str] | None:
    status = git.status()
    if not status:
        log("INFO", "변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.")
        return None
    log("INFO", f"Git status 수집 완료: {len(status)}개 파일 변경 감지")

    new_files = git.untracked(status)
    if new_files and not args.cached:
        # untracked 파일 내용은 보내지 않는다.
        log("INFO", "untracked 파일은 diff에 포함되지 않습니다: " + ", ".join(new_files))
        log("INFO", "포함하려면 `git add -N <file>` 후 실행하거나, 스테이징 후 --cached를 사용하세요.")

    diff = git.working_diff(args.cached)
    if not diff:
        if not (new_files and not args.cached):
            hint = "" if args.cached else " (스테이징된 변경은 --cached로 확인하세요)"
            log("INFO", f"변경 사항이 없습니다{hint}. 커밋 메시지를 생성하지 않고 종료합니다.")
        return None
    return status, diff


def collect_pr(args: argparse.Namespace) -> tuple[list[str], str] | None:
    log("INFO", f"현재 브랜치: {git.current_branch()} (기준: {args.base})")
    diff = git.branch_diff(args.base)
    if not diff:
        log("INFO", f"'{args.base}' 대비 변경 사항이 없습니다. PR 초안을 생성하지 않고 종료합니다.")
        return None
    files = git.diff_files(diff)
    log("INFO", f"{args.base}...HEAD 변경 파일 {len(files)}개")
    return files, diff


def run(args: argparse.Namespace) -> None:
    git.repo_root()
    collected = collect_commit(args) if args.command == "commit" else collect_pr(args)
    if collected is None:
        return
    files, diff = collected
    log("INFO", f"Git diff 수집 완료: {len(diff.splitlines())}줄")
    if len(diff) > args.max_diff_chars:
        diff = diff[: args.max_diff_chars]
        log("WARN", f"diff가 {args.max_diff_chars}자를 넘어 잘라서 사용합니다.")
    print("\n".join(files))


def main() -> None:
    args = parse_args()
    try:
        run(args)
    except RuntimeError as e:
        sys.exit(f"[ERROR] {e}")
