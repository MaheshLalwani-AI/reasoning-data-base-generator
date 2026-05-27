import re

from models import Question


class QuestionParser:

    QUESTION_PATTERN = re.compile(
        r"""
        (?=
            \n?\d+\.\s
        )
        """,
        re.VERBOSE,
    )

    OPTION_PATTERNS = [

        # (1) option

        re.compile(
            r"""
            \((\d)\)
            \s*
            (.*?)
            (?=
                \(\d\)
                |
                \n\d+\.\s
                |
                \Z
            )
            """,
            re.DOTALL | re.VERBOSE,
        ),

        # 1. option

        re.compile(
            r"""
            \n(\d)\.\s*
            (.*?)
            (?=
                \n\d\.\s
                |
                \n\d+\.\s
                |
                \Z
            )
            """,
            re.DOTALL | re.VERBOSE,
        ),

    ]

    def parse_pages(
        self,
        pages,
    ):

        questions = []

        seen = set()

        for page in pages:

            page_number = page.get(
                "page_number",
                0,
            )

            blocks = page.get(
                "blocks",
                [],
            )

            page_text = "\n".join(
                block.get(
                    "text",
                    "",
                )
                for block in blocks
            )

            chunks = re.split(
                self.QUESTION_PATTERN,
                page_text,
            )

            for chunk in chunks:

                try:

                    chunk = chunk.strip()

                    if len(chunk) < 40:
                        continue

                    q_match = re.match(
                        r"(\d+)\.",
                        chunk,
                    )

                    if not q_match:
                        continue

                    question_number = int(
                        q_match.group(1)
                    )

                    if question_number in seen:
                        continue

                    options = []

                    matched_pattern = None

                    for pattern in (
                        self.OPTION_PATTERNS
                    ):

                        matches = pattern.findall(
                            chunk
                        )

                        if len(matches) >= 2:

                            matched_pattern = (
                                pattern
                            )

                            for _, text in matches:

                                text = (
                                    self._clean_text(
                                        text
                                    )
                                )

                                if text:

                                    options.append(
                                        text
                                    )

                            break

                    if len(options) < 2:
                        continue

                    question_text = chunk

                    if matched_pattern:

                        question_text = (
                            matched_pattern.sub(
                                "",
                                question_text,
                            )
                        )

                    question_text = re.sub(
                        r"^\d+\.\s*",
                        "",
                        question_text,
                    )

                    question_text = (
                        self._clean_text(
                            question_text
                        )
                    )

                    if not question_text:
                        continue

                    question = Question(
                        exam_name="",
                        page_number=page_number,
                        question_number=question_number,
                        question_id="",
                        question_text=question_text,
                        options=options[:4],
                        correct_answer="",
                        ai_answer="",
                        verification_status="",
                        reasoning_type="",
                        solution="",
                    )

                    questions.append(
                        question
                    )

                    seen.add(
                        question_number
                    )

                except Exception as e:

                    print(
                        f"Skipped malformed question: {e}"
                    )

        return questions

    def _clean_text(
        self,
        text,
    ):

        lines = []

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            if (
                self._is_non_english_dominant(
                    line
                )
            ):

                continue

            # REMOVE OCR GARBAGE

            if len(line) <= 2:
                continue

            lines.append(
                line
            )

        return "\n".join(
            lines
        ).strip()

    def _is_non_english_dominant(
        self,
        text,
    ):

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

        ratio = (
            english_chars
            / total_letters
        )

        return ratio < 0.40