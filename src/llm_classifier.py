import hashlib
import json
import os
import re
from pathlib import Path

from classification.topics_loader import (
    ensure_canonical,
    load_canonical_topics,
)

try:
    import requests
except ImportError:
    requests = None


class LLMClassifier:
    """
    OpenRouter classifier with local JSON cache.

    Returns:
    - is_reasoning: bool | None
    - llm_topic: str

    If no OPENROUTER_API_KEY is set, it falls back gracefully.
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "deepseek/deepseek-chat"
    CACHE_PATH = Path("data/cache/llm_classification_cache.json")

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
        )

        self.model = (
            model
            or os.environ.get("OPENROUTER_MODEL")
            or self.DEFAULT_MODEL
        )

        self.canonical_topics = load_canonical_topics()
        self.cache = self._load_cache()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and requests is not None

    def classify(self, question_text: str) -> dict:
        fallback = {
            "is_reasoning": None,
            "llm_topic": "",
        }

        if not question_text:
            return {
                "is_reasoning": False,
                "llm_topic": "Uncategorized",
            }

        cache_key = self._cache_key(question_text)

        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.enabled:
            return fallback

        try:
            response = requests.post(
                self.OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(
                    {
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": self._build_prompt(question_text),
                            }
                        ],
                        "temperature": 0.0,
                        "max_tokens": 80,
                        "response_format": {
                            "type": "json_object",
                        },
                    }
                ),
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
                parsed.get("is_reasoning", False)
            )

            topic = ensure_canonical(
                str(parsed.get("topic", "")),
                self.canonical_topics,
            )

            if not is_reasoning:
                topic = "Uncategorized"

            result = {
                "is_reasoning": is_reasoning,
                "llm_topic": topic,
            }

            self.cache[cache_key] = result
            self._save_cache()

            return result

        except Exception as e:
            print(f"[LLMClassifier] error: {e}")
            return fallback

    def _build_prompt(self, question_text: str) -> str:
        topics_block = "\n".join(
            f"- {topic}"
            for topic in self.canonical_topics
        )

        return (
            "You classify questions from Indian competitive-exam papers "
            "(SSC, Bank, Railway, UPSC, state PYPs).\n\n"
            "Decide TWO things:\n"
            "1. is_reasoning: true if the question is a REASONING / "
            "Logical-Aptitude question. false if it is English, "
            "Maths/Quant, GK, Current Affairs, Science, Computer Awareness, "
            "Banking Awareness, or any other non-reasoning subject.\n"
            "2. topic: one EXACT name from the list below. If is_reasoning "
            "is false, set topic to \"Uncategorized\".\n\n"
            "Allowed topics. Use the exact string. Copy verbatim:\n"
            f"{topics_block}\n\n"
            "Respond ONLY with valid JSON in this exact shape. "
            "No prose, no code fences:\n"
            "{\"is_reasoning\": true, \"topic\": \"Topic Name\"}\n\n"
            "Question:\n"
            f"\"\"\"\n{question_text}\n\"\"\""
        )

    def _cache_key(self, question_text: str) -> str:
        normalized = re.sub(
            r"\s+",
            " ",
            question_text.strip().lower(),
        )

        payload = f"{self.model}|{normalized}"

        return hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

    def _load_cache(self) -> dict:
        if not self.CACHE_PATH.exists():
            return {}

        try:
            with self.CACHE_PATH.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

            return {}

        except Exception:
            return {}

    def _save_cache(self) -> None:
        self.CACHE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.CACHE_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.cache,
                file,
                ensure_ascii=False,
                indent=2,
            )

    @staticmethod
    def _safe_json(raw: str) -> dict | None:
        if not raw:
            return None

        text = raw.strip()

        if text.startswith(""):
            text = text.strip("`")
            text = re.sub(
                r"^\s*json",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

        return None