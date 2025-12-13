import numpy as np

class BehavioralSignature:

    def generate_signature(self, expense_history, stress_history):
        sig = {
            "avg_expense": float(np.mean(expense_history)) if len(expense_history) else 0,
            "expense_volatility": float(np.std(expense_history)) if len(expense_history) else 0,
            "stress_avg": float(np.mean(stress_history)) if len(stress_history) else 0,
            "spike_factor": float(np.max(expense_history) - np.min(expense_history)) if len(expense_history) else 0
        }
        return sig

    def compare_signatures(self, old_sig, new_sig):
        diffs = {}
        for key in old_sig:
            diffs[key] = float(new_sig[key] - old_sig[key])
        return diffs

behavior_signature = BehavioralSignature()
