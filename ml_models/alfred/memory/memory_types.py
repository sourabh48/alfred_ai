from enum import Enum

class MemoryType(Enum):
    SPENDING = "spending_event"
    BEHAVIOR = "behavior_state"
    GOAL = "goal_update"
    FAMILY = "family_event"
    CONVERSATION = "conversation"
    CAREER = "career_event"
    RISK = "risk_change"
