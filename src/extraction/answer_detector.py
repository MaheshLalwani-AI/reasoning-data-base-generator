import fitz
import re


class AnswerDetector:

    GREEN = 32768

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

        for page in self.document:

            text_dict = page.get_text(
                "dict"
            )

            for block in text_dict["blocks"]:

                if "lines" not in block:
                    continue

                for line in block["lines"]:

                    spans = line["spans"]

                    line_text = "".join(
                        span["text"]
                        for span in spans
                    ).strip()

                    if not line_text:
                        continue

                    # detect question number

                    q_match = re.search(
                        r"Question Number\s*:\s*(\d+)",
                        line_text,
                    )

                    if q_match:

                        current_question = int(
                            q_match.group(1)
                        )

                        continue

                    # detect green option

                    if (
                        current_question
                        and spans
                    ):

                        first_span = spans[0]

                        color = first_span.get(
                            "color"
                        )

                        if color != self.GREEN:
                            continue

                        option_match = re.match(
                            r"(\d+)\.",
                            line_text,
                        )

                        if option_match:

                            answers[
                                current_question
                            ] = option_match.group(
                                1
                            )

        return answers