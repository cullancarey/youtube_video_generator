from pathlib import Path

# File names
dev_filename = "youtube_lambda_requirements-dev.txt"
prod_filename = "youtube_lambda_requirements.txt"

# Dev-only dependencies to exclude from the production file
dev_only_deps = {
    "boto3",
    "botocore",
    "pytest",
    "iniconfig",
    "pluggy",
    "s3transfer",
    "jmespath",
    "pip-check-reqs",
}


def regenerate_prod_requirements(dev_path: Path, prod_path: Path, exclude_deps: set):
    with dev_path.open("r") as f:
        lines = f.readlines()

    # Strip dev-only packages and comments/blank lines
    prod_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-r"):
            continue
        pkg_name = line.split("==")[0].lower()
        if pkg_name not in exclude_deps:
            prod_lines.append(line)

    with prod_path.open("w") as f:
        f.write("\n".join(prod_lines) + "\n")

    print(
        f"✅ Regenerated {prod_path.name} with {len(prod_lines)} production packages (excluded {len(exclude_deps)} dev packages)."
    )


if __name__ == "__main__":
    root = Path(__file__).parent
    dev_path = root / dev_filename
    prod_path = root / prod_filename

    regenerate_prod_requirements(dev_path, prod_path, dev_only_deps)
