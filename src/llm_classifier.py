import os
import json

from classification.topics_loader import (
    load_canonical_topics,
    ensure_canonical,
)

try:
    import requests
except ImportError:
    requests = None


class LLMClassifier:
    """
    DeepSeek / OpenRouter topic classifier.

    Reads canonical topic names from topics.txt and
    forces the LLM's output to be one of them.
    """

    OPENROUTER_URL = (
        "https://openrouter.ai/api/v1/chat/completions"
    )

    DEFAULT_MODEL = (
        "deepseek/deepseek-chat"
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):

        self.api_key = (
            api_key
            or os.environ.get(
                "OPENROUTER_API_KEY"
            )
        )

        self.model = (
            model
            or os.environ.get(
                "OPENROUTER_MODEL"
            )
            or self.DEFAULT_MODEL
        )

        self.canonical_topics = (
            load_canonical_topics()
        )

    @property
    def enabled(self) -> bool:

        return bool(
            self.api_key
        ) and (
            requests is not None
        )

    def _build_prompt(
        self,
        question_text: str,
    ) -> str:

        topics_block = "\n".join(
            f"- {t}"
            for t in self.canonical_topics
        )

        return (
            "You are classifying competitive-exam REASONING "
            "questions into a strict topic taxonomy.\n\n"
            "You MUST respond with ONLY one topic name from "
            "this exact list (copy verbatim):\n\n"
            f"{topics_block}\n\n"
            "Rules:\n"
            "- Output ONLY the topic name. No explanation, "
            "no punctuation, no quotes.\n"
            "- If the question is NOT reasoning or doesn't "
            "clearly fit any topic, output exactly: "
            "Uncategorized\n"
            "- Use the most specific topic possible.\n\n"
            "Question:\n"
            f"\"\"\"\n{question_text}\n\"\"\"\n\n"
            "Topic:"
        )

    def classify(
        self,
        question_text: str,
    ) -> str:

        if not self.enabled:
            return ""

        if not question_text:
            return "Uncategorized"

        try:

            response = requests.post(
                self.OPENROUTER_URL,
                headers={
                    "Authorization": (
                        f"Bearer {self.api_key}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                self._build_prompt(
                                    question_text
                                )
                            ),
                        }
                    ],
                    "temperature": 0.0,
                    "max_tokens": 30,
                }),
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            raw = (
                data["choices"][0]
                ["message"]["content"]
            )

            return ensure_canonical(
                raw,
                self.canonical_topics,
            )

        except Exception as e:

            print(
                f"[LLMClassifier] error: {e}"
            )

            return ""