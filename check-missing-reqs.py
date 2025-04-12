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
    import argparse

    parser = argparse.ArgumentParser(
        description="Check for unused/missing Python requirements."
    )
    parser.add_argument(
        "--lambda-name",
        choices=["tweet", "youtube"],
        required=True,
        help="Specify which Lambda to check requirements for.",
    )
    args = parser.parse_args()

    if args.lambda_name == "tweet":
        run_check(
            source_dir=".",
            requirements_file="tweet_lambda_requirements.txt",
            ignore_paths=[
                "venv-tweet",
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
    elif args.lambda_name == "youtube":
        run_check(
            source_dir=".",
            requirements_file="youtube_lambda_requirements.txt",
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
