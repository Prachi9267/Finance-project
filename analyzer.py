#!/usr/bin/env python
# coding: utf-8

# In[2]:
import tabula
import pandas as pd
import re

def clean_amount(x):
    if isinstance(x, str):
        x = x.replace(",", "").strip()
    try:
        return float(x)
    except:
        return None


def analyze_bank_statement(uploaded_pdf):
    try:
        # Read PDF using Tabula
        dfs = tabula.read_pdf(uploaded_pdf, pages='all', multiple_tables=True)

        if not dfs or len(dfs) == 0:
            return {"error": "No tables found in PDF"}

        # Combine all tables
        df = pd.concat(dfs, ignore_index=True)

        # Fix column names
        df.columns = ["date", "narration", "withdrawal_amt", "deposit_amt"][:len(df.columns)]

        df["withdrawal_amt"] = df["withdrawal_amt"].apply(clean_amount)
        df["deposit_amt"] = df["deposit_amt"].apply(clean_amount)

        # ======== CLEAN NARRATION TEXT =========
        def clean_narration(text):
            text = str(text).upper().strip()
            replacements = ['DMRC','ZOMATO','SWIGGY','AMAZON','FLIPKART','PHONEPE','PAYTM','GPAY']
            for r in replacements:
                text = re.sub(rf'{r}.*', r, text)
            text = re.sub(r'[-_.,:;0-9]+$', '', text).strip()
            return text

        df['Clean_Narration'] = df['narration'].apply(clean_narration)

        # ======== CATEGORY MAPPING =========
        def categorize_transaction_base(narration):
            narration = str(narration)

            mapping = {
                'Food & Dining 🍱': ['ZOMATO', 'SWIGGY', 'FOOD', 'RESTAURANT'],
                'Travel & Fuel 🚗': ['DMRC', 'UBER', 'OLA', 'CAB', 'PETROL', 'FUEL', 'TRAVEL'],
                'Online Shopping 🛍️': ['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'SHOP'],
                'Utilities 💡': ['ELECTRICITY', 'WATER', 'BILL', 'RECHARGE', 'INTERNET'],
                'Investments 📈': ['INSURANCE', 'SIP', 'MUTUAL FUND', 'GROWW'],
                'Groceries 🛒': ['BLINKIT', 'BIGBASKET', 'GROCERY', 'MART', 'ZEPTO'],
            }

            for category, keywords in mapping.items():
                if any(k in narration for k in keywords):
                    return category
            return "Others 💼"

        df['Category'] = df['Clean_Narration'].apply(categorize_transaction_base)

        # ===== Dynamic category naming ======
        def create_dynamic_category(narration):
            narration = str(narration).title()
            if len(narration) > 30:
                narration = narration[:30] + '...'
            return f'🔹 {narration}'

        df['Category'] = df.apply(
            lambda row: create_dynamic_category(row['Clean_Narration'])
            if row['Category'] == 'Others 💼' and row['withdrawal_amt'] > 0
            else row['Category'],
            axis=1
        )

        df['Category'] = df['Category'].replace('Others 💼', 'Unclassified Payment 💼')

        # Summary
        df["amount"] = df["withdrawal_amt"].fillna(0) * -1 + df["deposit_amt"].fillna(0)
        spending_df = df.groupby("Category")["amount"].sum()

        return {
            "df": df,
            "spending_df": spending_df,
            "total_credit": df["deposit_amt"].sum(),
            "total_debit": df["withdrawal_amt"].sum()
        }

    except Exception as e:
        return {"error": f"PDF extraction failed: {e}"}




