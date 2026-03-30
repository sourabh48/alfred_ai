"""
Voice Assistant Service
Natural language interaction with Alfred using voice commands
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.utils import timezone

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    from gtts import gTTS
    import pygame
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class VoiceAssistantService:
    """
    AI-powered voice assistant for hands-free financial management.
    Supports voice commands for expenses, queries, and reports.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.nlp = None

        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except:
                self.nlp = None

        # Command patterns
        self.intent_patterns = {
            'add_expense': [
                r'(?:add|record|log)\s+(?:an?\s+)?expense',
                r'(?:i\s+)?spent\s+(?:rupees?\s+)?(\d+)',
                r'(?:paid|pay)\s+(?:rupees?\s+)?(\d+)',
            ],
            'get_balance': [
                r'(?:what(?:\'?s)?|show|tell)\s+(?:my|the)?\s*(?:current\s+)?balance',
                r'how\s+much\s+(?:money\s+)?(?:do\s+i\s+)?have',
            ],
            'get_expenses': [
                r'(?:what|show|tell)\s+(?:were\s+)?my\s+expenses',
                r'how\s+much\s+(?:did\s+i|have\s+i)\s+spen[dt]',
            ],
            'get_budget': [
                r'(?:what|show|tell)\s+(?:is\s+)?my\s+budget',
                r'how\s+much\s+can\s+i\s+spend',
            ],
            'get_loans': [
                r'(?:what|show|tell)\s+(?:are\s+)?my\s+loans',
                r'how\s+much\s+(?:do\s+i\s+)?owe',
            ],
            'get_investments': [
                r'(?:what|show|tell)\s+(?:are\s+)?my\s+investments',
                r'(?:what|show|tell)\s+(?:is\s+)?my\s+portfolio',
            ],
            'financial_health': [
                r'(?:what|show|tell)\s+(?:is\s+)?my\s+financial\s+health',
                r'how\s+am\s+i\s+doing\s+financially',
            ],
            'help': [
                r'help',
                r'what\s+can\s+you\s+do',
                r'list\s+commands',
            ]
        }

        # Entity extraction patterns
        self.entity_patterns = {
            'amount': r'(?:rupees?\s+|rs\.?\s*|inr\s+)?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            'category': r'(?:for|on|category)\s+(food|shopping|travel|utilities|entertainment|health|education)',
            'date': r'(?:on|dated?)\s+(today|yesterday|last\s+(?:week|month)|\d{1,2}(?:st|nd|rd|th)?\s+\w+)',
            'time_period': r'(today|yesterday|this\s+week|this\s+month|last\s+week|last\s+month)',
        }

    def listen(self, timeout: int = 5) -> Optional[str]:
        """
        Listen for voice input and convert to text.

        Args:
            timeout: Seconds to listen for (default 5)

        Returns:
            Recognized text or None
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return None

        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                print("Listening...")
                audio = self.recognizer.listen(source, timeout=timeout)

                # Recognize speech using Google Speech Recognition
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")

                return text.lower()

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None

    def speak(self, text: str, lang: str = 'en') -> bool:
        """
        Convert text to speech and play it.

        Args:
            text: Text to speak
            lang: Language code (default 'en')

        Returns:
            True if successful, False otherwise
        """
        if not TTS_AVAILABLE:
            # Fallback to printing
            print(f"Alfred: {text}")
            return False

        try:
            # Generate speech
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save("response.mp3")

            # Play audio
            pygame.mixer.init()
            pygame.mixer.music.load("response.mp3")
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            return True

        except Exception as e:
            print(f"TTS error: {e}")
            print(f"Alfred: {text}")
            return False

    def process_command(self, text: str, user) -> Dict:
        """
        Process natural language command and execute action.

        Args:
            text: Command text
            user: Django user object

        Returns:
            Dict with response and action taken
        """
        # Detect intent
        intent = self._detect_intent(text)

        # Extract entities
        entities = self._extract_entities(text)

        # Execute based on intent
        if intent == 'add_expense':
            return self._handle_add_expense(user, entities)

        elif intent == 'get_balance':
            return self._handle_get_balance(user)

        elif intent == 'get_expenses':
            return self._handle_get_expenses(user, entities)

        elif intent == 'get_budget':
            return self._handle_get_budget(user)

        elif intent == 'get_loans':
            return self._handle_get_loans(user)

        elif intent == 'get_investments':
            return self._handle_get_investments(user)

        elif intent == 'financial_health':
            return self._handle_financial_health(user)

        elif intent == 'help':
            return self._handle_help()

        else:
            return {
                'success': False,
                'intent': 'unknown',
                'response': "I didn't understand that. Try saying 'help' to see what I can do."
            }

    def _detect_intent(self, text: str) -> str:
        """Detect user intent from text."""
        text_lower = text.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent

        return 'unknown'

    def _extract_entities(self, text: str) -> Dict:
        """Extract entities (amount, category, date, etc.) from text."""
        entities = {}

        # Extract amount
        amount_match = re.search(self.entity_patterns['amount'], text, re.IGNORECASE)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            entities['amount'] = float(amount_str)

        # Extract category
        category_match = re.search(self.entity_patterns['category'], text, re.IGNORECASE)
        if category_match:
            entities['category'] = category_match.group(1).lower()

        # Extract time period
        period_match = re.search(self.entity_patterns['time_period'], text, re.IGNORECASE)
        if period_match:
            entities['time_period'] = period_match.group(1).lower()

        # Use NLP for better extraction if available
        if self.nlp:
            doc = self.nlp(text)

            # Extract monetary amounts
            for ent in doc.ents:
                if ent.label_ == 'MONEY':
                    money_text = ent.text.replace(',', '').replace('₹', '').replace('rupees', '').replace('rs', '')
                    try:
                        entities['amount'] = float(money_text.strip())
                    except:
                        pass

                # Extract dates
                if ent.label_ == 'DATE':
                    entities['date_text'] = ent.text

        return entities

    def _handle_add_expense(self, user, entities: Dict) -> Dict:
        """Handle adding an expense via voice."""
        from apps.expenses.models import Expense

        # Validate amount
        if 'amount' not in entities:
            return {
                'success': False,
                'intent': 'add_expense',
                'response': "I couldn't understand the amount. Please specify how much you spent."
            }

        amount = entities['amount']
        category = entities.get('category', 'other')
        description = f"Voice expense: {category}"

        # Create expense
        expense = Expense.objects.create(
            user=user,
            amount=amount,
            category=category,
            description=description,
            date=timezone.now().date()
        )

        return {
            'success': True,
            'intent': 'add_expense',
            'expense_id': expense.id,
            'response': f"Recorded an expense of {amount} rupees in {category} category."
        }

    def _handle_get_balance(self, user) -> Dict:
        """Get account balance."""
        from apps.expenses.models import BankAccount

        accounts = BankAccount.objects.filter(user=user, is_active=True)
        total_balance = sum(acc.current_balance for acc in accounts)

        if accounts.count() == 1:
            response = f"Your current balance is {total_balance:,.0f} rupees."
        else:
            response = f"Your total balance across {accounts.count()} accounts is {total_balance:,.0f} rupees."

        return {
            'success': True,
            'intent': 'get_balance',
            'total_balance': total_balance,
            'account_count': accounts.count(),
            'response': response
        }

    def _handle_get_expenses(self, user, entities: Dict) -> Dict:
        """Get expense summary for a period."""
        from apps.expenses.models import Expense

        # Determine time period
        period = entities.get('time_period', 'this month')

        if period == 'today':
            start_date = timezone.now().date()
            period_name = 'today'
        elif period == 'yesterday':
            start_date = timezone.now().date() - timedelta(days=1)
            period_name = 'yesterday'
        elif period == 'this week':
            start_date = timezone.now().date() - timedelta(days=7)
            period_name = 'this week'
        elif period == 'last week':
            start_date = timezone.now().date() - timedelta(days=14)
            period_name = 'last week'
        elif period == 'this month':
            start_date = timezone.now().date().replace(day=1)
            period_name = 'this month'
        elif period == 'last month':
            first_day_this_month = timezone.now().date().replace(day=1)
            start_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
            period_name = 'last month'
        else:
            start_date = timezone.now().date().replace(day=1)
            period_name = 'this month'

        # Get expenses
        expenses = Expense.objects.filter(user=user, transaction_date__gte=start_date)
        total = sum(exp.amount for exp in expenses)
        count = expenses.count()

        response = f"You spent {total:,.0f} rupees {period_name} across {count} transactions."

        return {
            'success': True,
            'intent': 'get_expenses',
            'period': period_name,
            'total': total,
            'count': count,
            'response': response
        }

    def _handle_get_budget(self, user) -> Dict:
        """Get budget information and spending status."""
        from apps.budgets.services.budget_intelligence import budget_intelligence_service

        affordability = budget_intelligence_service.calculate_daily_affordability(user)

        safe_spend = affordability.get('safe_daily_spend', 0)
        today_spent = affordability.get('today_spending', 0)
        status = affordability.get('status', 'UNKNOWN')

        if status == 'GOOD':
            response = f"You can safely spend {safe_spend:,.0f} rupees today. You've spent {today_spent:,.0f} so far."
        elif status == 'WARNING':
            response = f"Warning: You should spend no more than {safe_spend:,.0f} rupees today. You've already spent {today_spent:,.0f}."
        else:
            response = f"You're over budget today. Recommended daily spend is {safe_spend:,.0f} rupees, but you've spent {today_spent:,.0f}."

        return {
            'success': True,
            'intent': 'get_budget',
            'safe_daily_spend': safe_spend,
            'today_spending': today_spent,
            'status': status,
            'response': response
        }

    def _handle_get_loans(self, user) -> Dict:
        """Get loan summary."""
        from apps.loans.models import Loan

        active_loans = Loan.objects.filter(user=user, is_active=True)
        total_outstanding = sum(loan.remaining_balance for loan in active_loans)
        total_emi = sum(loan.emi for loan in active_loans)

        if active_loans.count() == 0:
            response = "You don't have any active loans. Great job!"
        elif active_loans.count() == 1:
            response = f"You have 1 active loan with {total_outstanding:,.0f} rupees outstanding. Your monthly EMI is {total_emi:,.0f} rupees."
        else:
            response = f"You have {active_loans.count()} active loans with total outstanding of {total_outstanding:,.0f} rupees. Your total monthly EMI is {total_emi:,.0f} rupees."

        return {
            'success': True,
            'intent': 'get_loans',
            'active_loans': active_loans.count(),
            'total_outstanding': total_outstanding,
            'total_emi': total_emi,
            'response': response
        }

    def _handle_get_investments(self, user) -> Dict:
        """Get investment portfolio summary."""
        from apps.investments.models import Investment

        investments = Investment.objects.filter(user=user)
        total_value = sum(inv.current_value for inv in investments)
        count = investments.count()

        if count == 0:
            response = "You don't have any investments tracked yet. Consider starting your investment journey!"
        else:
            response = f"Your investment portfolio has {count} holdings worth {total_value:,.0f} rupees in total."

        return {
            'success': True,
            'intent': 'get_investments',
            'investment_count': count,
            'total_value': total_value,
            'response': response
        }

    def _handle_financial_health(self, user) -> Dict:
        """Get financial health score and summary."""
        from apps.ml_engine.services.alfred_financial_brain import alfred_brain

        try:
            snapshot = alfred_brain.get_comprehensive_financial_snapshot(user)

            score = snapshot['health_score']['score']
            assessment = snapshot['health_score']['assessment']

            response = f"Your financial health score is {score} out of 100, which is {assessment}. "

            # Add top priority action
            if snapshot['priority_actions']:
                top_action = snapshot['priority_actions'][0]
                response += f"Top recommendation: {top_action}"

            return {
                'success': True,
                'intent': 'financial_health',
                'score': score,
                'assessment': assessment,
                'response': response
            }

        except Exception as e:
            return {
                'success': False,
                'intent': 'financial_health',
                'response': "I couldn't calculate your financial health right now. Please try again later."
            }

    def _handle_help(self) -> Dict:
        """Provide list of available commands."""
        commands = [
            "Add expense: 'I spent 500 rupees on food'",
            "Check balance: 'What is my balance?'",
            "View expenses: 'Show my expenses this month'",
            "Check budget: 'How much can I spend today?'",
            "View loans: 'What are my loans?'",
            "View investments: 'Show my portfolio'",
            "Financial health: 'How am I doing financially?'"
        ]

        response = "I can help you with: " + "; ".join(commands)

        return {
            'success': True,
            'intent': 'help',
            'commands': commands,
            'response': response
        }

    def conversation_mode(self, user, max_turns: int = 10) -> List[Dict]:
        """
        Enter continuous conversation mode.

        Args:
            user: Django user object
            max_turns: Maximum conversation turns (default 10)

        Returns:
            List of conversation exchanges
        """
        conversation = []

        self.speak("Hello! I'm Alfred, your financial assistant. How can I help you today?")

        for turn in range(max_turns):
            # Listen for command
            command_text = self.listen(timeout=10)

            if not command_text:
                self.speak("I didn't hear anything. Please try again.")
                continue

            # Check for exit command
            if any(word in command_text for word in ['exit', 'quit', 'bye', 'goodbye']):
                self.speak("Goodbye! Have a great day!")
                break

            # Process command
            result = self.process_command(command_text, user)

            # Store exchange
            conversation.append({
                'turn': turn + 1,
                'user_input': command_text,
                'intent': result.get('intent'),
                'response': result.get('response'),
                'success': result.get('success')
            })

            # Speak response
            self.speak(result['response'])

        return conversation


# Singleton instance
voice_assistant = VoiceAssistantService()
