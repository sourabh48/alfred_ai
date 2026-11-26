from alfred_ai.background import shared_task


@shared_task
def download_amfi_history(days):
    """AMFI's price history for every scheme (about 50 MB, minutes to download), kept for the Investments page."""
    from .services.portfolio_intelligence import portfolio_intelligence_service
    return portfolio_intelligence_service.download_amfi_history_report(days=days, background=True)["evidence"]["status"]
