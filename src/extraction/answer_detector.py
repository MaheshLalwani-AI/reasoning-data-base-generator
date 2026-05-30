import fitz
import re
from collections import defaultdict


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

    # Pattern to identify an answer-marking prefix on an option line
    # Prefix can be: x, X (wrong), s/, ^, \^ (correct)
    # The line may optionally start with "Ans " followed by the prefix
    ANSWER_PREFIX_PATTERN = re.compile(
        r"""
        ^\s*
        (?:
            Ans\s+
        )?
        (?P<prefix>
            [xX]
            |
            s/
            |
            \^
            |
            \\\^
        )?
        \s*
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # Extract the numeric option number from a line like "1. text" or "Ans A 1. text"
    # Handles:
    #   "1." / "1)" / "1:" / "1 -"
    #   "A 1." / "A) 1." (letter + option number combos)
    # Does NOT match letters like "A)" / "a." / "B."
    OPTION_NUMBER_PATTERN = re.compile(
        r"""
        (?:
            [a-dA-D]
            \s*
        )?
        ([1-4])
        \s*
        [.)\-:]
        """,
        re.VERBOSE,
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
        """Detect correct answers per (page_number, question_number).

        Strategy: For each question, collect all its associated option lines.
        Determine the correct answer by checking the prefix on each option line:
        - Lines starting with 's/' or '^' or '\\^' are correct (ticked)
        - Lines starting with 'x' or 'X' are incorrect (crossed out)
        - Lines with no prefix but following an 'Ans' line may be assumed correct
          if all other options have 'x'/'X' prefixes (implicit correct answer)
        """
        answers = {}

        # Per-question: collect all option lines and their prefix markers
        # Key: (page_number, question_number)
        # Value: list of (option_number, prefix_type) where prefix_type is
        #        'correct' (s/, ^, \^), 'wrong' (x, X), or 'neutral' (no prefix)
        question_options = defaultdict(list)
        question_has_ans_line = defaultdict(bool)

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

                    # Check for question start
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

                    key = (
                        current_question_page,
                        current_question,
                    )

                    # Check for direct answer patterns (Correct Answer: X)
                    direct_answer = self._extract_direct_answer(
                        line_text
                    )

                    if direct_answer:
                        answers[key] = direct_answer
                        continue

                    # Track if this question has an "Ans" line
                    if re.match(
                        r"^\s*Ans\s",
                        line_text,
                        flags=re.IGNORECASE,
                    ):
                        question_has_ans_line[
                            key
                        ] = True

                    # Extract the prefix and option number
                    result = self._extract_option_info(
                        line_text
                    )

                    if result is None:
                        # Check for tick marks in the text itself
                        if any(
                            mark in line_text
                            for mark in self.TICK_MARKS
                        ):
                            # Try to extract option number from this line
                            opt_num = self._extract_any_option_number(
                                line_text
                            )
                            if opt_num:
                                question_options[
                                    key
                                ].append(
                                    (
                                        opt_num,
                                        "correct",
                                    )
                                )
                        continue

                    option_number, prefix_type = result

                    question_options[key].append(
                        (
                            option_number,
                            prefix_type,
                        )
                    )

        # Resolve answers from collected option data
        for key, options in question_options.items():
            if key in answers:
                continue  # Already resolved via direct answer

            # Strategy 1: Find options explicitly marked as correct (s/, ^, \^)
            correct_options = [
                opt_num
                for opt_num, ptype in options
                if ptype == "correct"
            ]

            if len(correct_options) == 1:
                answers[key] = correct_options[0]
                continue

            if len(correct_options) > 1:
                # Multiple correct marks - use the first one found
                answers[key] = correct_options[0]
                continue

            # Strategy 2: If no explicit correct marks, find the one option
            # that is NOT marked as wrong (x/X), assuming all others are x'd
            wrong_options = {
                opt_num
                for opt_num, ptype in options
                if ptype == "wrong"
            }

            neutral_options = [
                opt_num
                for opt_num, ptype in options
                if ptype == "neutral"
            ]

            if len(neutral_options) == 1 and len(wrong_options) >= 1:
                # The single unmarked option is the correct answer
                # (all other options were crossed out)
                answers[key] = neutral_options[0]
                continue

            # Strategy 3: Check for green-colored spans on option lines
            # (for PDFs that use color highlighting for correct answers)
            green_answer = self._find_green_answer_in_document(
                key
            )

            if green_answer:
                answers[key] = green_answer
                continue

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

    def _extract_option_info(
        self,
        text: str,
    ) -> tuple | None:
        """Extract (option_number, prefix_type) from a line like:
        'x 1. text' -> ('1', 'wrong')
        's/ 2. text' -> ('2', 'correct')
        'Ans A 1. text' -> ('1', 'neutral')
        '3. text' -> ('3', 'neutral')
        'Ans s/ 1. text' -> ('1', 'correct')
        'Ans X 3. text' -> ('3', 'wrong')
        Returns None if line is not an option line.
        """
        # First, check if this line looks like an option line
        # (has a number followed by period/dash/colon)
        opt_match = self.OPTION_NUMBER_PATTERN.search(
            text
        )

        if not opt_match:
            return None

        option_number = opt_match.group(1)

        # Check prefix
        prefix_match = self.ANSWER_PREFIX_PATTERN.match(
            text
        )

        prefix_raw = (
            prefix_match.group("prefix")
            if prefix_match
            else None
        )

        if prefix_raw is None:
            prefix_type = "neutral"
        elif prefix_raw.lower() == "x":
            prefix_type = "wrong"
        elif prefix_raw in (
            "s/",
            "^",
            "\\^",
        ):
            prefix_type = "correct"
        else:
            prefix_type = "neutral"

        return (
            option_number,
            prefix_type,
        )

    def _extract_any_option_number(
        self,
        text: str,
    ) -> str | None:
        """Extract any option number (1-4) from text, used as fallback."""
        match = self.OPTION_NUMBER_PATTERN.search(
            text
        )

        if match:
            return match.group(1)

        return None

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

    def _find_green_answer_in_document(
        self,
        target_key: tuple,
    ) -> str | None:
        """Search document for green-colored option text for a specific question.

        Used as fallback for PDFs that highlight correct answers in green.
        """
        for page in self.document:
            page_number = page.number + 1

            if page_number != target_key[0]:
                # Only check the target page to be efficient
                continue

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

                    # Check if this is an option line for the target question
                    opt_match = self.OPTION_NUMBER_PATTERN.search(
                        line_text
                    )

                    if not opt_match:
                        continue

                    option_number = opt_match.group(1)

                    # Check if any span has green color
                    any_green = any(
                        self._span_is_green(
                            span
                        )
                        for span in spans
                    )

                    if any_green:
                        return self._normalize_option(
                            option_number
                        )

        return None

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
