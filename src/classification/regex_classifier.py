import re

from classification.topics_loader import (
    load_canonical_topics,
    ensure_canonical,
)


class RegexClassifier:
    """
    Cheap, broad keyword-based classifier.

    Role:
      1) is_reasoning -> rough yes/no.
         Computed as: reasoning_token_hits >= 1
         AND negative_token_hits == 0
         (the LLM gets the final say in the pipeline).
      2) regex_topic -> best-scoring canonical topic
         by token-overlap count. Falls back to
         "Uncategorized" when nothing matches.

    NOTE: This is INTENTIONALLY loose. Treat it as a
    hint column. The LLM column is the source of truth.
    """

    # =====================================================
    # Per-topic KEYWORD bags (lowercase tokens / bigrams).
    # We match each as a whole-word regex. No example
    # phrases, no positional logic.
    # =====================================================
    TOPIC_KEYWORDS: dict[str, list[str]] = {

        # ----- Seating -----
        "Linear Seating Arrangement": [
            "row", "linear", "left end", "right end",
            "straight line", "sitting", "seated",
        ],
        "Linear Seating Arrangement (Two Rows Facing Each Other)": [
            "two rows", "parallel rows",
            "facing each other", "facing north",
            "facing south",
        ],
        "Circular Seating Arrangement": [
            "circular", "round table",
            "facing the centre", "facing the center",
            "facing outside", "facing outward",
            "facing inward", "around a circular",
        ],
        "Square Seating Arrangement": [
            "square table", "square shaped",
            "corners of the square",
            "sides of the square",
        ],
        "Rectangular Seating Arrangement": [
            "rectangular table", "rectangular shaped",
        ],
        "Triangular Seating Arrangement": [
            "triangular table",
            "corners of the triangle",
        ],
        "Hexagonal Seating Arrangement": [
            "hexagonal", "hexagon table",
        ],
        "Uncertain Number Seating Arrangement": [
            "uncertain number", "may be",
            "not certain how many",
        ],

        # ----- Puzzles -----
        "Floor Puzzle": [
            "floor", "floors", "storey", "story",
            "ground floor", "topmost floor",
            "lives on",
        ],
        "Floor with Flat Puzzle": [
            "flat", "flats", "apartment",
        ],
        "Box Puzzle (Vertical Stack)": [
            "box", "boxes", "stacked",
            "kept above", "kept below",
            "immediately above", "immediately below",
        ],
        "Box Puzzle (Horizontal Arrangement)": [
            "shelf", "shelves", "rack",
        ],
        "Month Based Puzzle": [
            "january", "february", "march", "april",
            "may", "june", "july", "august",
            "september", "october", "november",
            "december", "different months",
        ],
        "Day Based Puzzle": [
            "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday",
            "sunday", "different days",
            "days of the week",
        ],
        "Date Based Puzzle": [
            "different dates", "1st", "15th", "30th",
        ],
        "Year/Age Puzzle": [
            "different ages", "different years",
            "born in", "eldest", "youngest",
            "elder", "younger",
        ],
        "Time Slot / Scheduling Puzzle": [
            "time slot", "scheduled at",
            "meeting", "appointment", "lecture",
            "shift",
        ],
        "Categorization Puzzle (Single Variable)": [
            "likes a different", "different colour",
            "different color", "different fruit",
            "different city", "different car",
            "different subject",
        ],
        "Categorization Puzzle (Double Variable)": [
            "two variables", "two parameters",
        ],
        "Categorization Puzzle (Triple Variable)": [
            "three variables", "three parameters",
        ],
        "Comparison Puzzle": [
            "taller than", "shorter than",
            "heavier than", "lighter than",
            "older than", "younger than",
        ],
        "Designation / Hierarchy Puzzle": [
            "designation", "rank", "senior",
            "junior", "hierarchy", "ceo",
            "manager", "director",
        ],

        # ----- Blood Relations -----
        "Blood Relations (General)": [
            "father", "mother", "brother", "sister",
            "son", "daughter", "husband", "wife",
            "uncle", "aunt", "cousin", "nephew",
            "niece", "grandfather", "grandmother",
            "related to",
        ],
        "Blood Relations (Pointing / Photograph)": [
            "pointing", "photograph", "picture",
        ],
        "Blood Relations (Family Tree)": [
            "family tree", "generations",
        ],
        "Coded Blood Relations": [
            "p + q", "p - q", "a @ b", "a # b",
            "means brother", "means sister",
            "means father", "means mother",
            "means son", "means daughter",
        ],
        "Generation Based Blood Relations": [
            "generation", "two generations",
            "three generations",
        ],

        # ----- Direction -----
        "Direction Sense": [
            "north", "south", "east", "west",
            "north-east", "north-west",
            "south-east", "south-west",
            "facing", "turns left", "turns right",
            "walks", "drives",
        ],
        "Direction Sense (Shortest Distance)": [
            "shortest distance", "how far",
            "straight line distance",
        ],
        "Direction Sense (Final Direction)": [
            "final direction", "facing now",
            "now facing",
        ],
        "Coded Direction Sense": [
            "if north means", "if east means",
            "directions are coded",
        ],
        "Clock Based Direction": [
            "12 o'clock direction",
            "3 o'clock direction",
            "6 o'clock direction",
            "9 o'clock direction",
        ],

        # ----- Coding-Decoding -----
        "Letter Coding (Substitution)": [
            "code language", "coded as",
            "is written as", "is coded",
            "decoded as",
        ],
        "Letter Coding (Shift / Skip)": [
            "shift", "skip", "next letter",
            "previous letter",
        ],
        "Number Coding": [
            "numeric code", "number code",
            "coded number",
        ],
        "Symbol Coding": [
            "symbol code", "@", "#", "$", "%", "&",
            "*", "coded using symbols",
        ],
        "Mixed Letter-Number Coding": [
            "letter cluster", "letter-cluster",
            "alphanumeric code",
            "letter number cluster",
        ],
        "Coded Equations / Symbol Operations": [
            "if + means", "if - means",
            "if × means", "if ÷ means",
            "interchanged",
        ],
        "Coded Word Logic": [
            "word code", "coded word",
        ],
        "Fictitious Language Coding": [
            "in a certain language",
            "in some language",
        ],
        "Conditional Coding": [
            "following conditions",
            "apply the conditions",
        ],

        # ----- Series -----
        "Number Series (Missing Term)": [
            "number series", "missing number",
            "missing term", "next number",
            "what comes next",
        ],
        "Number Series (Wrong Term)": [
            "wrong number", "wrong term",
            "does not fit",
        ],
        "Letter Series": [
            "letter series", "alphabet series",
        ],
        "Alphanumeric Series": [
            "alphanumeric", "alpha numeric",
            "alpha-numeric",
        ],
        "Mixed Series": [
            "mixed series",
        ],
        "Continuous Pattern Series": [
            "continuous pattern",
        ],
        "Symbol Series": [
            "symbol series",
        ],

        # ----- Analogy -----
        "Word Analogy": [
            "is to", "as", "analogous", "analogy",
        ],
        "Number Analogy": [
            "number analogy",
        ],
        "Letter Analogy": [
            "letter analogy",
        ],
        "Mixed Analogy": [
            "mixed analogy",
        ],
        "Choose Analogous Pair": [
            "analogous pair", "similar pair",
        ],
        "Figure Analogy": [
            "figure analogy",
        ],

        # ----- Classification -----
        "Word Classification": [
            "odd one out", "does not belong",
            "different from the others",
            "different from the rest",
        ],
        "Number Classification": [
            "odd number out",
        ],
        "Letter Classification": [
            "odd letter out",
        ],
        "Mixed Classification": [
            "mixed classification",
        ],
        "Figure Classification": [
            "figure classification",
        ],

        # ----- Alphabet & Word -----
        "Alphabet Test (Position)": [
            "alphabet position", "from the left",
            "from the right", "english alphabet",
        ],
        "Alphabet Test (After Operation)": [
            "after rearranging", "after reversing",
        ],
        "Alphabet Reversal": [
            "reversed alphabet", "alphabet reversed",
        ],
        "Dictionary Order": [
            "dictionary order", "alphabetical order",
        ],
        "Word Formation (From Given Letters)": [
            "meaningful word",
            "form a meaningful",
        ],
        "Word Formation (Using Word Letters)": [
            "using the letters of the word",
        ],
        "Letter Pair / Cluster": [
            "letter pair", "letter group",
        ],
        "Jumbled Letters": [
            "jumbled", "rearrange the letters",
        ],

        # ----- Logical -----
        "Syllogism (Two Statement)": [
            "statements", "conclusions",
            "all are", "no is", "some are",
            "syllogism",
        ],
        "Syllogism (Three Statement)": [
            "three statements",
        ],
        "Syllogism (Reverse / Possibility)": [
            "possibility", "reverse syllogism",
        ],
        "Statement and Conclusion": [
            "statement and conclusion",
            "conclusion follows",
        ],
        "Statement and Assumption": [
            "statement and assumption",
            "assumption is implicit",
        ],
        "Statement and Argument": [
            "statement and argument",
            "strong argument", "weak argument",
        ],
        "Statement and Course of Action": [
            "course of action",
        ],
        "Statement and Inference": [
            "statement and inference",
            "inference",
        ],
        "Cause and Effect": [
            "cause and effect",
            "independent causes",
        ],
        "Assertion and Reason": [
            "assertion", "reason",
            "assertion and reason",
        ],
        "Critical Reasoning": [
            "critical reasoning",
            "weaken the argument",
            "strengthen the argument",
        ],
        "Logical Deduction": [
            "logical deduction",
        ],
        "Strong and Weak Arguments": [
            "strong and weak",
        ],

        # ----- Data Sufficiency -----
        "Data Sufficiency (Two Statement)": [
            "data sufficiency",
            "statement i alone",
            "statement ii alone",
            "data is sufficient",
        ],
        "Data Sufficiency (Three Statement)": [
            "statement iii alone",
            "three statements",
        ],

        # ----- Ranking -----
        "Ranking (Single Row)": [
            "rank", "position from top",
            "position from bottom",
            "position from left",
            "position from right",
        ],
        "Ranking (Age / Height / Weight)": [
            "tallest", "shortest",
            "heaviest", "lightest",
            "oldest", "youngest",
        ],
        "Ranking (Marks / Score)": [
            "highest marks", "lowest marks",
            "scored",
        ],
        "Order and Sequence": [
            "ascending order",
            "descending order",
        ],

        # ----- Input-Output -----
        "Machine Input-Output (Shifting)": [
            "machine input", "step i",
            "step ii", "step iii",
        ],
        "Machine Input-Output (Arrangement)": [
            "arrangement step",
            "rearrangement",
        ],
        "Machine Input-Output (Mixed Operations)": [
            "mixed operations input",
        ],

        # ----- Inequality -----
        "Mathematical Inequality (Direct)": [
            "inequality", "greater than",
            "less than", "≥", "≤", ">", "<",
        ],
        "Coded Inequality": [
            "coded inequality",
            "not greater than",
            "not less than",
        ],
        "Filler Inequality": [
            "filler inequality",
        ],

        # ----- Clock & Calendar -----
        "Clock (Angle)": [
            "angle between",
            "hour hand", "minute hand",
        ],
        "Clock (Mirror / Water Image)": [
            "mirror image of the clock",
            "water image of the clock",
        ],
        "Clock (Faulty / Gaining / Losing)": [
            "gains", "loses",
            "faulty clock",
        ],
        "Calendar (Day of the Week)": [
            "day of the week",
            "what day",
        ],
        "Calendar (Odd Days)": [
            "odd days",
        ],
        "Calendar (Leap Year)": [
            "leap year",
        ],

        # ----- Venn -----
        "Venn Diagram (Classification)": [
            "venn diagram",
            "best represents",
        ],
        "Venn Diagram (Data Based)": [
            "venn diagram data",
        ],
        "Venn Diagram (Set Theory)": [
            "set theory",
        ],

        # ----- Non-Verbal -----
        "Mirror Image": [
            "mirror image",
        ],
        "Water Image": [
            "water image",
        ],
        "Paper Folding": [
            "paper folding", "folded paper",
        ],
        "Paper Cutting": [
            "paper cutting", "unfolded",
        ],
        "Embedded Figures": [
            "embedded figure",
        ],
        "Hidden Figures": [
            "hidden figure",
        ],
        "Counting Figures": [
            "counting figures",
            "how many triangles",
            "how many squares",
            "how many rectangles",
        ],
        "Figure Series": [
            "figure series",
            "next figure",
        ],
        "Figure Analogy (Non-Verbal)": [
            "figure analogy",
        ],
        "Figure Classification (Non-Verbal)": [
            "figure classification",
        ],
        "Figure Matrix": [
            "figure matrix",
            "matrix completion",
        ],
        "Pattern Completion": [
            "pattern completion",
            "complete the pattern",
        ],
        "Image Formation": [
            "image formation",
        ],
        "Image Analysis": [
            "image analysis",
        ],
        "Dot Situation": [
            "dot situation",
        ],
        "Rule Detection": [
            "rule detection",
        ],
        "Cube and Dice (Standard)": [
            "dice", "opposite face",
            "adjacent face",
        ],
        "Cube and Dice (Open / Net)": [
            "open dice", "net of dice",
            "net of cube",
        ],
        "Cube Construction (Painted Cube)": [
            "painted cube",
            "painted on all sides",
        ],
        "Cube Construction (Cut Cube)": [
            "cut into smaller cubes",
            "small cubes",
        ],

        # ----- Math Operations -----
        "Mathematical Operations (Symbol Substitution)": [
            "symbol substitution",
            "if + stands for",
        ],
        "Mathematical Operations (Sign Interchange)": [
            "sign interchange",
            "signs interchanged",
        ],
        "BODMAS Based Reasoning": [
            "bodmas",
        ],
        "Number Puzzle / Matrix": [
            "number puzzle",
            "number matrix",
        ],

        # ----- Decision -----
        "Decision Making": [
            "decision making",
        ],
        "Eligibility Test": [
            "eligibility", "eligible for",
            "selection criteria",
        ],
        "Course of Action": [
            "course of action",
        ],

        # ----- Misc -----
        "Logical Sequence of Words": [
            "logical sequence of words",
            "meaningful sequence",
            "logical order of words",
        ],
        "Missing Character / Number": [
            "missing character",
            "missing number",
            "question mark",
        ],
        "Analytical Reasoning": [
            "analytical reasoning",
        ],
        "Verbal Classification (Verbal Aptitude)": [
            "verbal classification",
        ],
        "Verbal Analogy": [
            "verbal analogy",
        ],
        "Distance, Time and Direction": [
            "distance time direction",
        ],
        "Calendar and Time": [
            "calendar and time",
        ],
        "Theme Detection": [
            "theme detection",
        ],
    }

    # =====================================================
    # NEGATIVE keyword bag — drops non-reasoning subjects.
    # Pure tokens. No phrasing.
    # =====================================================
    NEGATIVE_KEYWORDS: list[str] = [

        # Maths / Quant
        "profit and loss", "simple interest",
        "compound interest", "time and work",
        "time and distance", "pipe and cistern",
        "boat and stream", "quadratic equation",
        "probability", "trigonometry",
        "perimeter", "mensuration",
        "percentage", "ratio and proportion",
        "hcf", "lcm", "average",
        "discount", "partnership",
        "sin", "cos", "tan", "cot",
        "logarithm",
        "cost price", "selling price",
        "marked price", "volume of",
        "area of", "curved surface",
        "total surface", "diameter",
        "radius", "circumference",
        "square root", "cube root",
        "two trains", "downstream",
        "upstream", "efficiency",
        "work done", "profit percent",
        "loss percent", "c.p.", "s.p.",
        "m.p.", "cube of", "square of",
        "arithmetic progression",
        "geometric progression",

        # Science
        "photosynthesis", "mitochondria",
        "ribosome", "chromosome", "valency",
        "atomic number", "atomic mass",
        "periodic table", "newton's law",
        "ohm's law", "magnetic field",
        "electric current", "voltage",
        "molecule", "compound",
        "acid", "base", "salt",
        "greenhouse", "ecosystem",
        "mitosis", "meiosis", "cell division",
        "tissue", "organ", "organism",
        "gravity", "friction", "velocity",
        "acceleration", "force", "energy",
        "wavelength", "frequency",
        "electric circuit", "resistance",
        "chemical reaction", "oxidation",
        "reduction", "catalyst",

        # English
        "synonym", "antonym",
        "active voice", "passive voice",
        "direct speech", "indirect speech",
        "spot the error",
        "fill in the blank",
        "fill in the blanks",
        "idiom", "phrase",
        "cloze test", "para jumble",
        "parajumble", "one word substitution",
        "reading comprehension",
        "sentence improvement",
        "sentence rearrangement",
        "comprehension", "unseen passage",
        "title", "main idea",
        "author's view", "author's tone",
        "plural", "singular", "noun",
        "verb", "adjective", "adverb",
        "preposition", "conjunction",
        "tenses", "parts of speech",
        "spell", "spelling", "homophone",
        "homonym", "one word for",
        "error detection",
        "para completion",
        "sentence completion",

        # GK / Current Affairs
        "prime minister", "president of",
        "capital of", "currency of",
        "national bird", "national animal",
        "national flower", "national sport",
        "world bank", "imf", "unesco",
        "united nations", "world environment day",
        "reserve bank of india",
        "paris agreement",
        "olympics",
        "constitution of india",
        "fundamental rights",
        "directive principles",
        "largest", "smallest", "longest",
        "highest", "tallest", "shortest",
        "first woman", "first man",
        "invented by", "discovered by",
        "headquarters", "located in",
        "famous for", "who is known as",
        "who was known as", "fully fledged",
        "amendment", "article", "schedule",
        "fundamental duty", "chief minister",
        "governor of", "chief justice",
        "speaker of", "world's largest",
        "india's largest", "oldest",
        "newest", "first in india",
        "first in world", "father of",
        "mother of", "founder of",
        "head quarter", "established in",
        "formed in", "abolished",
        "bill", "act", "judgment",
        "science and technology",
        "award", "nobel prize",
        "padma", "gallantry",
        "population", "census",
        "gdp", "per capita income",
        "five year plan", "niti aayog",
        "planning commission",
        "state bird", "state animal",
        "state flower", "state tree",
        "tiger reserve", "national park",
        "wildlife sanctuary", "river",
        "mountain range", "peak",
        "largest producer", "leading producer",
        "export", "import",
        "treaty", "summit",
        "organization",

        # Computer Awareness
        "cpu", "ram", "rom", "hard drive",
        "operating system", "microsoft word",
        "excel", "powerpoint", "internet",
        "protocol", "tcp/ip", "url", "dns",
        "database", "sql",
        "keyboard shortcut", "ms office",
        "computer memory", "input device",
        "output device", "storage device",
        "software", "hardware", "malware",
        "virus", "antivirus", "firewall",
        "motherboard", "processor",
        "hard disk", "ssd", "usb",
        "html", "http", "https", "ftp",
        "lan", "wan", "man", "vpn",
        "algorithm", "programming",
        "binary", "decimal", "hexadecimal",
        "bits", "bytes",
        "generation of computers",
        "super computer", "mainframe",
        "microprocessor",
    ]

    # Match each keyword as a whole-word/bigram regex.
    # Punctuation in the keyword (e.g. "newton's law")
    # is escaped automatically.

    def __init__(self):

        self.canonical_topics = (
            load_canonical_topics()
        )

        self.compiled_topics: (
            dict[str, list[re.Pattern]]
        ) = {}

        for topic, kws in (
            self.TOPIC_KEYWORDS.items()
        ):

            self.compiled_topics[topic] = [
                self._compile_kw(k)
                for k in kws
            ]

        self.compiled_negatives = [
            self._compile_kw(k)
            for k in self.NEGATIVE_KEYWORDS
        ]

    @staticmethod
    def _compile_kw(
        kw: str,
    ) -> re.Pattern:

        # Whole-word match where possible.
        # For tokens with non-word chars
        # (e.g. ">=", "@") we drop the \b.

        escaped = re.escape(kw.lower())

        starts_word = bool(
            re.match(r"\w", kw)
        )

        ends_word = bool(
            re.search(r"\w$", kw)
        )

        pattern = escaped

        if starts_word:
            pattern = r"\b" + pattern

        if ends_word:
            pattern = pattern + r"\b"

        return re.compile(
            pattern, re.IGNORECASE
        )

    def classify(
        self,
        text: str,
    ) -> dict:

        if not text:
            return self._empty_result()

        normalized = re.sub(
            r"\s+",
            " ",
            text.lower(),
        )

        # ---- topic scoring (pure count) ----
        topic_hits: dict[str, int] = {}

        for topic, regexes in (
            self.compiled_topics.items()
        ):

            hits = 0

            for rx in regexes:
                hits += len(
                    rx.findall(normalized)
                )

            if hits > 0:
                topic_hits[topic] = hits

        # ---- negative scoring ----
        negative_hits = 0

        for rx in self.compiled_negatives:
            negative_hits += len(
                rx.findall(normalized)
            )

        # ---- decisions ----
        reasoning_hits = sum(
            topic_hits.values()
        )

        is_reasoning_hint = (
            reasoning_hits >= 1
            and negative_hits == 0
        )

        if topic_hits:

            best_topic = max(
                topic_hits.items(),
                key=lambda kv: kv[1],
            )[0]

            regex_topic = ensure_canonical(
                best_topic,
                self.canonical_topics,
            )

        else:
            regex_topic = "Uncategorized"

        if negative_hits > 0:
            # Strong signal it's NOT reasoning
            regex_topic = "Uncategorized"

        return {
            "is_reasoning_hint": (
                is_reasoning_hint
            ),
            "regex_topic": regex_topic,
            "reasoning_hits": reasoning_hits,
            "negative_hits": negative_hits,
            "topic_hits": topic_hits,
        }

    @staticmethod
    def _empty_result() -> dict:

        return {
            "is_reasoning_hint": False,
            "regex_topic": "Uncategorized",
            "reasoning_hits": 0,
            "negative_hits": 0,
            "topic_hits": {},
        }