import fitz
import re


class AnswerDetector:
    QUESTION_PATTERN = re.compile(
        r"""
        (?:
            Question\s*Number
            |
            Question\s*No\.?
            |
            Q\.?
        )
        \s*[:.\-]?\s*
        (\d+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    DIRECT_ANSWER_PATTERN = re.compile(
        r"""
        (?:
            Correct\s*Answer
            |
            Answer
        )
        \s*[:\-]\s*
        (?:Option\s*)?
        \(?
        ([1-4A-D])
        \)?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    OPTION_PATTERN = re.compile(
        r"""
        ^\s*
        (?:
            Ans\s*
        )?
        (?:
            Option\s*
        )?
        \(?
        ([1-4A-D])
        \)?
        \s*
        [.)\-:]
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    TICK_MARKS = (
        "✓",
        "✔",
        "☑",
        "✅",
        "[x]",
        "[X]",
        "(x)",
        "(X)",
    )

    def __init__(
        self,
        pdf_path: str,
    ):
        self.document = fitz.open(
            pdf_path
        )

    def detect_answers(
        self,
    ) -> dict:
        answers = {}

        current_question = None
        current_question_page = None

        for page in self.document:
            page_number = page.number + 1

            text_dict = page.get_text(
                "dict"
            )

            for block in text_dict.get(
                "blocks",
                [],
            ):
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    spans = line.get(
                        "spans",
                        [],
                    )

                    line_text = "".join(
                        span.get(
                            "text",
                            "",
                        )
                        for span in spans
                    ).strip()

                    if not line_text:
                        continue

                    q_match = self.QUESTION_PATTERN.search(
                        line_text
                    )

                    if q_match and "Question ID" not in line_text:
                        current_question = int(
                            q_match.group(1)
                        )
                        current_question_page = page_number

                    if not current_question:
                        continue

                    direct_answer = self._extract_direct_answer(
                        line_text
                    )

                    if direct_answer:
                        answers[
                            (
                                current_question_page,
                                current_question,
                            )
                        ] = direct_answer
                        continue

                    option_number = self._extract_option_number(
                        line_text
                    )

                    if not option_number:
                        continue

                    if self._line_is_marked_correct(
                        line_text=line_text,
                        spans=spans,
                    ):
                        answers[
                            (
                                current_question_page,
                                current_question,
                            )
                        ] = option_number

        return answers

    def _extract_direct_answer(
        self,
        text: str,
    ) -> str | None:
        match = self.DIRECT_ANSWER_PATTERN.search(
            text
        )

        if not match:
            return None

        return self._normalize_option(
            match.group(1)
        )

    def _extract_option_number(
        self,
        text: str,
    ) -> str | None:
        match = self.OPTION_PATTERN.search(
            text
        )

        if not match:
            return None

        return self._normalize_option(
            match.group(1)
        )

    def _normalize_option(
        self,
        value: str,
    ) -> str | None:
        value = value.strip().upper()

        letter_map = {
            "A": "1",
            "B": "2",
            "C": "3",
            "D": "4",
        }

        if value in letter_map:
            return letter_map[value]

        if value in {
            "1",
            "2",
            "3",
            "4",
        }:
            return value

        return None

    def _line_is_marked_correct(
        self,
        line_text: str,
        spans: list,
    ) -> bool:
        if any(
            mark in line_text
            for mark in self.TICK_MARKS
        ):
            return True

        if re.search(
            r"\bAns\s*[1-4A-D]?\b",
            line_text,
            flags=re.IGNORECASE,
        ):
            return True

        return any(
            self._span_is_green(
                span
            )
            for span in spans
        )

    def _span_is_green(
        self,
        span,
    ) -> bool:
        color = span.get(
            "color"
        )

        if color is None:
            return False

        red = (
            color >> 16
        ) & 255

        green = (
            color >> 8
        ) & 255

        blue = color & 255

        return (
            green >= 80
            and green > red * 1.2
            and green > blue * 1.2
        )