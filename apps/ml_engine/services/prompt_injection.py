"""Spot text written to hijack the AI (prompt injection) in public web text before a model reads it.

Patterns adapted from OpenJarvis `security/injection_scanner.py` (Apache-2.0, https://github.com/open-jarvis/OpenJarvis at
86f75ef7faeeb2b022a6621716d88c57ba105db0). Prompts still call all supplied text data, never instructions; this only keeps
the plainest attacks out of the model's view.
"""
import re

PATTERNS = tuple((name, re.compile(pattern, re.I)) for name, pattern in (
    ('prompt_override', r'\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|rules?)'),
    ('prompt_override', r'\bdisregard\s+(?:all\s+)?(?:previous|prior|your)\s+(?:instructions?|programming|rules?)'),
    ('identity_override', r'\byou\s+are\s+now\s+(?:a\s+)?(?:different|new|my)\b'),
    ('code_injection', r'\b(?:execute|run|eval)\s*\(\s*[\'"]'),
    ('shell_injection', r'(?:;|\||&&)\s*(?:rm|curl|wget|nc|ncat|bash|sh|python|perl)\s'),
    ('exfiltration', r'\b(?:send|post|upload|exfiltrate|transmit)\s+(?:(?:to|data|all|everything)\s+)*(?:to\s+)?(?:https?://|my\s+server)'),
    ('exfiltration', r'\bbase64\s+encode\s+(?:and\s+)?(?:send|include|append)'),
    ('jailbreak', r'\b(?:DAN|do\s+anything\s+now)\s+(?:mode|prompt|jailbreak)'),
    ('jailbreak', r'\bpretend\s+(?:you\s+)?(?:have\s+)?no\s+(?:restrictions?|limitations?|rules?|filters?)'),
    ('delimiter_injection', r'```(?:system|assistant)\b'),
    ('delimiter_injection', r'<\|(?:im_start|im_end|system|assistant)\|>'),
))


def finding(*texts):
    """The name of the first attack pattern found in any of the texts, else None."""
    for text in texts:
        if isinstance(text, str):
            for name, pattern in PATTERNS:
                if pattern.search(text):
                    return name
    return None
