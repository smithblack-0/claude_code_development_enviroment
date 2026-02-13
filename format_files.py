"""Run black and ruff over src/ and tests/, exit non-zero if either fails."""

import subprocess
import sys

TARGETS = ["src/", "tests/"]


def run(args):
    cmd = [sys.executable, "-m"] + args
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    black_rc = run(["black"] + TARGETS)
    ruff_rc = run(["ruff", "check", "--fix"] + TARGETS)

    if black_rc != 0 or ruff_rc != 0:
        print("\nFormatting failed.")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
