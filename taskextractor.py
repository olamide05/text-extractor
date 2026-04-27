"""
╔══════════════════════════════════════════════════════════╗
║           SMART TASK EXTRACTOR — Hackathon Project       ║
║                                                          ║
║  What it does:                                           ║
║    Takes plain text → extracts Task, Deadline, Priority  ║
║                                                          ║
║  How to run:                                             ║
║    pip install dateparser                                ║
║    python task_extractor.py                              ║
╚══════════════════════════════════════════════════════════╝
"""

import re
import json
from datetime import datetime
import dateparser  


# ════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION — Easy to tweak live during demo!
# ════════════════════════════════════════════════════════════

# HOW TO MODIFY URGENCY THRESHOLDS:
#   Change the numbers below to adjust what counts as HIGH/MEDIUM/LOW.
#   Example: set HIGH to 1 if you only want same-day tasks as HIGH.
URGENCY_THRESHOLDS = {
    "HIGH":   2,   # ≤ 2 days away  → HIGH priority
    "MEDIUM": 5,   # ≤ 5 days away  → MEDIUM priority
    # anything beyond 5 days   → LOW priority
}

# HOW TO ADD MORE DEADLINE KEYWORDS:
#   Just add a new string to this list.
#   The extractor will look for these words to find the deadline part.
DEADLINE_KEYWORDS = [
    # Keep longer/more-specific phrases FIRST so they match before shorter ones.
    # e.g. "due date" must come before "due", "must be in" before "by"/"before"
    "must be in",
    "due date",
    "deadline",
    "due",
    "submit",
    "by",
    "before",
]


# ════════════════════════════════════════════════════════════
#  STEP 1 — Extract the Task Name
# ════════════════════════════════════════════════════════════
"""
TASK EXTRACTION MODULE

Goal:
Extract the "action item" or task name from natural language input.

How it works:
- Searches for known deadline keywords (e.g. "due", "deadline", "by")
- Captures text before those keywords as the task name
- Cleans filler words (e.g. "please", "submit", "the")

Why regex:
- Keeps system lightweight and deterministic
- Avoids dependency on large NLP models
- Works well for structured student/work tasks
"""
def extract_task(text):
    """
    Finds the task name by grabbing everything BEFORE a deadline keyword.

    Example:
        "Assignment 2 is due on April 30"          → "Assignment 2"
        "CS101 exam deadline is May 5"             → "CS101 exam"
        "Please submit the project report by May 3"→ "project report"

    Logic:
        - Loop through each keyword (e.g. "due", "deadline")
        - Use regex to grab text before that keyword
        - Strip filler words from the front (Please, The, etc.)
        - Also strip action verbs like "submit", "send", "turn in"
    """
    # Filler phrases to strip from the front of the task name
    FILLER_PATTERN = r"^(please|kindly|remember to|note that|the|a|an)\b\s*"
    # Action verbs that aren't part of the real task name
    ACTION_VERBS   = r"^(submit|send|turn in|complete|finish|upload|hand in)\s+(the\s+|a\s+|an\s+)?"

    for keyword in DEADLINE_KEYWORDS:
        pattern = rf"^(.+?)\s+(?:is\s+|are\s+)?{re.escape(keyword)}\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            task = match.group(1).strip()
            # Strip filler words (loop in case there are multiple layers)
            for _ in range(3):
                task = re.sub(FILLER_PATTERN, "", task, flags=re.IGNORECASE).strip()
                task = re.sub(ACTION_VERBS,   "", task, flags=re.IGNORECASE).strip()
            if task:  # skip if stripping left us with nothing
                return task

    # Fallback: if no keyword found, just return the first 4 words
    return " ".join(text.split()[:4])


# ════════════════════════════════════════════════════════════
#  STEP 2 — Extract the Deadline Date/Time
# ════════════════════════════════════════════════════════════
"""
DEADLINE EXTRACTION MODULE

Goal:
Identify and parse natural language date expressions.

How it works:
- Detects deadline keywords in text
- Extracts substring containing date information
- Uses 'dateparser' to convert text → datetime object

Supported inputs:
- "April 30th"
- "tomorrow"
- "next Friday"
- "May 3 at 5pm"

Design choice:
- Uses external NLP library (dateparser) instead of building custom date logic
- Improves accuracy while keeping code simple
"""
def extract_deadline(text):
    """
    Finds and parses the date/time from the text.

    Uses the `dateparser` library which understands:
        "April 30th"   → datetime(2026, 4, 30)
        "30th April"   → datetime(2026, 4, 30)
        "tomorrow"     → tomorrow's date
        "May 3 at 5pm" → datetime(2026, 5, 3, 17, 0)

    HOW TO ADD MORE DATE FORMATS:
        dateparser handles most formats automatically.
        If you need a custom format, you can add it to the
        DATEPARSER_SETTINGS below using 'DATE_ORDER' or 'FORMATS'.

    Strategy:
        1. Find a deadline keyword in the text
        2. Take everything after it as the "date string"
        3. Feed that into dateparser
        4. If no keyword found, try parsing the whole text
    """

    # Settings for dateparser
    DATEPARSER_SETTINGS = {
        "PREFER_DATES_FROM": "future",  # Assume upcoming dates, not past
        "RETURN_AS_TIMEZONE_AWARE": False,
        "RELATIVE_BASE": datetime.now(),  # Anchor "tomorrow", "next week" to now
    }

    # Try to isolate the date portion (text after the keyword)
    for keyword in DEADLINE_KEYWORDS:
        pattern = rf"{re.escape(keyword)}\s+(?:on\s+|by\s+|at\s+)?(.+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_string = match.group(1).strip()
            # Strip leading "is", "at", "the" which can confuse dateparser
            date_string = re.sub(r"^(is|are|the)\s+", "", date_string, flags=re.IGNORECASE)
            parsed_date = dateparser.parse(date_string, settings=DATEPARSER_SETTINGS)
            if parsed_date:
                return parsed_date  # Return as soon as we get a valid date

    # Fallback: try parsing the entire input text
    return dateparser.parse(text, settings=DATEPARSER_SETTINGS)


# ════════════════════════════════════════════════════════════
#  STEP 3 — Calculate Priority
# ════════════════════════════════════════════════════════════
"""
PRIORITY CALCULATION ENGINE

Goal:
Assign urgency level based on how close the deadline is.

Logic:
- OVERDUE → deadline already passed
- HIGH    → 0–2 days left
- MEDIUM  → 3–5 days left
- LOW     → 6+ days left

Design principle:
- Fully configurable via URGENCY_THRESHOLDS dictionary
- No hardcoded logic inside function
"""
def calculate_priority(deadline):
    """
    Compares the deadline to today's date and assigns a priority level.

    Rules (from URGENCY_THRESHOLDS config above):
        OVERDUE → deadline has already passed
        HIGH    → within 2 days
        MEDIUM  → within 5 days
        LOW     → more than 5 days away
        UNKNOWN → no deadline found

    HOW TO MODIFY:
        Change the numbers in URGENCY_THRESHOLDS at the top of the file.
    """
    if deadline is None:
        return "UNKNOWN"

    today = datetime.now().date()
    days_left = (deadline.date() - today).days

    if days_left < 0:
        return "OVERDUE"
    elif days_left <= URGENCY_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif days_left <= URGENCY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    else:
        return "LOW"


# ════════════════════════════════════════════════════════════
#  MAIN FUNCTION — Ties everything together
# ════════════════════════════════════════════════════════════
"""
PIPELINE ORCHESTRATION

Goal:
Combine all modules into a single structured output.

Flow:
1. Extract task name
2. Extract deadline
3. Calculate priority
4. Compute remaining days
5. Return structured JSON object

Output is designed for:
- CLI display
- API integration (future extension)
- Frontend dashboards
"""
def extract_task_info(text):
    """
    Master function: takes raw text, returns a clean result dictionary.

    Input:  "Assignment 2 is due on April 30th at 5pm"
    Output: { "task": "Assignment 2",
               "deadline": "2026-04-30 17:00",
               "priority": "HIGH",
               "days_left": 3 }
    """
    task     = extract_task(text)
    deadline = extract_deadline(text)
    priority = calculate_priority(deadline)

    # Calculate days remaining (for display)
    if deadline:
        days_left = (deadline.date() - datetime.now().date()).days
        days_left_str = f"{days_left} day(s)" if days_left >= 0 else "OVERDUE"
        deadline_str  = deadline.strftime("%Y-%m-%d %H:%M")
    else:
        days_left_str = "N/A"
        deadline_str  = "Not found"

    return {
        "task":      task,
        "deadline":  deadline_str,
        "priority":  priority,
        "days_left": days_left_str,
    }


# ════════════════════════════════════════════════════════════
#  CLI — Simple menu to demo the project
# ════════════════════════════════════════════════════════════

def print_result(result):
    """Pretty-prints the result to the console."""
    priority_icons = {
        "HIGH":    "🔴",
        "MEDIUM":  "🟡",
        "LOW":     "🟢",
        "OVERDUE": "⚫",
        "UNKNOWN": "⚪",
    }
    icon = priority_icons.get(result["priority"], "")

    print("\n  ┌─────────────────────────────────────┐")
    print(f"  │ 📋 Task:     {result['task']:<23} │")
    print(f"  │ 📅 Deadline: {result['deadline']:<23} │")
    print(f"  │ ⏳ Due in:   {result['days_left']:<23} │")
    print(f"  │ {icon} Priority: {result['priority']:<23} │")
    print("  └─────────────────────────────────────┘")


EXAMPLE_INPUTS = [
    "Assignment 2 is due on April 30th at 5pm",
    "Please submit the project report by May 3rd",
    "CS101 exam deadline is tomorrow at 9am",
    "The internship application must be in before June 15",
]


def run_cli():
    print("\n" + "═" * 50)
    print("       📋  SMART TASK EXTRACTOR  📋")
    print("═" * 50)

    while True:
        print("\nOptions:")
        print("  1 — Run example inputs")
        print("  2 — Enter your own text")
        print("  3 — Show JSON output")
        print("  q — Quit")
        print("\nChoice: ", end="")

        choice = input().strip().lower()

        if choice == "q":
            print("\nBye! 👋\n")
            break

        elif choice == "1":
            print("\n--- Running examples ---")
            for example in EXAMPLE_INPUTS:
                print(f"\nInput: \"{example}\"")
                result = extract_task_info(example)
                print_result(result)

        elif choice == "2":
            print("\nPaste your text and press Enter:")
            user_text = input().strip()
            if user_text:
                result = extract_task_info(user_text)
                print_result(result)
            else:
                print("  (no input given)")

        elif choice == "3":
            print("\n--- JSON Output for all examples ---")
            for example in EXAMPLE_INPUTS:
                print(f"\nInput: \"{example}\"")
                result = extract_task_info(example)
                print(json.dumps(result, indent=2))

        else:
            print("  Unknown option — try 1, 2, 3, or q")


# ════════════════════════════════════════════════════════════
#  Entry point
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_cli()