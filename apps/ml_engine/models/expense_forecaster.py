"""
LSTM-based Expense Forecasting Model
Advanced deep learning for accurate expense prediction
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth, TruncWeek

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ExpenseLSTM(nn.Module):
    """
    LSTM Neural Network for expense forecasting.

    Architecture:
    - Input Layer: Expense features (amount, category, day of week, etc.)
    - LSTM Layers: 2 layers with 64 hidden units each
    - Dropout: 0.2 for regularization
    - Output Layer: Single value (predicted expense)
    """

    def __init__(self, input_size: int = 10, hidden_size: int = 64, num_layers: int = 2,
                 output_size: int = 1, dropout: float = 0.2):
        super(ExpenseLSTM, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Fully connected layers
        self.fc1 = nn.Linear(hidden_size, 32)
        self.fc2 = nn.Linear(32, output_size)

        # Activation and regularization
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # Initialize hidden and cell states
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        # LSTM forward pass
        out, _ = self.lstm(x, (h0, c0))

        # Take the last output
        out = out[:, -1, :]

        # Fully connected layers
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)

        return out


class ExpenseDataset(Dataset):
    """PyTorch Dataset for expense time series data."""

    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class ExpenseForecasterService:
    """
    Advanced LSTM-based expense forecasting service.
    Provides short-term (1-7 days) and long-term (1-12 months) predictions.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.category_encodings = {}
        self.is_trained = False

        if PYTORCH_AVAILABLE and SKLEARN_AVAILABLE:
            self.scaler = MinMaxScaler()
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = None

    def prepare_training_data(self, user, lookback_days: int = 90) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from user's expense history.

        Args:
            user: Django user object
            lookback_days: Days of history to use

        Returns:
            Tuple of (sequences, targets) for training
        """
        from apps.expenses.models import Expense

        # Fetch expense history
        start_date = timezone.now().date() - timedelta(days=lookback_days)
        expenses = Expense.objects.filter(
            user=user,
            transaction_date__gte=start_date
        ).order_by('transaction_date').values(
            'transaction_date', 'amount', 'category', 'description'
        )

        if not expenses:
            return np.array([]), np.array([])

        # Convert to DataFrame
        df = pd.DataFrame(expenses)

        # Feature engineering
        df['day_of_week'] = pd.to_datetime(df['transaction_date']).dt.dayofweek
        df['day_of_month'] = pd.to_datetime(df['transaction_date']).dt.day
        df['month'] = pd.to_datetime(df['transaction_date']).dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_month_start'] = (df['day_of_month'] <= 5).astype(int)
        df['is_month_end'] = (df['day_of_month'] >= 25).astype(int)

        # Encode categories
        categories = df['category'].unique()
        self.category_encodings = {cat: idx for idx, cat in enumerate(categories)}
        df['category_encoded'] = df['category'].map(self.category_encodings)

        # Aggregate by date (sum daily expenses)
        daily_expenses = df.groupby('transaction_date').agg({
            'amount': 'sum',
            'day_of_week': 'first',
            'day_of_month': 'first',
            'month': 'first',
            'is_weekend': 'first',
            'is_month_start': 'first',
            'is_month_end': 'first'
        }).reset_index()

        # Create sequences (use 7-day windows to predict next day)
        sequence_length = 7
        sequences = []
        targets = []

        for i in range(len(daily_expenses) - sequence_length):
            # Features: amount, day_of_week, is_weekend, etc.
            seq = daily_expenses.iloc[i:i+sequence_length][[
                'amount', 'day_of_week', 'day_of_month', 'month',
                'is_weekend', 'is_month_start', 'is_month_end'
            ]].values

            # Target: next day's expense
            target = daily_expenses.iloc[i+sequence_length]['amount']

            sequences.append(seq)
            targets.append(target)

        return np.array(sequences), np.array(targets)

    def train_model(self, user, epochs: int = 50, batch_size: int = 32,
                    learning_rate: float = 0.001) -> Dict:
        """
        Train LSTM model on user's expense history.

        Args:
            user: Django user object
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate for optimizer

        Returns:
            Dict with training results
        """
        if not PYTORCH_AVAILABLE or not SKLEARN_AVAILABLE:
            return {
                'success': False,
                'error': 'PyTorch or scikit-learn not available'
            }

        # Prepare data
        sequences, targets = self.prepare_training_data(user)

        if len(sequences) < 20:
            return {
                'success': False,
                'error': 'Insufficient data for training (need at least 20 days)'
            }

        # Normalize data
        seq_shape = sequences.shape
        sequences_flat = sequences.reshape(-1, seq_shape[-1])
        sequences_scaled = self.scaler.fit_transform(sequences_flat)
        sequences = sequences_scaled.reshape(seq_shape)

        # Normalize targets separately
        targets = targets.reshape(-1, 1)
        target_scaler = MinMaxScaler()
        targets_scaled = target_scaler.fit_transform(targets)

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            sequences, targets_scaled, test_size=0.2, random_state=42
        )

        # Create datasets and dataloaders
        train_dataset = ExpenseDataset(X_train, y_train)
        test_dataset = ExpenseDataset(X_test, y_test)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size)

        # Initialize model
        input_size = sequences.shape[2]
        self.model = ExpenseLSTM(input_size=input_size).to(self.device)

        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)

        # Training loop
        train_losses = []
        test_losses = []

        for epoch in range(epochs):
            # Training
            self.model.train()
            epoch_loss = 0
            for sequences_batch, targets_batch in train_loader:
                sequences_batch = sequences_batch.to(self.device)
                targets_batch = targets_batch.to(self.device)

                # Forward pass
                outputs = self.model(sequences_batch)
                loss = criterion(outputs, targets_batch)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

            avg_train_loss = epoch_loss / len(train_loader)
            train_losses.append(avg_train_loss)

            # Validation
            self.model.eval()
            test_loss = 0
            with torch.no_grad():
                for sequences_batch, targets_batch in test_loader:
                    sequences_batch = sequences_batch.to(self.device)
                    targets_batch = targets_batch.to(self.device)

                    outputs = self.model(sequences_batch)
                    loss = criterion(outputs, targets_batch)
                    test_loss += loss.item()

            avg_test_loss = test_loss / len(test_loader)
            test_losses.append(avg_test_loss)

        self.is_trained = True
        self.target_scaler = target_scaler

        return {
            'success': True,
            'epochs': epochs,
            'final_train_loss': train_losses[-1],
            'final_test_loss': test_losses[-1],
            'samples_trained': len(X_train),
            'samples_tested': len(X_test),
            'model_size': sum(p.numel() for p in self.model.parameters())
        }

    def predict_next_days(self, user, days_ahead: int = 7) -> Dict:
        """
        Predict expenses for next N days.

        Args:
            user: Django user object
            days_ahead: Number of days to predict

        Returns:
            Dict with daily predictions
        """
        if not self.is_trained:
            # Train model if not already trained
            train_result = self.train_model(user)
            if not train_result['success']:
                return self._fallback_prediction(user, days_ahead)

        from apps.expenses.models import Expense

        # Get last 7 days of data for prediction
        last_7_days = []
        for i in range(7, 0, -1):
            date = timezone.now().date() - timedelta(days=i)
            day_expense = Expense.objects.filter(
                user=user,
                date=date
            ).aggregate(total=Sum('amount'))['total'] or 0

            day_of_week = date.weekday()
            day_of_month = date.day
            month = date.month
            is_weekend = 1 if day_of_week in [5, 6] else 0
            is_month_start = 1 if day_of_month <= 5 else 0
            is_month_end = 1 if day_of_month >= 25 else 0

            last_7_days.append([
                day_expense, day_of_week, day_of_month, month,
                is_weekend, is_month_start, is_month_end
            ])

        # Make predictions
        predictions = []
        current_sequence = np.array(last_7_days).reshape(1, 7, -1)

        for day in range(days_ahead):
            # Normalize
            seq_scaled = self.scaler.transform(current_sequence.reshape(-1, 7))
            seq_scaled = seq_scaled.reshape(1, 7, -1)

            # Predict
            with torch.no_grad():
                self.model.eval()
                seq_tensor = torch.FloatTensor(seq_scaled).to(self.device)
                prediction = self.model(seq_tensor).cpu().numpy()

            # Denormalize
            predicted_amount = self.target_scaler.inverse_transform(prediction)[0][0]

            # Get prediction date
            pred_date = timezone.now().date() + timedelta(days=day+1)

            predictions.append({
                'date': pred_date.isoformat(),
                'predicted_amount': round(float(predicted_amount), 2),
                'day_of_week': pred_date.strftime('%A'),
                'confidence': 'High' if day < 3 else 'Medium' if day < 5 else 'Low'
            })

            # Update sequence for next prediction
            day_of_week = pred_date.weekday()
            new_row = np.array([[
                predicted_amount, day_of_week, pred_date.day, pred_date.month,
                1 if day_of_week in [5, 6] else 0,
                1 if pred_date.day <= 5 else 0,
                1 if pred_date.day >= 25 else 0
            ]])

            current_sequence = np.vstack([current_sequence[0][1:], new_row]).reshape(1, 7, -1)

        total_predicted = sum(p['predicted_amount'] for p in predictions)

        return {
            'success': True,
            'predictions': predictions,
            'total_predicted': round(total_predicted, 2),
            'average_daily': round(total_predicted / days_ahead, 2),
            'model': 'LSTM'
        }

    def predict_monthly_expenses(self, user, months_ahead: int = 6) -> Dict:
        """
        Predict monthly expenses for next N months.

        Args:
            user: Django user object
            months_ahead: Number of months to predict

        Returns:
            Dict with monthly predictions
        """
        from apps.expenses.models import Expense

        # Get historical monthly data
        monthly_data = []
        for i in range(12, 0, -1):
            start_date = (timezone.now().date().replace(day=1) -
                         timedelta(days=30*i))
            end_date = (start_date + timedelta(days=30))

            monthly_total = Expense.objects.filter(
                user=user,
                transaction_date__gte=start_date,
                transaction_date__lt=end_date
            ).aggregate(total=Sum('amount'))['total'] or 0

            monthly_data.append(monthly_total)

        if not monthly_data:
            return self._fallback_monthly_prediction(user, months_ahead)

        # Simple trend analysis
        recent_avg = np.mean(monthly_data[-3:]) if len(monthly_data) >= 3 else np.mean(monthly_data)
        trend = (monthly_data[-1] - monthly_data[0]) / len(monthly_data) if len(monthly_data) > 1 else 0

        predictions = []
        for month in range(1, months_ahead + 1):
            pred_date = timezone.now().date() + timedelta(days=30*month)
            predicted_amount = recent_avg + (trend * month)

            predictions.append({
                'month': pred_date.strftime('%b %Y'),
                'predicted_amount': round(max(0, predicted_amount), 2),
                'confidence': 'High' if month <= 2 else 'Medium' if month <= 4 else 'Low'
            })

        return {
            'success': True,
            'predictions': predictions,
            'total_predicted': round(sum(p['predicted_amount'] for p in predictions), 2),
            'trend': 'Increasing' if trend > 0 else 'Decreasing' if trend < 0 else 'Stable',
            'model': 'Trend Analysis'
        }

    def _fallback_prediction(self, user, days_ahead: int) -> Dict:
        """Fallback to simple average-based prediction."""
        from apps.expenses.models import Expense

        # Calculate average daily expense from last 30 days
        last_30_days = timezone.now().date() - timedelta(days=30)
        avg_daily = Expense.objects.filter(
            user=user,
            transaction_date__gte=last_30_days
        ).aggregate(
            daily_avg=Avg('amount')
        )['daily_avg'] or 0

        predictions = []
        for day in range(1, days_ahead + 1):
            pred_date = timezone.now().date() + timedelta(days=day)
            predictions.append({
                'date': pred_date.isoformat(),
                'predicted_amount': round(float(avg_daily), 2),
                'day_of_week': pred_date.strftime('%A'),
                'confidence': 'Low'
            })

        return {
            'success': True,
            'predictions': predictions,
            'total_predicted': round(float(avg_daily * days_ahead), 2),
            'average_daily': round(float(avg_daily), 2),
            'model': 'Simple Average (Fallback)'
        }

    def _fallback_monthly_prediction(self, user, months_ahead: int) -> Dict:
        """Fallback monthly prediction."""
        from apps.expenses.models import Expense

        avg_monthly = Expense.objects.filter(
            user=user
        ).aggregate(
            monthly_avg=Avg('amount')
        )['monthly_avg'] or 0

        avg_monthly *= 30  # Approximate monthly total

        predictions = []
        for month in range(1, months_ahead + 1):
            pred_date = timezone.now().date() + timedelta(days=30*month)
            predictions.append({
                'month': pred_date.strftime('%b %Y'),
                'predicted_amount': round(float(avg_monthly), 2),
                'confidence': 'Low'
            })

        return {
            'success': True,
            'predictions': predictions,
            'total_predicted': round(float(avg_monthly * months_ahead), 2),
            'model': 'Simple Average (Fallback)'
        }


# Singleton instance
expense_forecaster = ExpenseForecasterService()
