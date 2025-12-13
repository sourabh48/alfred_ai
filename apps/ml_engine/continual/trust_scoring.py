class TrustScoring:

    def score(self, data_point):
        score = 1.0

        for key, value in data_point.items():
            if value in [None, "", 0]:
                score -= 0.1

        return max(score, 0.1)

trust_scoring = TrustScoring()
