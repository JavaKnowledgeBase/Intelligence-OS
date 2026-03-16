from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

TEXT_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yml",
    ".yaml",
    ".ini",
    ".env",
    ".md",
    ".txt",
    ".toml",
    ".sh",
    ".ps1",
    ".dockerfile",
}

IGNORED_PATH_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    "dist",
}

ALLOWED_VALUE_PATTERNS = (
    re.compile(r"example\.com", re.IGNORECASE),
    re.compile(r"example\.org", re.IGNORECASE),
    re.compile(r"change-me-local-dev", re.IGNORECASE),
    re.compile(r"replace-with-a-long-random-local-secret", re.IGNORECASE),
    re.compile(r"name@company\.com", re.IGNORECASE),
)

SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "jwt secret assignment",
        re.compile(
            r"(?:JWT_SECRET_KEY|jwt_secret_key)\s*[:=]\s*['\"](?!replace-with-a-long-random-local-secret)[^'\"]{8,}['\"]",
            re.IGNORECASE,
        ),
    ),
    (
        "secret literal assignment",
        re.compile(
            r"\b(?:password|passwd|client_secret|api[_-]?key|secret|token)\b\s*[:=]\s*['\"](?!change-me-local-dev|replace-with-a-long-random-local-secret)[^'\"]{8,}['\"]",
            re.IGNORECASE,
        ),
    ),
    ("database url credentials", re.compile(r"postgres(?:ql\+psycopg)?://[^:\s]+:[^@\s]+@")),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan tracked or staged files for obvious secret leaks.")
    parser.add_argument("--staged", action="store_true", help="Scan staged files and staged content only.")
    return parser.parse_args()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def staged_files() -> list[Path]:
    result = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to list staged files.")
    return [REPO_ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()]


def tracked_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_PATH_PARTS for part in path.parts):
            continue
        if path.name.startswith(".env") or path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"Dockerfile"}:
            files.append(path)
    return files


def staged_text(path: Path) -> str | None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    result = git("show", f":{relative}")
    if result.returncode != 0:
        return None
    return result.stdout


def file_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def is_allowed_match(text: str) -> bool:
    return any(pattern.search(text) for pattern in ALLOWED_VALUE_PATTERNS)


def scan_content(path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)
            if is_allowed_match(snippet):
                continue
            findings.append(f"{path.relative_to(REPO_ROOT)}: potential {label}: {snippet[:120]}")
    return findings


def main() -> int:
    args = parse_args()
    try:
        files = staged_files() if args.staged else tracked_files()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    findings: list[str] = []
    for path in files:
        text = staged_text(path) if args.staged else file_text(path)
        if text is None:
            continue
        findings.extend(scan_content(path, text))

    if findings:
        print("Secret scan failed. Review these matches before committing:", file=sys.stderr)
        for finding in findings:
            print(f" - {finding}", file=sys.stderr)
        return 1

    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
