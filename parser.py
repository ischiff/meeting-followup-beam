"""
Parses free-form meeting notes into structured action items.

Each returned action item is a dict:
    {
        "text": str,       # the cleaned-up action text
        "owner": str,      # best-guess owner, "" if none found
        "deadline": str,   # best-guess deadline, "" if none found
        "raw": str,        # original line, for reference/debugging
    }

This is a heuristic, regex-based parser -- not an LLM call -- so it's fast
and free to run, but it won't catch every phrasing. It's tuned for the kind
of shorthand people actually type in meeting notes:

    TODO: Sarah to send the proposal by Friday
    - [ ] Action: follow up with legal (owner: Mike, due 7/18)
    * AI: schedule kickoff call @jordan
    3. Action item - update the roadmap deck, EOD Monday
"""

import re

# Lines that look like an action item either start with one of these markers
# or contain one of these keywords anywhere in the line.
ACTION_MARKERS = re.compile(
    r"^\s*[-*\d.]*\s*\[?\s*\]?\s*(TODO|TO-DO|ACTION\s*ITEM|ACTION|AI|FOLLOW[- ]?UP)\b[:\-\s]*",
    re.IGNORECASE,
)
# Only treat a bare keyword as an action marker when it's followed by a colon
# (e.g. "Action item:"). Without the colon requirement, ordinary sentences
# like "that wasn't an action item" would be misclassified.
ACTION_KEYWORD_COLON = re.compile(
    r"\b(TODO|TO-DO|ACTION\s*ITEM|ACTION|AI|FOLLOW[- ]?UP)\s*:", re.IGNORECASE
)

# "owner: name", "(owner: name)", "assigned to name", "@name"
OWNER_PATTERNS = [
    re.compile(r"\bowner\s*[:\-]\s*([A-Za-z][\w'.\-]*(?:\s+[A-Za-z][\w'.\-]*)?)", re.IGNORECASE),
    re.compile(r"\bassigned\s*to\s*[:\-]?\s*([A-Za-z][\w'.\-]*(?:\s+[A-Za-z][\w'.\-]*)?)", re.IGNORECASE),
    re.compile(r"@([A-Za-z][\w'.\-]*)"),
    # "Sarah to send..." / "Mike will follow up..." at the start of the text
    re.compile(r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:to|will|is going to)\s+\w", re.MULTILINE),
]

# "due 7/18", "due: Friday", "by EOD Monday", "deadline: next week"
DEADLINE_PATTERNS = [
    re.compile(r"\b(?:due|deadline)\s*[:\-]?\s*([A-Za-z0-9/\-]+(?:\s+[A-Za-z0-9]+)?)", re.IGNORECASE),
    re.compile(
        r"\bby\s+((?:EOD|COB|EOW)?\s*(?:next\s+)?"
        r"(?:mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:rs(?:day)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?"
        r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}-\d{1,2}(?:-\d{2,4})?"
        r"|end of (?:day|week|month)|tomorrow|today)\.?)",
        re.IGNORECASE,
    ),
]


def _strip_wrapping_punctuation(text):
    return text.strip(" \t-*:;,.")


def _extract_owner(text):
    for pattern in OWNER_PATTERNS:
        match = pattern.search(text)
        if match:
            return _strip_wrapping_punctuation(match.group(1))
    return ""


def _extract_deadline(text):
    for pattern in DEADLINE_PATTERNS:
        match = pattern.search(text)
        if match:
            return _strip_wrapping_punctuation(match.group(1))
    return ""


def _clean_text(text):
    """Remove owner/deadline annotations from the display text so it reads
    cleanly, e.g. 'send the proposal' instead of
    'send the proposal by Friday (owner: Sarah)'.
    """
    cleaned = text

    # Strip trailing "(owner: ..., due ...)" style annotations
    cleaned = re.sub(r"\(?\s*owner\s*[:\-].*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\(?\s*due\s*[:\-].*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\(\s*\)$", "", cleaned).strip()
    # Strip @mentions once they've been captured as the owner
    cleaned = re.sub(r"@[A-Za-z][\w'.\-]*", "", cleaned).strip()
    cleaned = _strip_wrapping_punctuation(cleaned)

    return cleaned if cleaned else text.strip()


def extract_action_items(notes):
    """Parse meeting notes text and return a list of action item dicts."""
    if not notes:
        return []

    lines = notes.split("\n")
    items = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        has_marker = bool(ACTION_MARKERS.match(line))
        has_colon_keyword = bool(ACTION_KEYWORD_COLON.search(line))
        if not (has_marker or has_colon_keyword):
            continue

        # Strip the leading marker (e.g. "TODO:", "- [ ] Action:") before
        # extracting owner/deadline/text, so patterns anchored to the start
        # of the remaining text (like "Sarah to send...") still match.
        working_text = ACTION_MARKERS.sub("", line).strip()
        working_text = ACTION_KEYWORD_COLON.sub("", working_text).strip()

        owner = _extract_owner(working_text)
        deadline = _extract_deadline(working_text)
        text = _clean_text(working_text)

        items.append(
            {
                "text": text,
                "owner": owner,
                "deadline": deadline,
                "raw": raw_line,
            }
        )

    return items