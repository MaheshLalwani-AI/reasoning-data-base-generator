from openpyxl import Workbook

from openpyxl.styles import (
    Alignment,
)

from openpyxl.utils import (
    get_column_letter,
)

from models import Question


class ExcelWriter:

    HEADERS = [
        "Exam Name",
        "PDF Page No",
        "Question Number",
        "Question ID",
        "Question",
        "Option 1",
        "Option 2",
        "Option 3",
        "Option 4",
        "PDF Correct Answer",
    ]

    def write(
        self,
        questions: list[Question],
        output_path: str,
        pdf_path: str = "",
    ):

        workbook = Workbook()

        sheet = workbook.active

        sheet.title = "Questions"

        # HEADERS

        for col_num, header in enumerate(
            self.HEADERS,
            start=1,
        ):

            cell = sheet.cell(
                row=1,
                column=col_num,
                value=header,
            )

            cell.alignment = Alignment(
                wrap_text=True,
                vertical="top",
            )

        current_row = 2

        # DATA

        for question in questions:

            try:

                if question is None:
                    continue

                options = (
                    question.options
                )

                if options is None:
                    options = []

                exam_name = getattr(
                    question,
                    "exam_name",
                    "",
                )

                row = [
                    exam_name,
                    getattr(
                        question,
                        "page_number",
                        "",
                    ),
                    getattr(
                        question,
                        "question_number",
                        "",
                    ),
                    getattr(
                        question,
                        "question_id",
                        "",
                    ),
                    getattr(
                        question,
                        "question_text",
                        "",
                    ),
                    options[0]
                    if len(options) > 0
                    else "",
                    options[1]
                    if len(options) > 1
                    else "",
                    options[2]
                    if len(options) > 2
                    else "",
                    options[3]
                    if len(options) > 3
                    else "",
                    getattr(
                        question,
                        "correct_answer",
                        "",
                    ),
                ]

                max_lines = 1

                for col_num, value in enumerate(
                    row,
                    start=1,
                ):

                    if value is None:
                        value = ""

                    value = str(
                        value
                    ).replace(
                        "\r\n",
                        "\n",
                    )

                    cell = sheet.cell(
                        row=current_row,
                        column=col_num,
                        value=value,
                    )

                    cell.alignment = Alignment(
                        wrap_text=True,
                        vertical="top",
                    )

                    line_count = (
                        value.count("\n")
                        + 1
                    )

                    if (
                        line_count
                        > max_lines
                    ):

                        max_lines = (
                            line_count
                        )

                # AUTO ROW HEIGHT

                sheet.row_dimensions[
                    current_row
                ].height = max(
                    25,
                    max_lines * 18,
                )

                current_row += 1

            except Exception as e:

                print(
                    f"Skipped malformed question: {e}"
                )

        # COLUMN WIDTHS

        widths = {
            1: 35,
            2: 12,
            3: 15,
            4: 18,
            5: 90,
            6: 35,
            7: 35,
            8: 35,
            9: 35,
            10: 25,
        }

        for col_num, width in widths.items():

            column_letter = (
                get_column_letter(
                    col_num
                )
            )

            sheet.column_dimensions[
                column_letter
            ].width = width

        workbook.save(
            output_path
        )