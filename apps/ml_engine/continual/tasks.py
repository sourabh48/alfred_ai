from celery import shared_task
from apps.ml_engine.training.train_salary import train_salary_model
from apps.ml_engine.training.train_expense_lstm import train_expense_lstm
from apps.ml_engine.training.train_burnout_rf import train_burnout_model
from apps.ml_engine.training.train_risk_classifier import train_risk_classifier
from apps.ml_engine.training.train_relationship import train_relationship_model
from apps.ml_engine.training.train_rl_agent import train_rl_agent

@shared_task
def run_global_training_cycle():
    print("=== Running Alfred AI Global Training Cycle ===")

    train_salary_model()
    train_expense_lstm()
    train_burnout_model()
    train_risk_classifier()
    train_relationship_model()
    train_rl_agent()

    print("=== Global Training Complete ===")
