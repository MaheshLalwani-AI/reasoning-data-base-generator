import re

from models import Question


class QuestionParser:

    QUESTION_PATTERN = re.compile(
        r"""
        (
            Q\.\d+.*?
        )
        (?=
            Q\.\d+
            |
            \Z
        )
        """,
        re.DOTALL | re.VERBOSE,
    )

    QUESTION_NUMBER_PATTERN = re.compile(
        r"Q\.(\d+)"
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

    OPTION_PATTERN = re.compile(
        r"""
        (?:
            Ans\s*
        )?
        (\d+)\.
        \s*
        (.*?)
        (?=
            (?:Ans\s*)?\d+\.
            |
            Question\s*ID
            |
            Chosen\s*Option
            |
            Status
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

            matches = list(
                self.QUESTION_PATTERN.finditer(
                    page_text
                )
            )

            for match in matches:

                try:

                    chunk = (
                        match.group(1)
                        .strip()
                    )

                    qno_match = (
                        self.QUESTION_NUMBER_PATTERN.search(
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
    ):

        question_id = ""

        qid_match = (
            self.QUESTION_ID_PATTERN.search(
                chunk
            )
        )

        if qid_match:

            question_id = (
                qid_match.group(1)
            )

        option_matches = (
            self.OPTION_PATTERN.findall(
                chunk
            )
        )

        options = []

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

        if len(options) < 2:

            return None

        # REMOVE OPTIONS

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
            options=options[:4],
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

            # Remove artifacts
            line = re.sub(r"(?i)\bAns\s*\d*\b", "", line).strip()
            line = re.sub(r"(?i)[\s\.]+[xX]\s*$", "", line).strip()

            # Skip if residue line
            if not line or line.lower() in ('x', 'x.', '.x'):
                continue

            lines.append(
                line
            )

        return "\n".join(
            lines
        ).strip()