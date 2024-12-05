from fastapi import FastAPI
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
import calendar
from datetime import date, timedelta, datetime
from typing import List
from botocore.exceptions import ClientError
from uuid import uuid4
from boto3.dynamodb.conditions import Key
from utils.transactions import get_transaction_service
from models.transaction import Transaction
from calendar import monthrange

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.today = datetime.now()
        self.start_range = self.today - timedelta(days=30)
        self.end_range = self.today + timedelta(days=210)
        self.balance_dict = self.initialize_balance_dict(self.start_range, self.end_range)
        self.income_transactions = []
        self.expense_transactions = []
        self.current_balance = Decimal(0)

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Convert string date to datetime object."""
        return datetime.strptime(date_str, "%m-%d-%Y") if date_str else None

    def initialize_balance_dict(self, start_date: datetime, end_date: datetime) -> Dict[datetime, Dict[str, Optional[Decimal]]]:
        """Initialize balance dictionary for the specified date range."""
        return {start_date + timedelta(days=i): {'balance': Decimal(0), 'overdraft': None, 'can_pay': True} 
                for i in range((end_date - start_date).days + 1)}
        
    def separate_transactions_by_type(self, transactions):
        # Separate transactions into income and expense lists
        for transaction in transactions:
            if transaction.type == 'income':
                self.income_transactions.append(transaction)
            elif transaction.type == 'expense':
                self.expense_transactions.append(transaction)

    def convert_balance_keys_to_string(self, balance_dict: Dict[datetime, Dict[str, any]]) -> Dict[str, Dict[str, any]]:
        """Convert the keys of a balance dictionary from datetime to string format 'mm-dd-yyyy'."""
        converted_dict = {}
        
        for date_key, value in balance_dict.items():
            # Convert datetime key to string in 'mm-dd-yyyy' format
            date_str = date_key.strftime("%m-%d-%Y")
            converted_dict[date_str] = value
        
        return converted_dict
        
    
    def is_within_date_range(self, start_date, end_date, check_start, check_end):
        return (check_start <= end_date) and (check_end >= start_date)

    def add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, monthrange(year, month)[1])
        return datetime(year, month, day)
    
    def add_month_if_possible(self, original_date, current_date):
        
        next_month = current_date.month + 1
        next_year = current_date.year
        
        if next_month > 12:
            next_month = 1
            next_year += 1
            
        last_day_of_next_month = calendar.monthrange(next_year, next_month)[1]

        if original_date.day <= last_day_of_next_month:
            new_date = current_date.replace(year=next_year, month=next_month, day=original_date.day)
        else:
            new_date = current_date.replace(year=next_year, month=next_month, day=last_day_of_next_month)
        
        return new_date
            
    def date_range(self, start_date_str, end_date_str):
        start_date = self.parse_date(start_date_str.strftime("%m-%d-%Y"))
        end_date = self.parse_date(end_date_str.strftime("%m-%d-%Y"))
        
        if start_date and end_date:
            current_date = start_date
            while current_date <= end_date:
                yield current_date
                current_date += timedelta(days=1)

    def calculate_recurring_dates(self, transactions, recurring_transactions):
        """Calculate recurring income transactions for the next 7 months."""
        today = datetime.now()
        start_window = today - timedelta(days=30)
        end_window = today + timedelta(days=210)
        start_window = self.parse_date(start_window.strftime("%m-%d-%Y"))
        end_window = self.parse_date(end_window.strftime("%m-%d-%Y"))
        logger.info(f"Start window: {start_window}, End window: {end_window}")
        transaction_dates = {}

        for transaction in transactions:
            # if transaction.type != 'income':
            #     continue
            if transaction.start_date:
                start_date = self.parse_date(transaction.start_date)
            else:
                start_date = self.parse_date(transaction.date_of_transaction)
            if(transaction.skip_end_date):
                end_date = self.parse_date(end_window.strftime("%m-%d-%Y"))
            else:
                if transaction.end_date:
                    end_date = self.parse_date(transaction.end_date)
                else:
                    end_date = self.parse_date(transaction.date_of_transaction)
            
            # Check if the transaction falls within the specified date range
            if not self.is_within_date_range(start_date, end_date, start_window, end_window):
                continue
            
            if transaction.frequency == 'one-time':
                trans_date = self.parse_date(transaction.date_of_transaction)
                if start_window <= trans_date <= end_window:
                    transaction_dates[trans_date] = transaction_dates.get(trans_date, Decimal(0)) + Decimal(transaction.amount)
                    recurring_transactions[trans_date].append(transaction)

            elif transaction.frequency in ['weekly', 'bi-weekly']:
                trans_date = self.parse_date(transaction.start_date)
                interval_days = 7 if transaction.frequency == 'weekly' else 14
                target_weekday = transaction.day - 1  # Adjust for 0-indexed weekday

                if trans_date.weekday() != target_weekday:
                    days_diff = (target_weekday - trans_date.weekday()) % 7
                    
                    # If the difference is more than 3 days, subtract instead of add
                    if days_diff > 3:
                        days_diff -= 7
                    
                    trans_date += timedelta(days=days_diff)
                    
                # Generate dates for weekly or bi-weekly transactions
                while trans_date <= end_window:
                    if trans_date >= start_window and trans_date <= end_date:
                        transaction_dates[trans_date] = transaction_dates.get(trans_date, Decimal(0)) + Decimal(transaction.amount)
                        recurring_transactions[trans_date].append(transaction)
                    
                    trans_date += timedelta(days=interval_days)

            elif transaction.frequency == 'semi-monthly':
                first_trans_date = self.parse_date(transaction.date_of_transaction)
                second_trans_date = self.parse_date(transaction.date_of_second_transaction)
                
                while first_trans_date <= end_window or second_trans_date <= end_window:
                    if first_trans_date >= start_window and first_trans_date <= end_date:
                        transaction_dates[first_trans_date] = transaction_dates.get(first_trans_date, Decimal(0)) + transaction.amount
                        recurring_transactions[first_trans_date].append(transaction)
                    
                    if second_trans_date >= start_window and second_trans_date <= end_date:
                        transaction_dates[second_trans_date] = transaction_dates.get(second_trans_date, Decimal(0)) + transaction.amount
                        recurring_transactions[second_trans_date].append(transaction)
                        
                    first_trans_date = self.add_months(first_trans_date, 1)
                    second_trans_date = self.add_months(second_trans_date, 1)

            elif transaction.frequency == 'monthly':
                trans_date = self.parse_date(transaction.date_of_transaction)
                orignal_date = self.parse_date(transaction.date_of_transaction)
                
                while trans_date <= end_window:
                    if trans_date >= start_window and trans_date <= end_date:
                        transaction_dates[trans_date] = transaction_dates.get(trans_date, Decimal(0)) + transaction.amount
                        recurring_transactions[trans_date].append(transaction)
                        
                    # Move to the next month for monthly transactions
                    trans_date = self.add_month_if_possible(orignal_date, trans_date)
                    # trans_date = self.add_months(trans_date, 1)

        return dict(sorted(transaction_dates.items())), recurring_transactions
    
    def calculate_daily_finances(self, income_dict, expense_dict, start_date_str, end_date_str):

        start_date = self.parse_date(start_date_str.strftime("%m-%d-%Y"))
        end_date = self.parse_date(end_date_str.strftime("%m-%d-%Y"))

        result = {}
        prev_balance = Decimal('0')

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%m-%d-%Y")
            
            # Get income and expenses for the current day
            daily_income = sum(transaction.amount for transaction in income_dict.get(current_date, []))
            daily_expenses = expense_dict.get(current_date, [])
            # daily_expenses = sum(transaction.amount for transaction in expense_dict.get(current_date, []))

            # Calculate available balance for the day
            available_balance = prev_balance + daily_income

            # Process expenses
            can_pay_all = True
            paid_expenses = []
            unpaid_expenses = []
            overdraft = Decimal('0')

            for expense in daily_expenses:
                if available_balance >= expense.amount:
                    available_balance -= expense.amount
                    paid_expenses.append(expense)
                else:
                    can_pay_all = False
                    unpaid_expenses.append(expense)
                    overdraft += expense.amount - available_balance
                    available_balance = Decimal('0')
                    # break  # Stop processing further expenses
                    if available_balance < 0:
                        break

            # Prepare the result for this day
            day_result = {
                'opening_balance': prev_balance,
                'closing_balance': available_balance,
                'can_pay': can_pay_all,
                'paid_transactions': paid_expenses,
                'unpaid_transactions': unpaid_expenses,
                'income': daily_income,
                'income_transactions': income_dict.get(current_date, []),
            }

            if not can_pay_all:
                day_result['overdraft'] = overdraft

            result[date_str] = day_result

            # Update previous balance for the next day
            prev_balance = available_balance

            current_date += timedelta(days=1)

        return result
    
    def calculate_balances(self) -> Dict[datetime, Dict[str, Optional[Decimal]]]:
        """Calculate daily balances based on the list of transactions."""
        
        logger.info(f"Calculating balances for user: {self.user_id}")
        transactions = get_transaction_service().list_user_transactions(self.user_id)
        self.separate_transactions_by_type(transactions)
        today = datetime.now()
        start_window = today - timedelta(days=30)
        end_window = today + timedelta(days=210)
        recurring_income_transactions = {date: [] for date in self.date_range(start_window, end_window)}
        recurring_expense_transactions = {date: [] for date in self.date_range(start_window, end_window)}
        
        recurring_income , recurring_income_transactions= self.calculate_recurring_dates(self.income_transactions, recurring_income_transactions)
        recurring_expense, recurring_expense_transactions = self.calculate_recurring_dates(self.expense_transactions, recurring_expense_transactions)
        results = self.calculate_daily_finances(recurring_income_transactions, recurring_expense_transactions, start_window, end_window)
        return results
       