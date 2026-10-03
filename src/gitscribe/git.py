import re
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


def succeeds(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def repo_root() -> Path:
    """CLI는 Git 프로젝트 루트에서만 실행한다."""
    try:
        root = Path(git("rev-parse", "--show-toplevel").strip())
    except RuntimeError:
        raise RuntimeError("Git 리포지토리가 아닙니다. git init 된 프로젝트 루트에서 실행하세요.") from None
    if root.resolve() != Path.cwd().resolve():
        raise RuntimeError(f"프로젝트 루트 디렉토리({root})에서 실행하세요.")
    return root


def status() -> list[str]:
    return git("status", "--porcelain").splitlines()


def untracked(status_lines: list[str]) -> list[str]:
    return [line[3:] for line in status_lines if line.startswith("??")]


def working_diff(cached: bool) -> str:
    return git("diff", "--cached") if cached else git("diff")


def branch_diff(base: str) -> str:
    # EAFP: 바로 실행하고, 실패했을 때만 원인을 진단한다.
    try:
        return git("diff", f"{base}...HEAD")
    except RuntimeError:
        if not succeeds("rev-parse", "--verify", "-q", "HEAD"):
            raise RuntimeError("커밋이 없습니다. 먼저 커밋한 뒤 pr 명령을 실행하세요.") from None
        if not succeeds("rev-parse", "--verify", "-q", base):
            raise RuntimeError(f"기준 브랜치 '{base}'가 없습니다. --base 옵션으로 지정하세요.") from None
        raise


def current_branch() -> str:
    return git("branch", "--show-current").strip() or "(detached HEAD)"


def diff_files(diff: str) -> list[str]:
    return re.findall(r"^diff --git a/.* b/(.*)$", diff, flags=re.M)
