import re

from src.models import Question


class QuestionParser:

    QUESTION_PATTERN = re.compile(
        r"""
        Question\ Number\s*:\s*(\d+)
        .*?
        Question\ Id\s*:\s*(\d+)
        .*?
        (?=Question\ Number\s*:|\Z)
        """,
        re.DOTALL | re.VERBOSE,
    )

    OPTION_PATTERN = re.compile(
        r"""
        \n
        (\d+)\.
        \s*
        (.*?)
        (?=
            \n\d+\.
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    METADATA_PATTERNS = [
        r"Question Number\s*:\s*\d+",
        r"Question Id\s*:\s*\d+",
        r"Question Type\s*:\s*\w+",
        r"Correct Marks\s*:\s*[\d\.]+",
        r"Wrong Marks\s*:\s*[\d\.]+",
    ]

    def parse_pages(
        self,
        pages: list[dict],
    ) -> list[Question]:

        questions = []

        seen_numbers = set()

        for page in pages:

            try:

                page_number = page.get(
                    "page_number",
                    0,
                )

                blocks = page.get(
                    "blocks",
                    [],
                )

                if not blocks:
                    continue

                page_text = "\n".join(
                    block.get(
                        "text",
                        "",
                    )
                    for block in blocks
                )

                matches = list(
                    self.QUESTION_PATTERN.finditer(
                        page_text
                    )
                )

                for match in matches:

                    try:

                        full_block = (
                            match.group(0)
                        )

                        question_number = int(
                            match.group(1)
                        )

                        question_id = (
                            match.group(2)
                        )

                        if (
                            question_number
                            in seen_numbers
                        ):

                            continue

                        parsed = (
                            self._parse_question(
                                block=full_block,
                                page_number=page_number,
                                question_number=question_number,
                                question_id=question_id,
                            )
                        )

                        if parsed is None:
                            continue

                        questions.append(
                            parsed
                        )

                        seen_numbers.add(
                            question_number
                        )

                    except Exception as e:

                        print(
                            f"Skipped malformed question block: {e}"
                        )

            except Exception as e:

                print(
                    f"Skipped malformed page: {e}"
                )

        return questions

    def _parse_question(
        self,
        block: str,
        page_number: int,
        question_number: int,
        question_id: str,
    ) -> Question | None:

        if (
            "Options :" not in block
        ):

            return None

        parts = block.split(
            "Options :",
            maxsplit=1,
        )

        if len(parts) != 2:
            return None

        question_part = parts[0]

        options_part = parts[1]

        question_text = (
            self._clean_question(
                question_part
            )
        )

        options = (
            self._extract_options(
                options_part
            )
        )

        if not question_text:
            return None

        if not options:
            return None

        if len(options) < 2:
            return None

        return Question(
            exam_name="",
            page_number=page_number,
            question_number=question_number,
            question_id=question_id,
            question_text=question_text,
            options=options,
            correct_answer="",
            ai_answer="",
            verification_status="",
            reasoning_type="",
            solution="",
        )

    def _clean_question(
        self,
        text: str,
    ) -> str:

        for pattern in (
            self.METADATA_PATTERNS
        ):

            text = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE,
            )

        cleaned_lines = []

        for line in text.splitlines():

            line = line.rstrip()

            if not line.strip():
                continue

            if (
                self._is_non_english_dominant(
                    line
                )
            ):

                continue

            cleaned_lines.append(
                line
            )

        return "\n".join(
            cleaned_lines
        ).strip()

    def _extract_options(
        self,
        text: str,
    ) -> list[str]:

        matches = (
            self.OPTION_PATTERN.findall(
                text
            )
        )

        cleaned = []

        for _, option in matches:

            try:

                lines = []

                for line in (
                    option.splitlines()
                ):

                    line = line.rstrip()

                    if not line.strip():
                        continue

                    if (
                        self._is_non_english_dominant(
                            line
                        )
                    ):

                        continue

                    lines.append(
                        line
                    )

                option = "\n".join(
                    lines
                ).strip()

                if option:

                    cleaned.append(
                        option
                    )

            except Exception:
                continue

        return cleaned[:4]

    def _is_non_english_dominant(
        self,
        text: str,
    ) -> bool:

        english_chars = len(
            re.findall(
                r"[A-Za-z]",
                text,
            )
        )

        total_letters = len(
            re.findall(
                r"[^\W\d_]",
                text,
                flags=re.UNICODE,
            )
        )

        if total_letters == 0:
            return False

        english_ratio = (
            english_chars
            / total_letters
        )

        return english_ratio < 0.5