"""Requests the assistant refuses by policy, before any search.

Some questions cannot be answered from any page and must never be answered from one: a request for a
secret or a sign-in, for the names of teachers or children, or for a ranking of teachers. Retrieval
could find a page that merely mentions the words (a deploy page names a service account, a help page
says "teacher"), so these are caught first, by plain patterns. A refusal is not a leak and shows no
source.

The patterns refuse a request to SHOW something. An explanation of why something is hidden ("why
can't I see names") is a fair question and is answered from the help pages.
"""

from __future__ import annotations

import re

# Not preceded by a letter or digit, so ANTHROPIC_API_KEY is caught (the underscore is not a letter).
_NO_LETTER = r"(?<![A-Za-z0-9])"
SECRETS = re.compile(
    _NO_LETTER
    + r"(?:api[\s_-]?keys?|secret keys?|client secrets?|passwords?|passcodes?|credentials?|private keys?"
    r"|(?:access|bearer|auth(?:entication)?) tokens?|sign[\s-]?in (?:accounts?|keys?|details)"
    r"|login (?:details|accounts?)|\.env\b|environment file)(?![A-Za-z0-9])",
    re.I,
)
_ASKING_TO_SEE = r"(?:show|list|give|tell|display|print|reveal|share|send|provide|find|get|name|who are|what are|which)\b"
INDIVIDUALS = re.compile(
    r"(?:"
    + _ASKING_TO_SEE
    + r"[^.?!]{0,40}\b(?:names? of (?:the )?(?:teachers?|children|pupils?|students?|mentors?)"
    r"|(?:teachers?|children|pupils?|students?|mentors?)(?:'s|s')? names?|phone numbers?|home address(?:es)?|roll numbers?)"
    r"|\bwhich teachers?\b"
    r"|\bwho is (?:the )?(?:best|worst|weakest|strongest)\b"
    r"|\b(?:best|worst|weakest|top|bottom|lowest|highest)[\s-](?:performing |ranked |rated )?teachers?"
    r"|\bteachers? (?:ranks?|ranked|rankings?) (?:the )?(?:lowest|highest|worst|best)"
    r"|\brank(?:ing)? (?:of )?(?:the )?teachers?"
    r")",
    re.I,
)

REASON = {
    "secret": "I never show secrets, keys, sign-in details or accounts.",
    "individual": "I never show a named person's data or rank teachers: this app is built so nobody is judged by a number.",
}


def refusal(text: str) -> str | None:
    """The reason code ("secret" or "individual") if the question must be refused, else None."""
    if SECRETS.search(text):
        return "secret"
    if INDIVIDUALS.search(text):
        return "individual"
    return None
