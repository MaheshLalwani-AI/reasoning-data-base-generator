import pandas as pd


class ExcelReader:

    def read_questions(
        self,
        excel_path: str,
    ) -> list[dict]:

        df = pd.read_excel(
            excel_path
        )

        questions = []

        for _, row in df.iterrows():

            options = []

            for i in range(1, 5):

                value = row.get(
                    f"Option {i}"
                )

                if pd.notna(value):

                    options.append(
                        str(value)
                    )

            questions.append(
                {
                    "question_number": row.get(
                        "Question Number"
                    ),
                    "question_text": row.get(
                        "Question"
                    ),
                    "options": options,
                    "pdf_answer": row.get(
                        "PDF Correct Answer"
                    ),
                }
            )

        return questions