import os
import re
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
    DeepSeek / OpenRouter classifier.

    A single call returns both:
      - is_reasoning: bool
      - llm_topic: canonical name from topics.txt

    Uses forced JSON output for reliability.
    Falls back gracefully (returns empty result)
    if no API key is set or the request fails.
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

    # =====================================================
    # Prompt builder
    # =====================================================
    def _build_prompt(
        self,
        question_text: str,
    ) -> str:

        topics_block = "\n".join(
            f"- {t}"
            for t in self.canonical_topics
        )

        return (
            "You classify questions from "
            "Indian competitive-exam papers "
            "(SSC, Bank, Railway, UPSC, "
            "state PYPs).\n\n"

            "Decide TWO things:\n"
            "1. is_reasoning: true if the "
            "question is a REASONING / "
            "Logical-Aptitude question. "
            "false if it is English, "
            "Maths/Quant, GK, Current "
            "Affairs, Science, Computer "
            "Awareness, Banking Awareness, "
            "or any other non-reasoning "
            "subject.\n"
            "2. topic: one EXACT name from "
            "the list below. If is_reasoning "
            "is false, set topic to "
            "\"Uncategorized\".\n\n"

            "Allowed topics (use the exact "
            "string, copy verbatim):\n"
            f"{topics_block}\n\n"

            "Respond ONLY with valid JSON in "
            "this exact shape. No prose, no "
            "code fences:\n"
            "{\"is_reasoning\": <true|false>, "
            "\"topic\": \"<exact topic name>\"}"
            "\n\n"

            "Question:\n"
            f"\"\"\"\n{question_text}\n\"\"\""
        )

    # =====================================================
    # Main entry
    # =====================================================
    def classify(
        self,
        question_text: str,
    ) -> dict:

        fallback = {
            "is_reasoning": None,
            "llm_topic": "",
        }

        if not self.enabled:
            return fallback

        if not question_text:
            return {
                "is_reasoning": False,
                "llm_topic": "Uncategorized",
            }

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
                    "max_tokens": 80,
                    "response_format": {
                        "type": "json_object"
                    },
                }),
                timeout=45,
            )

            response.raise_for_status()

            data = response.json()

            raw = (
                data["choices"][0]
                ["message"]["content"]
            )

            parsed = self._safe_json(raw)

            if parsed is None:
                return fallback

            is_reasoning = bool(
                parsed.get(
                    "is_reasoning",
                    False,
                )
            )

            topic = ensure_canonical(
                str(
                    parsed.get(
                        "topic",
                        "",
                    )
                ),
                self.canonical_topics,
            )

            if not is_reasoning:
                topic = "Uncategorized"

            return {
                "is_reasoning": is_reasoning,
                "llm_topic": topic,
            }

        except Exception as e:

            print(
                f"[LLMClassifier] error: {e}"
            )

            return fallback

    # =====================================================
    # Robust JSON extraction
    # =====================================================
    @staticmethod
    def _safe_json(
        raw: str,
    ) -> dict | None:

        if not raw:
            return None

        text = raw.strip()

        # Strip accidental code fences like ```json ... ``` or ``` ... ```
        if text.startswith("```"):
            text = text.strip("`")
            text = re.sub(
                r"^\s*json",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()

        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Last-resort: extract the first
        # {...} block from the response
        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if match:
            try:
                return json.loads(
                    match.group(0)
                )
            except Exception:
                return None

        return None