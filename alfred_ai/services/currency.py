"""How rupee amounts are written. Recognising one never converts it to another currency."""

# Use with re.IGNORECASE. The odd sign is the UTF-8 rupee sign misread as Windows-1252.
INR_NAME = r"(?:INR\.?|RUPEES?|RS(?:\.?/-|\.)?)"
INR_SIGN = r"(?:\u20b9|\u00e2\u201a\u00b9|\u20a8)"
# After a label the name can touch the word before it, as in "Loan AmountRs.5,00,000".
INR_LABEL_TOKEN = rf"(?:{INR_NAME}|{INR_SIGN})"
INR_TOKEN = rf"(?:\b{INR_NAME}|{INR_SIGN})"
# A number with no prefix is money only when a currency name follows it. A bare "/-" also ends
# other currencies and references, so it counts only after a label.
INR_AMOUNT = (
    rf"(?:{INR_TOKEN}\s*|(?<![0-9A-Za-z,.$\u20ac\u00a3])(?=[0-9][0-9,]*(?:\.\d{{1,2}})?\s*(?:RUPEES?|INR|RS)\b))"
    r"([0-9][0-9,]*(?:\.\d{1,2})?)(?!\.?\d)"
)
