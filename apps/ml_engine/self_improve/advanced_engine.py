from .code_scanner import code_scanner
from .analyzer import code_analyzer
from .performance_profiler import performance_profiler
from .refactor_advisor import refactor_advisor
from .patch_generator import patch_generator
from .evolution_planner import evolution_planner


class SelfImproveEngine:

    def run_full_analysis(self):

        codebase = code_scanner.scan_project()
        results = []

        for file in codebase:
            content = file["content"]

            analysis = code_analyzer.analyze(content)
            performance = performance_profiler.analyze_ast(content)
            advice = refactor_advisor.recommend(content)
            patch = patch_generator.generate_patch(content, advice)

            results.append({
                "path": file["path"],
                "analysis": analysis,
                "performance_issues": performance,
                "refactor_suggestions": advice,
                "patch_proposal": patch
            })

        roadmap = evolution_planner.plan(
            [r["analysis"] for r in results]
        )

        return {
            "files_analyzed": len(codebase),
            "results": results,
            "evolution_plan": roadmap
        }


self_improve_engine = SelfImproveEngine()
