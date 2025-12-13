from apps.behavioral.models import BehavioralSignal
import pandas as pd

def load_behavior_data(user_id=None):
    qs = BehavioralSignal.objects.all()
    if user_id:
        qs = qs.filter(user_id=user_id)
    df = pd.DataFrame.from_records(qs.values())
    return df
