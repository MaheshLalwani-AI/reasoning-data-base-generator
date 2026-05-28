from src.core.document_models import (
    DocumentFile,
)

from src.parsing.parsers.metadata_parser import (
    MetadataParser,
)


class ParserRouter:

    def parse(
        self,
        document: DocumentFile,
    ):

        sample_texts = []

        for page in document.pages[:3]:

            for block in page.blocks:

                sample_texts.append(
                    block.text
                )

        sample = "\n".join(
            sample_texts
        )

        if (
            "Question Number"
            in sample
        ):

            print(
                "Using MetadataParser"
            )

            parser = (
                MetadataParser()
            )

            return parser.parse(
                document
            )

        print(
            "No compatible parser found."
        )

        return []