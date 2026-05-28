from pathlib import Path


def load_canonical_topics() -> list[str]:

    repo_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    topics_file = (
        repo_root / "topics.txt"
    )

    topics = []

    if not topics_file.exists():
        return topics

    for line in topics_file.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        topics.append(line)

    return topics


def ensure_canonical(
    name: str,
    canonical: list[str],
) -> str:

    if not name:
        return "Uncategorized"

    name = name.strip().strip(
        "\"'`. \n\t"
    )

    if name in canonical:
        return name

    lower_map = {
        t.lower(): t for t in canonical
    }

    if name.lower() in lower_map:
        return lower_map[
            name.lower()
        ]

    return "Uncategorized"