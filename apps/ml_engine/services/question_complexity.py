"""How hard a question is, from 0 (trivial) to 1 (very complex), so a simple one can go to the fast local model.

Adapted from OpenJarvis `learning/routing/complexity.py` (Apache-2.0, https://github.com/open-jarvis/OpenJarvis at
86f75ef7faeeb2b022a6621716d88c57ba105db0): same signals and weights; ALFRED adds money words to the arithmetic signal.
"""
import re

_CODE = re.compile(r"```|`[^`]+`|\bdef\s|\bclass\s|\bimport\s|\bfunction\s|\bconst\s|\bvar\s|\blet\s|"
                   r"\bif\s*\(|->|=>|\{\s*\}|\bfor\s+\w+\s+in\s|#include|System\.out", re.I)
# Arithmetic the model would have to do itself; recorded figures it only copies do not count.
_MATH = re.compile(r"\bsolve\b|\bintegral\b|\bequation\b|\bproof\b|\bderivative\b|\bmatrix\b|\btheorem\b|\bcalculate\b|"
                   r"\bcompute\b|\bsigma\b|\bsum\b|\blimit\b|\bprobability\b|\bwhat if\b|\bif i (?:pay|invest|save|prepay)\b|"
                   r"\bper ?cent(?:age)?\b|%|\binterest on\b|\bproject(?:ion|ed)?\b|\bforecast\b", re.I)
_REASONING = re.compile(r"\bexplain\b|\banalyze\b|\banalyse\b|\bcompare\b|\bwhy\b|\bstep[- ]by[- ]step\b|\breason\b|\bthink\b|"
                        r"\bpros\s+and\s+cons\b|\btrade-?\s*offs?\b|\bevaluate\b|\bshould i\b", re.I)
_MULTI_STEP = re.compile(r"\bstep\s*\d|\b(?:and\s+also|additionally|furthermore)\b|\b\d+\.\s", re.I)
_CREATIVE = re.compile(r"\bcreate\b|\bdesign\b|\bdraft\b|\bcompose\b", re.I)
_PAIRS = ((r"\bthen\b", r"\bthen\b"), (r"\bfirst\b", r"\bnext\b"))
_CREATIVE_PAIRS = ((r"\bwrite\b", r"\b(?:essay|story|article|report|poem|letter|email)\b"),
                   (r"\bgenerate\b", r"\b(?:code|script|program)\b"))


def _ordered(text, first, second):
    opening = re.search(first, text, re.I)
    return opening is not None and re.search(second, text[opening.end():], re.I) is not None


def score(query):
    """(score, signals) for a question; the score is a weighted sum of independent signals."""
    query = query if isinstance(query, str) else ''
    length = len(query)
    length_score = 0.0 if length < 20 else 0.3 if length < 100 else 0.6 if length < 300 else 0.8 if length < 800 else 1.0
    has_code, has_math = bool(_CODE.search(query)), bool(_MATH.search(query))
    domain = 1.0 if has_code and has_math else 0.8 if has_math else 0.7 if has_code else 0.0
    has_reasoning = bool(_REASONING.search(query))
    multi_step = bool(_MULTI_STEP.search(query)) or any(_ordered(query, a, b) for a, b in _PAIRS)
    reasoning = 1.0 if has_reasoning and multi_step else 0.8 if multi_step else 0.6 if has_reasoning else 0.0
    parts = query.count('?') + len(re.findall(r'^\s*(?:\d+[.)]|[-*])\s', query, re.M))
    multi = 0.0 if parts <= 1 else 0.5 if parts <= 3 else 1.0
    creative = 0.7 if _CREATIVE.search(query) or any(_ordered(line, a, b) for line in query.split('\n') for a, b in _CREATIVE_PAIRS) else 0.0
    total = min(1.0, 0.20 * length_score + 0.25 * domain + 0.25 * reasoning + 0.15 * multi + 0.15 * creative)
    return total, dict(has_code=has_code, has_math=has_math, has_reasoning=has_reasoning, multi_step=multi_step, parts=parts)


def is_simple(query):
    """Trivial or simple tier (below 0.30, OpenJarvis's boundary) with no arithmetic, code or reasoning to do."""
    total, signals = score(query)
    return total < 0.30 and not (signals['has_math'] or signals['has_code'] or signals['has_reasoning'] or signals['multi_step'])
