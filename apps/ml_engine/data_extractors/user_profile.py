from apps.users.models import User
import pandas as pd

def load_user_profiles():
    return pd.DataFrame.from_records(User.objects.all().values())
