import fitz


class PDFExtractor:

    def __init__(
        self,
        pdf_path: str,
    ):

        self.pdf_path = pdf_path

    def extract_pages(
        self,
    ):

        document = fitz.open(
            self.pdf_path
        )

        pages = []

        for page_index in range(
            len(document)
        ):

            page = document[
                page_index
            ]

            blocks = (
                self._extract_blocks(
                    page
                )
            )

            pages.append(
                {
                    "page_number":
                    page_index + 1,

                    "blocks":
                    blocks,
                }
            )

        document.close()

        return pages

    def _extract_blocks(
        self,
        page,
    ):

        raw_blocks = page.get_text(
            "blocks"
        )

        cleaned_blocks = []

        for block in raw_blocks:

            try:

                x0 = block[0]
                y0 = block[1]
                x1 = block[2]
                y1 = block[3]

                text = block[4]

                if not text:
                    continue

                text = text.strip()

                if not text:
                    continue

                # REMOVE VERY SHORT
                # RANDOM OCR GARBAGE

                if (
                    len(text) <= 1
                ):

                    continue

                cleaned_blocks.append(
                    {
                        "text": text,
                        "bbox": (
                            x0,
                            y0,
                            x1,
                            y1,
                        ),
                    }
                )

            except Exception:
                continue

        # =========================
        # COLUMN DETECTION
        # =========================

        left_column = []

        right_column = []

        page_width = page.rect.width

        midpoint = (
            page_width / 2
        )

        for block in cleaned_blocks:

            x0 = block["bbox"][0]

            if x0 < midpoint:

                left_column.append(
                    block
                )

            else:

                right_column.append(
                    block
                )

        # =========================
        # SORT TOP TO BOTTOM
        # =========================

        left_column.sort(
            key=lambda b:
            (
                b["bbox"][1],
                b["bbox"][0],
            )
        )

        right_column.sort(
            key=lambda b:
            (
                b["bbox"][1],
                b["bbox"][0],
            )
        )

        # =========================
        # REBUILD READING ORDER
        # =========================

        ordered_blocks = (
            left_column
            + right_column
        )

        return ordered_blocks