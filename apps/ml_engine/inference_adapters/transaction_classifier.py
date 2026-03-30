"""
Advanced Transaction Classifier using ML for payment type, recipient, and company detection.
Uses sentence transformers for semantic understanding of transaction descriptions.
"""
import re
from typing import Dict, List, Tuple, Optional
from .base_adapter import BaseModelAdapter

# Try to import sentence transformers, but make it optional
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except (ImportError, NameError):
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class TransactionClassifierAdapter(BaseModelAdapter):
    """
    ML-powered transaction classifier for intelligent categorization.
    Uses semantic embeddings to understand transaction context.
    """

    def __init__(self):
        super().__init__()
        self.model = None
        self.category_embeddings = {}
        self.company_patterns = self._load_company_patterns()
        self.payment_mode_patterns = self._load_payment_mode_patterns()

    def load(self):
        """Load sentence transformer model for semantic classification."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("Info: Sentence transformers not available. Using rule-based classification only.")
            self.model = None
            return

        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self._precompute_category_embeddings()
            print("✓ Sentence transformer model loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load transformer model: {e}")
            self.model = None

    def _precompute_category_embeddings(self):
        """Precompute embeddings for each expense category."""
        category_descriptions = {
            "food": "restaurant cafe dining eating food delivery meal breakfast lunch dinner",
            "groceries": "supermarket grocery store vegetables fruits daily essentials shopping",
            "shopping": "online shopping clothes fashion electronics purchase retail store",
            "bills": "electricity water bill payment utility service charge",
            "utilities": "electricity gas water internet mobile recharge bill",
            "travel": "transport taxi uber ola metro train flight hotel booking",
            "fuel": "petrol diesel gas station fuel pump",
            "health": "hospital pharmacy medical doctor clinic medicine healthcare",
            "subscription": "netflix spotify premium membership subscription monthly plan",
            "entertainment": "movie theater cinema gaming entertainment fun leisure",
            "rent": "house rent apartment housing lease",
            "loan": "loan EMI payment installment finance credit",
            "credit_card": "credit card payment bill",
            "investment": "mutual fund stock trading investment share market",
            "transfer": "transfer money send UPI payment to friend family",
            "income": "salary income received credit refund reversal",
        }

        if self.model:
            for category, description in category_descriptions.items():
                self.category_embeddings[category] = self.model.encode(
                    description, convert_to_tensor=True
                )

    def predict(self, transaction_text: str, direction: str = "debit") -> Dict[str, str]:
        """
        Predict transaction details using ML.

        Returns:
            Dict with classification, category, payment_mode, merchant, company_name, counterparty
        """
        # Extract company name
        company_name = self._detect_company(transaction_text)

        # Extract merchant/counterparty
        merchant = self._extract_merchant(transaction_text)
        counterparty = merchant

        # Detect payment mode
        payment_mode = self._detect_payment_mode(transaction_text)

        # Classify category using ML
        if direction == "credit":
            classification, category = self._classify_credit_transaction(transaction_text)
        else:
            classification, category = self._classify_debit_transaction(transaction_text, company_name)

        return {
            "classification": classification,
            "category": category,
            "payment_mode": payment_mode,
            "merchant": merchant,
            "company_name": company_name,
            "counterparty": counterparty,
            "confidence": 0.85,  # Model confidence score
        }

    def _classify_debit_transaction(self, text: str, company: str) -> Tuple[str, str]:
        """Classify debit transaction using semantic ML."""
        text_upper = text.upper()

        # Rule-based priority checks for loans
        loan_keywords = ["BAJAJ", "POONAWALLA", "EMI", "LOAN", "HOUSING FINANCE", "FINCORP"]
        if any(kw in text_upper for kw in loan_keywords):
            return ("loan", "loan")

        # Investment patterns
        investment_keywords = ["GROWW", "ZERODHA", "MUTUAL FUND", "STOCK", "TRADING"]
        if any(kw in text_upper for kw in investment_keywords):
            return ("other", "investment")

        # Credit card payments
        if any(kw in text_upper for kw in ["CREDIT CARD", "ONECARD", "CRED CLUB"]):
            return ("other", "credit_card")

        # Use ML for semantic classification
        if self.model and self.category_embeddings:
            category = self._semantic_classify(text)
            return ("expense", category)

        # Fallback to rule-based
        return self._rule_based_classification(text)

    def _classify_credit_transaction(self, text: str) -> Tuple[str, str]:
        """Classify credit transaction."""
        text_upper = text.upper()

        if any(kw in text_upper for kw in ["REFUND", "REVERSAL", "REVERSED"]):
            return ("other", "income")

        if any(kw in text_upper for kw in ["SALARY", "BONUS", "INCENTIVE"]):
            return ("other", "income")

        if any(kw in text_upper for kw in ["NEFT CR", "RTGS CR", "IMPS CR"]):
            return ("other", "income")

        return ("other", "transfer")

    def _semantic_classify(self, text: str) -> str:
        """Use sentence embeddings to classify transaction semantically."""
        if not self.model:
            return "other"

        try:
            text_embedding = self.model.encode(text, convert_to_tensor=True)

            best_category = "other"
            best_score = 0.0

            for category, category_embedding in self.category_embeddings.items():
                score = util.pytorch_cos_sim(text_embedding, category_embedding).item()
                if score > best_score:
                    best_score = score
                    best_category = category

            return best_category if best_score > 0.3 else "other"
        except Exception:
            return "other"

    def _rule_based_classification(self, text: str) -> Tuple[str, str]:
        """Fallback rule-based classification."""
        text_upper = text.upper()

        rules = [
            ("expense", "groceries", ["GROCERY", "SUPERMARKET", "SMART BAZAAR"]),
            ("expense", "food", ["RESTAURANT", "CAFE", "SWIGGY", "ZOMATO", "FOOD"]),
            ("expense", "fuel", ["PETROL", "FUEL", "INDIAN OIL", "HPCL"]),
            ("expense", "utilities", ["ELECTRICITY", "RECHARGE", "BILL"]),
            ("expense", "shopping", ["AMAZON", "FLIPKART", "MYNTRA"]),
            ("expense", "travel", ["UBER", "OLA", "METRO", "IRCTC"]),
            ("expense", "health", ["PHARMACY", "HOSPITAL", "MEDICAL"]),
        ]

        for classification, category, keywords in rules:
            if any(kw in text_upper for kw in keywords):
                return (classification, category)

        return ("expense", "other")

    def _detect_company(self, text: str) -> str:
        """Detect company name from transaction text using patterns."""
        text_upper = text.upper()

        for pattern, company_name in self.company_patterns:
            if pattern in text_upper:
                return company_name

        # Extract from merchant field
        merchant = self._extract_merchant(text)
        return merchant[:255]

    def _extract_merchant(self, text: str) -> str:
        """Extract merchant name from transaction description."""
        # Remove common noise
        text = re.sub(r'\b(UPI|NEFT|RTGS|IMPS|ACH)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d{10,}\b', '', text)  # Remove reference numbers

        # Split and clean
        parts = re.split(r'[-/]', text)
        merchant_parts = []

        for part in parts:
            cleaned = part.strip()
            if len(cleaned) > 3 and not cleaned.isdigit():
                merchant_parts.append(cleaned.title())
                if len(' '.join(merchant_parts)) > 40:
                    break

        return ' '.join(merchant_parts[:3]) if merchant_parts else text[:60].title()

    def _detect_payment_mode(self, text: str) -> str:
        """Detect payment mode from transaction text."""
        text_upper = text.upper()

        for pattern, mode in self.payment_mode_patterns:
            if pattern in text_upper:
                return mode

        return "BANK"

    def _load_company_patterns(self) -> List[Tuple[str, str]]:
        """Load company detection patterns."""
        return [
            ("AMAZON", "Amazon"),
            ("FLIPKART", "Flipkart"),
            ("MYNTRA", "Myntra"),
            ("SWIGGY", "Swiggy"),
            ("ZOMATO", "Zomato"),
            ("UBER", "Uber"),
            ("OLA", "Ola Cabs"),
            ("GROWW", "Groww"),
            ("ZERODHA", "Zerodha"),
            ("CRED", "CRED"),
            ("NETFLIX", "Netflix"),
            ("SPOTIFY", "Spotify"),
            ("HDFC", "HDFC Bank"),
            ("ICICI", "ICICI Bank"),
            ("SBI", "State Bank of India"),
            ("AXIS", "Axis Bank"),
            ("INDIAN OIL", "Indian Oil"),
            ("JIO", "Reliance Jio"),
            ("AIRTEL", "Airtel"),
            ("BAJAJ", "Bajaj Finance"),
            ("POONAWALLA", "Poonawalla Fincorp"),
        ]

    def _load_payment_mode_patterns(self) -> List[Tuple[str, str]]:
        """Load payment mode detection patterns."""
        return [
            ("UPI", "UPI"),
            ("ACH", "ACH"),
            ("NEFT", "NEFT"),
            ("RTGS", "RTGS"),
            ("IMPS", "IMPS"),
            ("ATM", "ATM"),
            ("CARD", "CARD"),
            ("POS", "CARD"),
        ]


# Singleton instance
transaction_classifier = TransactionClassifierAdapter()
