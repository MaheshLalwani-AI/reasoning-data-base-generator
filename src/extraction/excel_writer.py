from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

from models import Question


class ExcelWriter:

    HEADERS = [
        "Exam Name",
        "Page Number",
        "Question Number",
        "Question",
        "Question Image",
        "Option 1",
        "Option 2",
        "Option 3",
        "Option 4",
        "Correct Answer",
        "AI Answer",
        "Verification Status",
        "Reasoning Type",
        "Regex Topic",
        "LLM Topic",
        "Solution",
    ]

    def write(
        self,
        questions: list[Question],
        output_path: str,
    ) -> None:

        output_file = Path(output_path)

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        workbook = openpyxl.Workbook()

        sheet = workbook.active

        sheet.title = "Questions"

        sheet.append(self.HEADERS)

        for question in questions:

            options = list(question.options)

            while len(options) < 4:
                options.append("")

            row = [
                question.exam_name,
                question.page_number,
                question.question_number,
                question.question_text,
                question.question_image,
                options[0],
                options[1],
                options[2],
                options[3],
                question.correct_answer,
                question.ai_answer,
                question.verification_status,
                question.reasoning_type,
                question.regex_topic,
                question.llm_topic,
                question.solution,
            ]

            sheet.append(row)

        # Mild auto-width
        for col_index, _ in enumerate(
            self.HEADERS,
            start=1,
        ):
            letter = get_column_letter(
                col_index
            )
            sheet.column_dimensions[
                letter
            ].width = 22

        workbook.save(output_file)