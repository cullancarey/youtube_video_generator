from pathlib import Path
import subprocess

# Adjust paths for new structure
base_dir = Path(__file__).parent / "lambdas" / "youtube"
dev_filename = base_dir / "youtube_lambda_requirements-dev.txt"
prod_filename = base_dir / "youtube_lambda_requirements.txt"

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
    "setuptools",
    "wheel",
    "pygments",
    "packaging",
    "pip",
    "pipdeptree",
    "urllib3",
    "six",
    "python-dateutil",
}


def regenerate_prod_requirements(dev_path: Path, prod_path: Path, exclude_deps: set):
    with dev_path.open("r") as f:
        lines = f.readlines()

    # Strip dev-only packages and comments/blank lines
    prod_lines = []
    for line in lines:
        line = line.strip()
        if (
            not line
            or line.startswith("#")
            or line.startswith("-r")
            or "==" not in line
        ):
            continue
        pkg_name = line.split("==")[0].lower()
        if pkg_name not in exclude_deps:
            prod_lines.append(line)

    with prod_path.open("w") as f:
        f.write("\n".join(prod_lines) + "\n")

    print(
        f"✅ Regenerated {prod_path.name} with {len(prod_lines)} production packages "
        f"(excluded {len(exclude_deps)} dev packages)."
    )


def export_dev_requirements(dev_path: Path):
    subprocess.run(
        [
            "uv",
            "export",
            "--format",
            "requirements.txt",
            "--group",
            "dev",
            "--no-emit-project",
            "--no-header",
            "--no-annotate",
            "--no-hashes",
            "--output-file",
            str(dev_path),
        ],
        check=True,
    )
    print(f"✅ Exported {dev_path.name} from uv.lock")


if __name__ == "__main__":
    export_dev_requirements(dev_filename)
    regenerate_prod_requirements(dev_filename, prod_filename, dev_only_deps)
