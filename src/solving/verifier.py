class AnswerVerifier:

    def verify(
        self,
        pdf_answer: str | None,
        ai_answer: str | None,
    ) -> str:

        if not pdf_answer:
            return "NO PDF ANSWER"

        if not ai_answer:
            return "NO AI ANSWER"

        pdf_answer = (
            pdf_answer.strip().lower()
        )

        ai_answer = (
            ai_answer.strip().lower()
        )

        if pdf_answer == ai_answer:
            return "MATCH"

        return "MISMATCH"