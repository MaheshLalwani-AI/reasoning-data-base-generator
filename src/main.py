import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from extractor import PDFExtractor
from parser import QuestionParser
from answer_detector import AnswerDetector
from excel_writer import ExcelWriter
from ai_solver import AISolver
from verifier import AnswerVerifier
from topic_classifier import TopicClassifier

def get_pdf_path() -> Path:

    data_folder = Path("data")

    pdf_files = list(
        data_folder.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDF found inside data folder."
        )

    if len(pdf_files) > 1:

        print(
            "\nWARNING:"
        )

        print(
            "Multiple PDFs found."
        )

        print(
            f"Using: {pdf_files[0].name}\n"
        )

    return pdf_files[0]


def main():

    print("\n==============================")

    print(
        "REASONING PDF AI SOLVER"
    )

    print("==============================\n")

    # LOAD ENV

    load_dotenv()

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise ValueError(
            "OPENROUTER_API_KEY not found in .env"
        )

    # AUTO DETECT PDF

    pdf_path = get_pdf_path()

    output_path = (
        Path("data")
        / "output.xlsx"
    )

    print(
        f"PDF Selected: "
        f"{pdf_path.name}\n"
    )

    # STEP 1
    # Extract PDF

    print(
        "[1] Extracting PDF..."
    )

    extractor = PDFExtractor(
        pdf_path=str(pdf_path)
    )

    pages = extractor.extract_pages()

    print(
        f"Pages extracted: "
        f"{len(pages)}\n"
    )

    # STEP 2
    # Parse Questions

    print(
        "[2] Parsing questions..."
    )

    parser = QuestionParser()

    questions = parser.parse_pages(
        pages
    )

    print(
        f"Questions parsed: "
        f"{len(questions)}\n"
    )

    # STEP 3
    # Detect PDF Answers

    print(
        "[3] Detecting PDF answers..."
    )

    detector = AnswerDetector(
        pdf_path=str(pdf_path)
    )

    answers = detector.detect_answers()

    print(
        f"Answers detected: "
        f"{len(answers)}"
    )

    print("\nAnswer Map:")

    print(answers)

    print()

    # MAP PDF ANSWERS

    mapped_count = 0

    for question in questions:

        qno = (
            question.question_number
        )

        if qno not in answers:
            continue

        try:

            option_number = int(
                answers[qno]
            )

            option_index = (
                option_number - 1
            )

            if (
                0
                <= option_index
                < len(question.options)
            ):

                question.correct_answer = (
                    question.options[
                        option_index
                    ]
                )

                mapped_count += 1

        except Exception as e:

            print(
                f"Failed mapping Q{qno}: {e}"
            )

    print(
        f"PDF answers mapped: "
        f"{mapped_count}\n"
    )

    # STEP 4
    # AI SOLVING

    print(
        "[4] Solving with DeepSeek V4 Flash..."
    )

    topic_classifier = (
        TopicClassifier(
            topics_file="topics.txt"
        )
    )

    solver = AISolver(
        api_key=api_key,
        topics_text=(
            topic_classifier
            .get_topics_text()
        ),
    )

    verifier = AnswerVerifier()

    results = asyncio.run(
        solver.solve_batch(
            questions
        )
    )

    solved_count = 0

    for question, result in zip(
        questions,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):

            print(
                f"Failed Q"
                f"{question.question_number}: "
                f"{result}"
            )

            continue

        # DEBUG PRINT

        print(
            f"\nQ{question.question_number} RESULT:"
        )

        print(result)

        # AI ANSWER

        option_number = result.get(
            "correct_option_number"
        )

        if (
            option_number
            and isinstance(
                option_number,
                int,
            )
            and 1 <= option_number
            <= len(question.options)
        ):

            question.ai_answer = (
                question.options[
                    option_number - 1
                ]
            )

        # IMPORTANT FIX
        # topic -> reasoning_type

        question.reasoning_type = (
            result.get("topic")
        )

        # SOLUTION

        question.solution = (
            result.get(
                "solution"
            )
        )

        # VERIFICATION

        question.verification_status = (
            verifier.verify(
                pdf_answer=(
                    question.correct_answer
                ),
                ai_answer=(
                    question.ai_answer
                ),
            )
        )

        solved_count += 1

    print(
        f"\nAI solved: "
        f"{solved_count}\n"
    )

    # STEP 5
    # WRITE EXCEL

    print(
        "[5] Writing Excel..."
    )

    writer = ExcelWriter()

    writer.write(
        questions=questions,
        output_path=str(
            output_path
        ),
        pdf_path=str(pdf_path),
    )

    print(
        "\n=============================="
    )

    print(
        "Excel generated successfully"
    )

    print(
        f"Output: {output_path}"
    )

    print(
        "==============================\n"
    )


if __name__ == "__main__":
    main()