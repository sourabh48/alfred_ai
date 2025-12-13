class AnomalyDetector:

    def detect_expense_spike(self, history, threshold=2.0):
        if len(history) < 5:
            return False, 0

        mean = sum(history) / len(history)
        latest = history[-1]

        if latest > mean * threshold:
            return True, latest - mean

        return False, 0

    def detect_burnout_spike(self, stress_history):
        if len(stress_history) < 5:
            return False

        return stress_history[-1] > (sum(stress_history[:-1]) / len(stress_history[:-1])) * 1.5

anomaly_detector = AnomalyDetector()
