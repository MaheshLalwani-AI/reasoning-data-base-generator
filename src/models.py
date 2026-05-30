from dataclasses import dataclass, field


@dataclass
class Question:

    exam_name: str = ""

    page_number: int = 0

    question_number: int = 0

    question_id: str = ""

    question_text: str = ""

    question_image: str = ""

    options: list[str] = field(
        default_factory=list
    )

    correct_answer: str = ""

    ai_answer: str = ""

    verification_status: str = ""

    reasoning_type: str = ""

    regex_topic: str = ""

    is_reasoning: bool = True

    solution: str = ""