import re

from models import Question


class QuestionParser:

    # Pattern for "Q.1", "Q.2", etc.
    QUESTION_PATTERN = re.compile(
        r"""
        (
            Q\.\d+.*?
        )
        (?=
            Q\.\d+
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    # Pattern for plain "1.", "2.", etc. at start of a line.
    # Captures the full question text (number + content) in group 1.
    QUESTION_PATTERN_PLAIN = re.compile(
        r"""
        (
            ^\s*\d+\.\s+
            .*?
        )
        (?=
            ^\s*\d+\.\s+
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            \Z
        )
        """,
        re.DOTALL | re.MULTILINE | re.VERBOSE,
    )

    # Pattern for "Que. 1", "Que. 2", etc.
    QUESTION_PATTERN_QUE = re.compile(
        r"""
        (
            Que\.\s*\d+\s*
            .*?
        )
        (?=
            Que\.\s*\d+
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    QUESTION_NUMBER_PATTERN = re.compile(
        r"Q\.(\d+)"
    )

    QUESTION_NUMBER_PATTERN_PLAIN = re.compile(
        r"^\s*(\d+)\.",
        re.MULTILINE,
    )

    QUESTION_NUMBER_PATTERN_QUE = re.compile(
        r"Que\.\s*(\d+)",
    )

    QUESTION_ID_PATTERN = re.compile(
        r"""
        Question\s*ID
        \s*:\s*
        (\d+)
        """,
        re.VERBOSE,
    )

    CHOSEN_OPTION_PATTERN = re.compile(
        r"""
        Chosen\s*Option
        \s*:\s*
        (\d+)
        """,
        re.VERBOSE,
    )

    # Pattern for numbered options: "1.", "2.", etc.
    # Handles optional prefixes like:
    #   "x 1." / "X 1."  (crossed-out/wrong)
    #   "s/ 1."          (ticked/correct)
    #   "^ 1." / "\^ 1." (ticked/correct)
    #   "Ans 1."         (answer declaration)
    #   "Ans x 1."       (answer crossed-out)
    #   "Ans A 1."       (lettered answer + numbered option)
    #   "Ans s/ 1."      (ticked answer)
    #   "Ans ^ 1."       (ticked answer)
    #   "Ans X 1."       (crossed-out answer)
    OPTION_PATTERN = re.compile(
        r"""
        ^\s*
        (?:
            Ans\s+
        )?
        (?:
            [xX]|s/|\^|\\\^
        )?
        \s*
        (\d+)\.
        \s*
        (.*?)
        (?=
            \s*(?:(?:[xX]|s/|\^|\\\^)?\s*(?:Ans\s+)?\d+\.)
            |
            Question\s*ID
            |
            Chosen\s*Option
            |
            Status
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            ^\s*\d+\.\s+\d+[^\.]
            |
            ^\s*Que\.\s*\d+
            |
            \bPage\s*-\s*\d+
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE | re.MULTILINE,
    )

    # Pattern for lettered options: "(a)", "(b)", "(c)", "(d)",
    # "(A)", "(B)", "(C)", "(D)", "A)", "B)", "C)", "D)".
    # Matches both newline-separated and inline formats.
    LETTER_OPTION_PATTERN = re.compile(
        r"""
        \s*
        \(?
        ([a-dA-D])
        \)
        \s*
        (.*?)
        (?=
            \s*\(?[a-dA-D]\)
            |
            \n\s*\d+\.
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    # Pattern for "1.)", "2.)", "3.)" style options (with close paren after digit)
    PAREN_DIGIT_OPTION_PATTERN = re.compile(
        r"""
        (\d+)
        \.\)
        \s*
        (.*?)
        (?=
            \d+\.\)
            |
            Correct\s*Option
            |
            Correct\s*Answer
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    def parse_pages(
        self,
        pages,
    ):

        questions = []

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

            # Try Q-prefixed pattern first
            matches = list(
                self.QUESTION_PATTERN.finditer(
                    page_text
                )
            )

            # Fall back to plain-numbered pattern if Q-prefixed
            # found nothing
            if not matches:
                matches = list(
                    self.QUESTION_PATTERN_PLAIN.finditer(
                        page_text
                    )
                )

            # Fall back to Que. pattern
            if not matches:
                matches = list(
                    self.QUESTION_PATTERN_QUE.finditer(
                        page_text
                    )
                )

            for match in matches:

                try:

                    chunk = (
                        match.group(1)
                        .strip()
                    )

                    # Determine which number pattern to use
                    qno_match = (
                        self.QUESTION_NUMBER_PATTERN.search(
                            chunk
                        )
                    )

                    if not qno_match:
                        qno_match = (
                            self.QUESTION_NUMBER_PATTERN_PLAIN.search(
                                chunk
                            )
                        )

                    if not qno_match:
                        qno_match = (
                            self.QUESTION_NUMBER_PATTERN_QUE.search(
                                chunk
                            )
                        )

                    if not qno_match:
                        continue

                    question_number = int(
                        qno_match.group(1)
                    )

                    parsed = (
                        self._parse_question(
                            chunk=chunk,
                            page_number=page_number,
                            question_number=question_number,
                            qno_match=qno_match,
                        )
                    )

                    if parsed is None:
                        continue

                    questions.append(
                        parsed
                    )

                except Exception as e:

                    print(
                        f"Skipped malformed question: {e}"
                    )

        return questions

    def _parse_question(
        self,
        chunk,
        page_number,
        question_number,
        qno_match=None,
    ):

        question_id = ""

        # Remove question number prefix from chunk text
        # (e.g., "Que. 2", "Q.5", "1.") so it doesn't leak into question text
        if qno_match:
            chunk = self.QUESTION_NUMBER_PATTERN_QUE.sub("", chunk, count=1)
            chunk = self.QUESTION_NUMBER_PATTERN.sub("", chunk, count=1)
            chunk = self.QUESTION_NUMBER_PATTERN_PLAIN.sub("", chunk, count=1)

        qid_match = (
            self.QUESTION_ID_PATTERN.search(
                chunk
            )
        )

        if qid_match:

            question_id = (
                qid_match.group(1)
            )

        # Try numbered options first: "1.", "2.", etc.
        option_matches = (
            self.OPTION_PATTERN.findall(
                chunk
            )
        )

        use_lettered = False
        options = []

        if option_matches:

            for _, option_text in option_matches:

                option_text = (
                    self._clean_text(
                        option_text
                    )
                )

                if option_text:

                    options.append(
                        option_text
                    )

        # Fall back to lettered options if not enough numbered options
        if len(options) < 2:

            options = []
            use_lettered = True

            letter_matches = (
                self.LETTER_OPTION_PATTERN.findall(
                    chunk
                )
            )

            for _, option_text in letter_matches:

                option_text = (
                    self._clean_text(
                        option_text
                    )
                )

                if option_text:

                    options.append(
                        option_text
                    )

        # Fall back to "1.)", "2.)" style options
        if len(options) < 2:

            options = []
            use_lettered = True

            paren_matches = (
                self.PAREN_DIGIT_OPTION_PATTERN.findall(
                    chunk
                )
            )

            for _, option_text in paren_matches:

                option_text = (
                    self._clean_text(
                        option_text
                    )
                )

                if option_text:

                    options.append(
                        option_text
                    )

        if len(options) < 2:

            return None

        # REMOVE OPTIONS FROM QUESTION TEXT
        if use_lettered:

            question_text = (
                self.LETTER_OPTION_PATTERN.sub(
                    "",
                    chunk,
                )
            )

            # Also try removing paren-digit options
            question_text = (
                self.PAREN_DIGIT_OPTION_PATTERN.sub(
                    "",
                    question_text,
                )
            )

        else:

            question_text = (
                self.OPTION_PATTERN.sub(
                    "",
                    chunk,
                )
            )

        # REMOVE METADATA

        question_text = re.sub(
            r"Question\s*ID\s*:.*",
            "",
            question_text,
        )

        question_text = re.sub(
            r"Chosen\s*Option\s*:.*",
            "",
            question_text,
        )

        question_text = re.sub(
            r"Status\s*:.*",
            "",
            question_text,
        )

        question_text = re.sub(
            r"Q\.\d+",
            "",
            question_text,
        )

        question_text = re.sub(
            r"^\s*\d+\.",
            "",
            question_text,
        )

        question_text = (
            self._clean_text(
                question_text
            )
        )

        if not question_text:

            return None

        return Question(
            exam_name="",
            page_number=page_number,
            question_number=question_number,
            question_id=question_id,
            question_text=question_text,
            options=options[:5],
            correct_answer="",
            ai_answer="",
            verification_status="",
            reasoning_type="",
            solution="",
        )

    def _clean_text(
        self,
        text,
    ):

        lines = []

        for line in text.splitlines():

            # Remove standard and Unicode whitespace noise
            line = line.strip().strip('\xa0\ufeff\u200b')

            if not line:
                continue

            lower = line.lower()

            if "adda247" in lower:
                continue

            if "exammix" in lower:
                continue

            # Remove answer/prefix artifacts that may bleed into option text
            # Remove leading "Ans X", "Ans x", "Ans", etc.
            line = re.sub(r"^(?:\s*Ans\s*[xXs/^]?\s*)", "", line).strip()
            # Remove leading "x" / "X" / "s/" / "^" / "\^" prefixes (answer markers)
            line = re.sub(r"^[xXs/^\\]+\s*", "", line).strip()
            # Remove trailing "x" / "X" answer markers (e.g., after option text)
            line = re.sub(r"\s+[xX]\s*$", "", line).strip()
            # Remove leading ")" from option text (e.g., ") Uncle")
            line = re.sub(r"^\)\s*", "", line).strip()

            # Remove "Page - N" or "Page N" artifacts bleeding into text
            line = re.sub(r"\bPage\s*-\s*\d+\b", "", line).strip()
            line = re.sub(r"\bPage\s+\d+\b", "", line).strip()

            # Skip if residue line
            if not line or line.lower() in ('x', 'x.', '.x', 's/', '^', '\\^'):
                continue

            # Filter garbled non-English text (Malayalam/other script artifacts)
            if self._is_garbled_text(line):
                continue

            lines.append(
                line
            )

        return "\n".join(
            lines
        ).strip()

    @staticmethod
    def _is_garbled_text(text: str) -> bool:
        """Detect garbled/corrupted non-English text from PDF extraction."""
        if not text:
            return False
        # Count valid English/ASCII characters
        valid_chars = len(
            re.findall(
                r"[A-Za-z0-9\s\.\,\?\!\(\)\[\]\{\}\+\-\*\/\=\>\<\@\#\$\%\^\&\:\;\"\'\`\~\|\\\\]",
                text,
            )
        )
        total_chars = len(text.strip())
        if total_chars == 0:
            return False
        # Exempt very short text (could be math answers like "42°")
        if total_chars < 5:
            return False
        # If less than 40% valid characters, it's likely garbled
        return (valid_chars / total_chars) < 0.4