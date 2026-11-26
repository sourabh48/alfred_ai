"""Sections of the Bharatiya Nyaya Sanhita, 2023 for a legal question, so ALFRED answers a scenario like a legal assistant
(owner 2026-11-26, "Official BNS + IPC"). The text is the official NCRB compilation built by scripts/build_law_corpus.py;
it is public law, read on this PC, and may go to Gemini only alongside a question that is already allowed to go there."""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "data" / "bns_2023.json"
SECTION_CHARS = 9000  # whole offence sections, with the punishment clauses after the illustrations; only s. 2 is cut
LIMIT = 4

LEGAL = re.compile(
    r"\b(?:law|legal|illegal|lawyer|advocate|court|judge|police|fir|complaint|arrest\w*|bail|charge[ds]?|accused|offen[cs]e|"
    r"crime|criminal|punish\w*|penalty|jail|prison|imprison\w*|convict\w*|bns|ipc|sanhita|penal|section \d+|"
    r"murder\w*|kill\w*|theft|steal\w*|stole\w*|rob\w*|cheat\w*|fraud\w*|scam\w*|assault\w*|beat(?:en|s)?|hit|slap\w*|"
    r"stab\w*|rape\w*|molest\w*|harass\w*|stalk\w*|dowry|kidnap\w*|abduct\w*|threat\w*|blackmail\w*|extort\w*|defam\w*|"
    r"forg\w*|counterfeit\w*|trespass\w*|bribe\w*|embezzl\w*|misappropriat\w*|vandal\w*|sue[ds]?|reputation)\b", re.I)

# Everyday words for the terms the Sanhita uses. shortcut: a word list, not embeddings; upgrade if scenarios miss sections.
EVERYDAY = {
    "hit": "hurt assault criminal force", "beat": "hurt assault criminal force", "slap": "hurt assault criminal force",
    "punch": "hurt assault criminal force", "kick": "hurt assault criminal force", "attack": "hurt assault criminal force",
    "injur": "hurt grievous", "broke": "grievous hurt fracture", "fractur": "grievous hurt", "stab": "dangerous weapon grievous hurt",
    "knife": "dangerous weapon", "gun": "firearm dangerous weapon", "shot": "firearm", "acid": "acid grievous hurt",
    "kill": "murder culpable homicide death", "die": "death culpable homicide negligence", "dead": "death murder", "suicid": "abetment suicide",
    "steal": "theft movable property", "stole": "theft movable property", "stolen": "stolen property theft", "snatch": "snatching theft",
    "pickpocket": "theft", "rob": "robbery", "loot": "robbery dacoity", "scam": "cheating dishonestly deceiving",
    "fraud": "cheating dishonestly fraudulently", "cheat": "cheating deceiving", "dupe": "cheating deceiving",
    "threat": "criminal intimidation", "threaten": "criminal intimidation", "blackmail": "extortion criminal intimidation",
    "extort": "extortion", "molest": "assault outrage modesty woman", "grope": "sexual harassment modesty",
    "harass": "sexual harassment insult modesty", "stalk": "stalking", "rape": "rape", "husband": "cruelty husband relative",
    "wife": "cruelty husband", "dowry": "dowry death cruelty", "kidnap": "kidnapping", "abduct": "abduction",
    "insult": "insult defamation", "defam": "defamation", "slander": "defamation", "forg": "forgery", "fake": "forgery counterfeit",
    "trespass": "criminal trespass house-trespass", "break": "house-breaking", "burgl": "house-breaking theft",
    "damag": "mischief", "vandal": "mischief", "embezzl": "criminal breach trust misappropriation", "misappropriat": "misappropriation",
    "accident": "rash negligence death vehicle", "driv": "rash negligence vehicle", "rod": "dangerous weapon instrument",
    "stick": "dangerous weapon instrument", "promis": "cheating deceiving induce delivery", "vanish": "cheating dishonestly",
    "demand": "extortion", "reputation": "defamation harm reputation", "false": "defamation", "rumour": "defamation", "drunk": "rash negligent", "mob": "unlawful assembly rioting", "riot": "rioting",
    "bribe": "gratification bribery", "obscen": "obscene", "gambl": "gambling", "poison": "poison hurt",
}
_STOP = {"the", "and", "for", "with", "that", "this", "what", "who", "was", "were", "has", "have", "had", "his", "her", "him", "she",
         "they", "them", "can", "will", "shall", "any", "not", "but", "from", "into", "out", "under", "section", "sections", "person",
         "whoever", "also", "such", "may", "which", "there", "done", "does", "did", "law", "legal", "india", "indian"}


def _stem(word):
    return re.sub(r"(?:ing|ed|es|s)$", "", word) if len(word) > 4 else word


def _words(text):
    return [_stem(w) for w in re.findall(r"[a-z][a-z-]{2,}", text.lower()) if w not in _STOP]


@lru_cache(maxsize=1)
def corpus():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    sections = data["sections"]
    heads = [Counter(_words(item["heading"])) for item in sections]
    bodies = [Counter(_words(item["text"])) for item in sections]
    seen = Counter(word for head, body in zip(heads, bodies) for word in set(head) | set(body))
    idf = {word: math.log(len(sections) / count) for word, count in seen.items()}
    return data, heads, bodies, idf


def is_legal(question):
    return isinstance(question, str) and bool(LEGAL.search(question))


def _direct(question, sections):
    """"section 103", "BNS 103" or "IPC 302" named in the question."""
    found = []
    for code, number in re.findall(r"\b(ipc|bns|section|s\.)\s*(\d{1,3}[A-Z]?)\b", question, re.I):
        if code.lower() == "ipc":
            found += [item for item in sections if re.search(rf"(?:^|\s){re.escape(number)}\.", item["ipc"])]
        elif number.isdigit() and 1 <= int(number) <= len(sections):
            found.append(sections[int(number) - 1])
    return found


def sections(question, limit=LIMIT):
    """The sections that best fit the question, as answer sources (refs law-1…); empty for a question about something else."""
    if not is_legal(question):
        return []
    data, heads, bodies, idf = corpus()
    items = data["sections"]
    words = _words(question)
    words += [_stem(term) for word in words for key, terms in EVERYDAY.items() if word.startswith(key) for term in terms.split()]
    wanted = Counter(words)
    scores = [sum(idf.get(word, 0) * (3 * min(head[word], 1) + min(body[word], 3)) for word in wanted)
              for head, body in zip(heads, bodies)]
    ranked = [items[i] for i in sorted(range(len(items)), key=lambda i: -scores[i]) if scores[i] >= 4][:limit]
    picked = []
    for item in _direct(question, items) or ranked:  # a named section is the answer by itself
        if item not in picked: picked.append(item)
    return [{"ref": f"law-{number}", "classification": "statute_section", "url": data["source"],
             "data": {"act": "Bharatiya Nyaya Sanhita, 2023", "section": item["section"], "heading": item["heading"],
                      "chapter": item["chapter"], "text": item["text"][:SECTION_CHARS], "ipc": item["ipc"] or "not listed in the source table",
                      "in_force_from": data["in_force_from"]}}
            for number, item in enumerate(picked[:limit + 2], 1)]


INSTRUCTIONS = (
    'Sources classified statute_section (refs such as [law-1]) are sections of the Bharatiya Nyaya Sanhita, 2023 (BNS), in force '
    'from 1 July 2024. It replaced the Indian Penal Code, 1860 (IPC), which still governs offences committed before that date; '
    'each source names the old IPC section. When they are supplied, answer like a legal assistant, in full, in labelled sections in '
    'this order: Answer (which offence or offences the facts most likely make out, in plain words), Applicable sections (each BNS '
    'section with its ref, its old IPC section, and what it requires), How they apply (each requirement against the facts given, '
    'saying which facts are missing or unclear), Likely outcome and punishment (only as the section text states it; the real result '
    'depends on the evidence and the court), What would change it (facts or defences that matter), Next steps (practical steps such '
    'as a police complaint or FIR, keeping evidence, a lawyer or free legal aid) and Note (general information, not legal advice). '
    'If web results are also supplied, add What was searched and What was found after Answer. Name only the sections supplied '
    '(their section and ipc fields): never another section number, even one you remember, since the whole answer is hidden if it '
    'names one. Quote terms of punishment and amounts exactly as the supplied sources state them, with their refs. Say plainly '
    'when no supplied section fits the facts. ')
