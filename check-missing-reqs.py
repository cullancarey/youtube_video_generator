import subprocess
import argparse
import sys
from pathlib import Path


def run_check(source_dir, requirements_file, ignore_paths):
    command = ["pip-missing-reqs", source_dir, "--requirements-file", requirements_file]

    for path in ignore_paths:
        command.extend(["-f", path])

    print(f"\n🔍 Checking for missing requirements in {source_dir}")
    print(f"Using requirements file: {requirements_file}")
    print(f"Ignoring paths: {', '.join(ignore_paths)}\n")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ pip-missing-reqs exited with code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check for unused/missing Python requirements."
    )
    parser.add_argument(
        "--requirements-file",
        default="youtube_lambda_requirements.txt",
        help="Requirements file to validate (default: youtube_lambda_requirements.txt).",
    )
    args = parser.parse_args()

    run_check(
        source_dir=".",
        requirements_file=args.requirements_file,
        ignore_paths=[
            "venv-youtube",
            "tests",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".git",
            ".venv",
            "terraform",
            "images",
        ],
    )
