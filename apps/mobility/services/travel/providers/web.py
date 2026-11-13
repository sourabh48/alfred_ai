"""The only text from a request that may leave the PC in a travel lookup: a short place name."""
import re


def public_place(value):
    """Only short geographic slots; never send messages, identifiers or profile blobs."""
    text = str(value or "").strip()
    if not 2 <= len(text) <= 100 or len(text.split()) > 7:
        return ""
    if not all(c.isalpha() or c in " .,'()-" for c in text):
        return ""
    if re.search(r"\b(?:email|salary|account|registration|password|my|wife|husband|family|phone|passport)\b", text, re.I):
        return ""
    return text
