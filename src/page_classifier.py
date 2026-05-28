import re
import os
from pathlib import Path


class PageClassifier:
    """
    Regex-based classifier that:
      1. Decides if a page/question is REASONING (vs English/Maths/GK/Science).
      2. Assigns a canonical topic name from topics.txt.
    """

    TOPICS_FILE = Path(__file__).parent.parent / "topics.txt"

    def __init__(self):
        self.canonical_topics = self._load_topics()
        self._build_patterns()
        self._compile()

    # ---------------------------------------------------------
    # Load canonical topic list
    # ---------------------------------------------------------
    def _load_topics(self):
        topics = []
        if self.TOPICS_FILE.exists():
            for line in self.TOPICS_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                topics.append(line)
        return set(topics)

    def _ensure_canonical(self, name):
        """Guard: if a topic isn't in topics.txt, fall back to Uncategorized."""
        return name if name in self.canonical_topics else "Uncategorized"

    # ---------------------------------------------------------
    # Build per-topic regex map
    # Each canonical topic -> list of regex strings
    # ---------------------------------------------------------
    def _build_patterns(self):
        self.topic_patterns = {
            # ===== Seating =====
            "Linear Seating Arrangement": [
                r"\bsit(?:ting)? in a (?:straight )?(?:row|line)\b",
                r"\bpeople are there in (?:a |the )?row\b",
                r"\blinear arrangement\b",
                r"\bfrom the left end\b",
                r"\bfrom the right end\b",
            ],
            "Circular Seating Arrangement": [
                r"\bcircular table\b",
                r"\bround table\b",
                r"\bfacing the (?:centre|center)\b",
                r"\bfacing outside\b",
                r"\bfacing away from the (?:centre|center)\b",
                r"\bsits? around a circular\b",
            ],
            "Square Seating Arrangement": [
                r"\bsquare(?:-shaped)? table\b",
                r"\bcorners of (?:the |a )?square\b",
                r"\bsides of (?:the |a )?square\b",
            ],
            "Triangular Seating Arrangement": [
                r"\btriangular table\b",
                r"\bcorners of (?:the |a )?triangle\b",
            ],
            "Parallel Row Seating": [
                r"\btwo parallel rows\b",
                r"\brow 1 .{0,40} row 2\b",
                r"\bfacing each other\b",
            ],

            # ===== Puzzles =====
            "Floor Puzzle": [
                r"\bdifferent floors\b",
                r"\b(?:lives|live) on (?:a |the )?(?:different |)floor\b",
                r"\beight[- ]?(?:storey|story|storeyed)\b",
                r"\bground floor is numbered\b",
            ],
            "Box Puzzle": [
                r"\b(?:different )?boxes?\b.{0,40}\b(?:one above|stacked|kept)\b",
                r"\bkept (?:immediately )?above\b",
                r"\bkept (?:immediately )?below\b",
                r"\bbox is kept between\b",
            ],
            "Month Based Puzzle": [
                r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b.{0,80}\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
                r"\bdifferent months of the (?:same )?year\b",
            ],
            "Day Based Puzzle": [
                r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b.{0,80}\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                r"\bdifferent days of the (?:same )?week\b",
            ],
            "Year/Age Puzzle": [
                r"\bborn in different years\b",
                r"\bdifferent ages\b",
                r"\beldest among\b",
                r"\byoungest among\b",
            ],
            "Scheduling Puzzle": [
                r"\bschedule\b.{0,40}\b(?:meeting|appointment|class|lecture)\b",
                r"\bdifferent time slots\b",
                r"\bappointments? on\b",
            ],
            "Categorization Puzzle": [
                r"\bdifferent (?:cities|colours|colors|fruits|brands|cars|subjects)\b.{0,80}\bdifferent\b",
                r"\beach one likes a different\b",
            ],

            # ===== Blood Relations =====
            "Blood Relations": [
                r"\bhow is .{0,40} related to\b",
                r"\b(?:father|mother|brother|sister|son|daughter|husband|wife|uncle|aunt|nephew|niece|cousin|grandfather|grandmother) of\b",
                r"\b(?:father's|mother's) (?:brother|sister|son|daughter)\b",
                r"\bpointing (?:to|at) (?:a |the )?(?:photograph|picture)\b",
            ],
            "Coded Blood Relations": [
                r"\b[A-Z]\s*[+\-×%@\$#&\*]\s*[A-Z]\b.{0,80}\brelated\b",
                r"\bp\s*[+\-×%@\$#&\*]\s*q\b.{0,80}\brelated\b",
                r"\bif .{0,40} means .{0,40} (?:brother|sister|father|mother|son|daughter)\b",
            ],

            # ===== Direction =====
            "Direction Sense": [
                r"\bfacing (?:north|south|east|west)\b",
                r"\btowards (?:north|south|east|west)\b",
                r"\bturns? (?:to (?:his|her|its) )?(?:left|right)\b",
                r"\b(?:north|south)[- ]?(?:east|west)\b",
                r"\ball turns are 90\b",
            ],
            "Distance and Displacement": [
                r"\bshortest distance\b",
                r"\bhow far\b.{0,40}\bfrom\b",
                r"\bfinal position\b",
                r"\bdisplacement from\b",
            ],

            # ===== Coding-Decoding =====
            "Letter Coding": [
                r"\bin a certain code language\b.{0,80}\b[A-Z]{3,}\s+is (?:written|coded)\b",
                r"\bis coded as\b.{0,40}\b[A-Z]{3,}\b",
            ],
            "Number Coding": [
                r"\bis coded as\b.{0,40}\b\d{2,}\b",
                r"\bcoded as\b.{0,20}\d+\b",
            ],
            "Symbol Coding": [
                r"\b[@#\$%&\*][A-Z][@#\$%&\*]\b",
                r"\bcoded using (?:the following )?symbols\b",
            ],
            "Mixed Coding-Decoding": [
                r"\bletter[- ]?(?:number )?cluster\b",
                r"\bletter[- ]?cluster\b",
                r"\b[A-Z]{2,}\d{2,}\b",
            ],
            "Coded Equations": [
                r"\bif\s*\+\s*means\b",
                r"\bif\s*[-×÷]\s*means\b",
                r"\binterchanged with\b.{0,40}\bsigns?\b",
            ],

            # ===== Series =====
            "Number Series": [
                r"\bnumber series\b",
                r"\b\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\?\b",
            ],
            "Letter Series": [
                r"\bletter series\b",
                r"\b[A-Z]\s*,\s*[A-Z]\s*,\s*[A-Z]\s*,\s*[A-Z]\s*,\s*\?\b",
            ],
            "Alphanumeric Series": [
                r"\balpha[- ]?numeric series\b",
                r"\b[A-Z]\d+\s+[A-Z]\d+\s+[A-Z]\d+\b",
            ],
            "Mixed Series": [
                r"\bmixed series\b",
            ],
            "Wrong Number Series": [
                r"\bwrong (?:number|term) (?:in the )?series\b",
                r"\bdoes not fit the (?:series|pattern)\b",
            ],

            # ===== Analogy & Classification =====
            "Analogy": [
                r"\bis (?:to|related to) .{0,30} as .{0,30} is to\b",
                r"\bsame (?:relationship|way|logic) as\b",
                r"\bfollows the same (?:logic|pattern)\b",
            ],
            "Classification (Odd One Out)": [
                r"\bodd one out\b",
                r"\bdoes not belong\b",
                r"\bwhich (?:one )?(?:does not|doesn'?t) belong\b",
                r"\bdifferent from (?:the )?(?:others|rest)\b",
            ],

            # ===== Alphabet & Word =====
            "Alphabet Test": [
                r"\b\d+(?:st|nd|rd|th) letter (?:from|to) the (?:left|right)\b",
                r"\bposition of letters? in the (?:english )?alphabet\b",
            ],
            "Dictionary Order": [
                r"\bdictionary order\b",
                r"\balphabetical order\b",
            ],
            "Word Formation": [
                r"\bmeaningful word\b",
                r"\bword formation\b",
                r"\busing the letters\b.{0,40}\bword\b",
            ],
            "Letter Cluster": [
                r"\bletter pair\b",
                r"\bletter group\b",
                r"\bletter cluster\b",
            ],

            # ===== Logical =====
            "Syllogism": [
                r"\bstatements?:\s*\n?.{0,200}\bconclusions?:\b",
                r"\ball\s+\w+\s+are\s+\w+\b",
                r"\bno\s+\w+\s+is\s+\w+\b",
                r"\bsome\s+\w+\s+are\s+\w+\b",
                r"\bonly conclusion (?:i|ii|iii|iv) follows\b",
                r"\bboth conclusions follow\b",
            ],
            "Statement and Conclusion": [
                r"\bstatement and conclusion\b",
                r"\blogically follows from the statement\b",
            ],
            "Statement and Assumption": [
                r"\bstatement and assumption\b",
                r"\bimplicit in the statement\b",
            ],
            "Statement and Argument": [
                r"\bstatement and argument\b",
                r"\bstrong argument\b",
                r"\bweak argument\b",
            ],
            "Statement and Course of Action": [
                r"\bstatement and course of action\b",
                r"\bcourse of action\b",
            ],
            "Statement and Inference": [
                r"\bstatement and inference\b",
                r"\bdefinitely true\b.{0,40}\bstatement\b",
            ],
            "Cause and Effect": [
                r"\bcause and effect\b",
                r"\bindependent causes?\b",
            ],
            "Assertion and Reason": [
                r"\bassertion and reason\b",
                r"\bassertion \(a\)\b.{0,80}\breason \(r\)\b",
            ],

            # ===== Data Sufficiency =====
            "Data Sufficiency": [
                r"\bdata sufficiency\b",
                r"\bstatement i alone\b",
                r"\bstatement ii alone\b",
                r"\bquestion can be answered\b",
                r"\beither statement (?:alone )?is sufficient\b",
            ],

            # ===== Ranking =====
            "Ranking and Order": [
                r"\brank from the (?:top|bottom)\b",
                r"\bposition from the (?:left|right|top|bottom)\b",
                r"\b(?:tallest|shortest|heaviest|lightest) among\b",
                r"\barranged in (?:ascending|descending) order\b",
            ],

            # ===== Input-Output =====
            "Machine Input-Output": [
                r"\binput\s*[:\-]\s*.{0,80}\bstep i\b",
                r"\bmachine input\b",
                r"\bstep (?:i|ii|iii|iv|v)\b.{0,80}\bstep (?:ii|iii|iv|v|vi)\b",
            ],

            # ===== Inequality =====
            "Mathematical Inequality": [
                r"\b[A-Z]\s*[<>]\s*[A-Z]\s*[<>]\s*[A-Z]\b",
                r"\b[A-Z]\s*[<>=]\s*[A-Z]\b.{0,40}\bconclusion\b",
            ],
            "Coded Inequality": [
                r"\bcoded inequality\b",
                r"\bnot greater than\b",
                r"\bnot less than\b",
                r"\bif .{0,40} means (?:greater|less) than\b",
            ],

            # ===== Clock & Calendar =====
            "Clock": [
                r"\bangle between the hands\b",
                r"\b(?:hour|minute) hand\b",
                r"\bclock shows\b",
                r"\bmirror image of (?:the )?clock\b",
            ],
            "Calendar": [
                r"\bday of the week\b",
                r"\bwhat day (?:of the week )?(?:was|will be)\b",
                r"\bodd days?\b",
                r"\bleap year\b",
            ],

            # ===== Venn =====
            "Venn Diagram": [
                r"\bvenn diagram\b",
                r"\brepresents the relationship\b",
                r"\bbest represents\b.{0,40}\b(?:given|following) (?:classes|items)\b",
            ],

            # ===== Non-Verbal =====
            "Mirror Image": [
                r"\bmirror image\b",
            ],
            "Water Image": [
                r"\bwater image\b",
            ],
            "Paper Folding": [
                r"\bpaper folding\b",
                r"\bfolded and then\b",
            ],
            "Paper Cutting": [
                r"\bpaper cutting\b",
                r"\bunfolded\b.{0,40}\bappear\b",
            ],
            "Embedded Figures": [
                r"\bembedded figure\b",
                r"\bhidden figure\b",
            ],
            "Counting Figures": [
                r"\bcounting figures\b",
                r"\bhow many (?:triangles|squares|rectangles|circles)\b",
            ],
            "Figure Series": [
                r"\bfigure series\b",
                r"\bnext figure (?:in the )?series\b",
            ],
            "Figure Analogy": [
                r"\bfigure analogy\b",
            ],
            "Figure Classification": [
                r"\bfigure classification\b",
            ],
            "Figure Matrix": [
                r"\bfigure matrix\b",
                r"\bmatrix completion\b",
            ],
            "Pattern Completion": [
                r"\bpattern completion\b",
                r"\bcomplete the pattern\b",
            ],
            "Cube and Dice": [
                r"\bdice\b.{0,40}\b(?:opposite|adjacent) face\b",
                r"\bdifferent positions of (?:a |the )?(?:dice|cube)\b",
            ],
            "Cube Construction": [
                r"\bcube\b.{0,40}\b(?:painted|cut into)\b",
                r"\bsmall cubes\b",
            ],

            # ===== Math Operations =====
            "Mathematical Operations": [
                r"\bmathematical operations\b",
                r"\binterchanged\b.{0,30}\b(?:signs|symbols|operators)\b",
            ],
            "BODMAS Based Reasoning": [
                r"\bbodmas\b",
                r"\bafter applying bodmas\b",
            ],

            # ===== Misc =====
            "Decision Making": [
                r"\bdecision making\b",
                r"\beligible for\b.{0,80}\bcriteria\b",
            ],
            "Logical Sequence of Words": [
                r"\blogical (?:order|sequence) of (?:the )?words\b",
                r"\bmeaningful (?:order|sequence)\b",
            ],
            "Missing Character": [
                r"\bmissing (?:number|character|term)\b",
                r"\bwhat (?:should|will) (?:come|replace) (?:in (?:the )?place of )?the question mark\b",
            ],
        }

        # ===== Negative (non-reasoning) subject patterns =====
        self.negative_patterns = [
            # Science
            r"\bmass number\b", r"\bconcave mirror\b", r"\bgreenhouse effect\b",
            r"\bcarbon dioxide\b", r"\bbohr'?s model\b", r"\bamplitude of a wave\b",
            r"\bmagnetic field\b", r"\blysosomes\b", r"\belectrolytic refining\b",
            r"\bepithelial tissue\b", r"\bphotosynthesis\b", r"\bchemical reaction\b",
            r"\batomic number\b", r"\bvalency\b", r"\bperiodic table\b",
            r"\bnewton'?s law\b", r"\bohm'?s law\b",
            # Maths
            r"\bprofit and loss\b", r"\bsimple interest\b", r"\bcompound interest\b",
            r"\btime and work\b", r"\btime and distance\b", r"\bpipe and cistern\b",
            r"\bboat and stream\b", r"\bquadratic equation\b", r"\bprobability\b",
            r"\btrigonometry\b", r"\bperimeter\b", r"\barea of (?:a |the )?(?:triangle|square|rectangle|circle)\b",
            r"\bvolume of (?:a |the )?(?:cube|cylinder|sphere|cone)\b",
            r"\bmensuration\b", r"\bpercentage\b", r"\bratio and proportion\b",
            r"\bhcf\b", r"\blcm\b", r"\bsin\s*\(", r"\bcos\s*\(", r"\btan\s*\(",
            # English
            r"\breading comprehension\b", r"\bsynonym\b", r"\bantonym\b",
            r"\bactive voice\b", r"\bpassive voice\b", r"\bdirect speech\b",
            r"\bindirect speech\b", r"\bspot the error\b", r"\bfill in the blanks?\b",
            r"\bidiom\b", r"\bphrase\b", r"\bcloze test\b", r"\bpara[- ]?jumble\b",
            r"\bsentence rearrangement\b", r"\bone[- ]?word substitution\b",
            # GK / Current Affairs
            r"\bworld environment day\b", r"\breserve bank of india\b",
            r"\bparis agreement\b", r"\bappointed as\b", r"\bwho among the following\b",
            r"\bprime minister of\b", r"\bpresident of\b", r"\bcapital of\b",
            r"\bcurrency of\b", r"\bnational (?:bird|animal|flower|sport)\b",
            r"\bunesco\b", r"\bworld bank\b", r"\bimf\b", r"\bunited nations\b",
        ]

        # Weak structural signals (boost reasoning score, no topic assignment)
        self.weak_patterns = [
            r"\?.{0,20}\([abcd]\)",
            r"\b[a-z]{2,}[0-9]{2,}\b",
            r"[@#\$%&]",
            r"\b[A-Z]\s*[<>]\s*[A-Z]\b",
        ]

    def _compile(self):
        self.compiled_topic_patterns = {
            topic: [re.compile(p, re.I) for p in patterns]
            for topic, patterns in self.topic_patterns.items()
        }
        self.compiled_negative = [re.compile(p, re.I) for p in self.negative_patterns]
        self.compiled_weak = [re.compile(p, re.I) for p in self.weak_patterns]

    # ---------------------------------------------------------
    # Language filter — keep only English-dominant text
    # ---------------------------------------------------------
    @staticmethod
    def is_english_dominant(text, threshold=0.7):
        if not text:
            return False
        # Count basic-latin alphabet chars vs all alphabetic chars
        latin = sum(1 for c in text if "a" <= c.lower() <= "z")
        alpha = sum(1 for c in text if c.isalpha())
        if alpha == 0:
            return False
        return (latin / alpha) >= threshold

    # ---------------------------------------------------------
    # Classify
    # ---------------------------------------------------------
    def classify(self, text: str):
        original = text or ""
        text_l = re.sub(r"\s+", " ", original.lower())

        # Per-topic match counts
        topic_hits = {}
        strong_score = 0
        for topic, patterns in self.compiled_topic_patterns.items():
            hits = 0
            for rx in patterns:
                found = rx.findall(text_l)
                if found:
                    hits += len(found)
            if hits:
                topic_hits[topic] = hits
                strong_score += hits * 6

        # Weak structural
        weak_score = 0
        for rx in self.compiled_weak:
            weak_score += len(rx.findall(text_l)) * 2

        # Direction-word boost
        if len(re.findall(r"\b(left|right|north|south|east|west)\b", text_l)) >= 4:
            weak_score += 8

        # Negative
        negative_score = 0
        matched_negative = []
        for rx in self.compiled_negative:
            found = rx.findall(text_l)
            if found:
                negative_score += len(found) * 7
                matched_negative.append(rx.pattern)

        reasoning_score = strong_score + weak_score
        final_score = reasoning_score - negative_score

        # Decision: is this a reasoning question?
        is_reasoning = False
        if strong_score >= 18:
            is_reasoning = True
        elif final_score >= 12:
            is_reasoning = True

        # Pick best topic
        if topic_hits:
            best_topic = max(topic_hits.items(), key=lambda kv: kv[1])[0]
            regex_topic = self._ensure_canonical(best_topic)
        else:
            regex_topic = "Uncategorized"

        return {
            "is_reasoning": is_reasoning,
            "regex_topic": regex_topic,
            "reasoning_score": reasoning_score,
            "negative_score": negative_score,
            "final_score": final_score,
            "topic_hits": topic_hits,
            "matched_negative": matched_negative,
        }