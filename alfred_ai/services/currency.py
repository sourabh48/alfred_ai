"""How rupee amounts are written. Recognising one never converts it to another currency."""

# Use with re.IGNORECASE. The odd last form is the UTF-8 rupee sign misread as Windows-1252.
INR_TOKEN = r"(?:\b(?:INR|RUPEES?|RS[./-]*)|\u20b9|\u00e2\u201a\u00b9)"
# A number with no prefix is money only when a currency name or "/-" follows it.
INR_AMOUNT = rf"(?:{INR_TOKEN}\s*|(?=[0-9][0-9,]*(?:\.\d{{1,2}})?\s*(?:RUPEES?\b|INR\b|RS\b|/-)))([0-9,]+(?:\.\d{{1,2}})?)"
