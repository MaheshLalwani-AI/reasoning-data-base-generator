import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from extraction.answer_detector import (
    AnswerDetector,
)

from extraction.excel_writer import (
    ExcelWriter,
)

from extraction.extractor import (
    PDFExtractor,
)

from extraction.parsers.metadata_parser import (
    QuestionParser,
)

from solving.ai_solver import (
    AISolver,
)

from solving.topic_classifier import (
    TopicClassifier,
)

from solving.verifier import (
    AnswerVerifier,
)


def get_pdf_path() -> Path:

    pdf_folder = Path(
        "data/pdfs"
    )

    pdf_files = sorted(
        pdf_folder.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDFs found in data/pdfs"
        )

    print(
        f"\nPDFs found: "
        f"{len(pdf_files)}"
    )

    for pdf in pdf_files:

        print(
            f"- {pdf.name}"
        )

    print()

    return pdf_files[0]


def main():

    print(
        "\n======================="
    )

    print(
        "QUESTION COLLECTOR"
    )

    print(
        "=======================\n"
    )

    load_dotenv()

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    pdf_path = get_pdf_path()

    print(
        f"Using PDF: "
        f"{pdf_path.name}\n"
    )

    # STEP 1
    # EXTRACT PDF

    print(
        "[1] Extracting PDF..."
    )

    extractor = PDFExtractor(
        pdf_path=str(
            pdf_path
        )
    )

    pages = (
        extractor.extract_pages()
    )

    print(
        f"Pages extracted: "
        f"{len(pages)}\n"
    )

    # STEP 2
    # PARSE QUESTIONS

    print(
        "[2] Parsing questions..."
    )

    parser = QuestionParser()

    questions = (
        parser.parse_pages(
            pages
        )
    )

    print(
        f"Questions parsed: "
        f"{len(questions)}\n"
    )

    if questions:

        print(
            "FIRST QUESTION:\n"
        )

        print(
            questions[0]
        )

        print()

    # STEP 3
    # DETECT ANSWERS

    print(
        "[3] Detecting answers..."
    )

    detector = AnswerDetector(
        pdf_path=str(
            pdf_path
        )
    )

    answers = (
        detector.detect_answers()
    )

    print(
        f"Answers detected: "
        f"{len(answers)}\n"
    )

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
                < len(
                    question.options
                )
            ):

                question.correct_answer = (
                    question.options[
                        option_index
                    ]
                )

                mapped_count += 1

        except Exception as e:

            print(
                f"Answer mapping failed "
                f"for Q{qno}: {e}"
            )

    print(
        f"Mapped answers: "
        f"{mapped_count}\n"
    )

    # STEP 4
    # AI SOLVING

    if api_key:

        print(
            "[4] AI solving..."
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

        verifier = (
            AnswerVerifier()
        )

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

            question.reasoning_type = (
                result.get(
                    "topic"
                )
            )

            question.solution = (
                result.get(
                    "solution"
                )
            )

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
            f"AI solved: "
            f"{solved_count}\n"
        )

    else:

        print(
            "[4] AI solving skipped "
            "(No API key)\n"
        )

    # STEP 5
    # WRITE EXCEL

    print(
        "[5] Writing Excel..."
    )

    output_path = Path(
        "data/extracted/extracted_questions.xlsx"
    )

    writer = ExcelWriter()

    writer.write(

        questions=questions,

        output_path=str(
            output_path
        ),

        pdf_path=str(
            pdf_path
        ),
    )

    print(
        "\n======================="
    )

    print(
        "EXCEL GENERATED"
    )

    print(
        f"Output: "
        f"{output_path}"
    )

    print(
        "=======================\n"
    )


if __name__ == "__main__":
    main()