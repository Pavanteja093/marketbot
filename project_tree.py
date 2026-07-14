from pathlib import Path

ROOT = Path(r"C:\Users\pavan\Documents\Python\Marketbot")

OUTPUT_FILE = ROOT / "marketbot_tree.txt"

IGNORE = {
    "__pycache__",
    ".git",
    ".venv",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache"
}


def build_tree(folder, prefix=""):

    entries = sorted(
        [e for e in folder.iterdir() if e.name not in IGNORE],
        key=lambda x: (x.is_file(), x.name.lower())
    )

    for i, entry in enumerate(entries):

        connector = "└── " if i == len(entries) - 1 else "├── "

        yield prefix + connector + entry.name

        if entry.is_dir():

            extension = "    " if i == len(entries) - 1 else "│   "

            yield from build_tree(
                entry,
                prefix + extension
            )


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    f.write(ROOT.name + "\n")

    for line in build_tree(ROOT):

        f.write(line + "\n")

print("=" * 60)
print("PROJECT TREE CREATED")
print("=" * 60)
print(OUTPUT_FILE)