import json
import asyncio

from openai import AsyncOpenAI


class AISolver:

    MAX_CONCURRENT = 5

    def __init__(
        self,
        api_key: str,
        topics_text: str,
    ):

        self.topics_text = (
            topics_text
        )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        self.semaphore = (
            asyncio.Semaphore(
                self.MAX_CONCURRENT
            )
        )

    async def solve_question(
        self,
        question_text: str,
        options: list[str],
    ) -> dict:

        async with self.semaphore:

            prompt = self._build_prompt(
                question_text,
                options,
            )

            response = await (
                self.client.chat.completions.create(
                    model="deepseek/deepseek-v4-flash",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert reasoning solver.\n"
                                "Return ONLY valid JSON.\n"
                                "Do not return markdown.\n"
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.1,
                    response_format={
                        "type": "json_object"
                    },
                    extra_body={
                        "reasoning": {
                            "effort": "high"
                        }
                    },
                )
            )

            text = (
                response
                .choices[0]
                .message
                .content
            )

            try:

                return json.loads(
                    text
                )

            except Exception:

                cleaned = (
                    self._extract_json(
                        text
                    )
                )

                if cleaned:

                    try:

                        return json.loads(
                            cleaned
                        )

                    except Exception:
                        pass

                return {
                    "topic": None,
                    "solution": (
                        "Failed parsing AI response"
                    ),
                    "correct_option_number": None,
                }

    async def solve_batch(
        self,
        questions: list,
    ) -> list[dict]:

        tasks = []

        for question in questions:

            task = (
                self.solve_question(
                    question_text=(
                        question.question_text
                    ),
                    options=(
                        question.options
                    ),
                )
            )

            tasks.append(
                task
            )

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        return results

    def _build_prompt(
        self,
        question_text: str,
        options: list[str],
    ) -> str:

        option_text = ""

        for i, option in enumerate(
            options,
            start=1,
        ):

            option_text += (
                f"{i}. {option}\n"
            )

        return f"""
Solve the reasoning question carefully.

Question:
{question_text}

Options:
{option_text}

Choose ONLY ONE topic
from this list:

{self.topics_text}

Return ONLY valid JSON:

{{
    "topic": "...",
    "solution": "...",
    "correct_option_number": 1
}}
"""

    def _extract_json(
        self,
        text: str,
    ) -> str | None:

        start = text.find("{")

        end = text.rfind("}")

        if (
            start == -1
            or end == -1
        ):

            return None

        return text[
            start : end + 1
        ]