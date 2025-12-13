class EvolutionPlanner:

    def plan(self, analysis_results):
        roadmap = []

        for item in analysis_results:
            if "performance" in item.lower():
                roadmap.append("Optimize loops & switch to numpy operations.")
            if "security" in item.lower():
                roadmap.append("Review external API calls + input validation.")
            if "architecture" in item.lower():
                roadmap.append("Modularize ML engine into microservices.")

        roadmap.append("Enhance memory engine with more embeddings.")
        roadmap.append("Periodically retrain models using real-world data.")

        return roadmap


evolution_planner = EvolutionPlanner()
