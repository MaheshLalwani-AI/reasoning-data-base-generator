import re

from pathlib import Path


class TopicClassifier:

    def __init__(
        self,
        topics_file: str,
    ):

        self.topics = self._load_topics(
            topics_file
        )

    def _load_topics(
        self,
        topics_file: str,
    ) -> list[str]:

        lines = Path(
            topics_file
        ).read_text(
            encoding="utf-8"
        ).splitlines()

        cleaned_topics = []

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # REMOVE:
            # 1.
            # 2)
            # - 
            # •
            # etc.

            line = re.sub(
                r"^\s*[\d]+[\.\)]\s*",
                "",
                line,
            )

            line = re.sub(
                r"^\s*[-•]\s*",
                "",
                line,
            )

            line = line.strip()

            if line:

                cleaned_topics.append(
                    line
                )

        return cleaned_topics

    def get_topics_text(
        self,
    ) -> str:

        return "\n".join(
            f"- {topic}"
            for topic in self.topics
        )