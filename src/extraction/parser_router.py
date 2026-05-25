import re

from src.extraction.parsers.metadata_parser import (
    QuestionParser as MetadataParser,
)

from src.extraction.parsers.plain_mcq_parser import (
    QuestionParser as PlainMCQParser,
)


class ParserRouter:

    def __init__(self):

        self.metadata_parser = (
            MetadataParser()
        )

        self.plain_mcq_parser = (
            PlainMCQParser()
        )

    def parse_pages(
        self,
        pages,
    ):

        sample_text = (
            self._collect_sample_text(
                pages
            )
        )

        # =========================
        # FORMAT FAMILY 1
        # Metadata PDFs
        # =========================

        if (
            "Question Number"
            in sample_text
            and
            "Question Id"
            in sample_text
        ):

            print(
                "Detected: metadata_parser"
            )

            return (
                self.metadata_parser.parse_pages(
                    pages
                )
            )

        # =========================
        # FORMAT FAMILY 2
        # Plain MCQ PDFs
        # =========================

        plain_mcq_pattern = re.search(
            r"\n\s*\d+\.",
            sample_text,
        )

        option_pattern = re.search(
            r"\(\d\)",
            sample_text,
        )

        if (
            plain_mcq_pattern
            and
            option_pattern
        ):

            print(
                "Detected: plain_mcq_parser"
            )

            return (
                self.plain_mcq_parser.parse_pages(
                    pages
                )
            )

        # =========================
        # NO MATCH
        # =========================

        print(
            "No compatible parser found."
        )

        return []

    def _collect_sample_text(
        self,
        pages,
    ) -> str:

        texts = []

        # CHECK FIRST 5 PAGES

        for page in pages[:5]:

            blocks = page.get(
                "blocks",
                [],
            )

            for block in blocks:

                text = block.get(
                    "text",
                    "",
                )

                texts.append(text)

        return "\n".join(
            texts
        )