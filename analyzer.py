#!/usr/bin/env python
# coding: utf-8

# In[2]:




# In[3]:


import pandas as pd
import numpy as np
import re
import tabula
import os

def analyze_bank_statement(uploaded_file):

    # Save uploaded file temporarily
    pdf_path = "uploaded_statement.pdf"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())

    # Convert PDF → CSV
    csv_path = pdf_path.replace('.pdf', '.csv')

    try:
        tabula.convert_into(pdf_path, csv_path, output_format="csv", pages='all', guess=True)
    except Exception as e:
        return {"error": f"PDF extraction failed: {e}"}

    # Load CSV
    df = pd.read_csv(csv_path)

    # === Auto-detect key columns ===
    def detect_column(df, keywords):
        for col in df.columns:
            if any(re.search(k, col.lower()) for k in keywords):
                return col
        return None

    def detect_narration_column(df):
        for col in df.columns:
            if re.search(r'narration|description|transaction|details', col.lower()):
                return col
        return None

    narration_col = detect_narration_column(df)
    withdraw_col = detect_column(df, ['withdraw', 'debit', 'dr'])
    credit_col = detect_column(df, ['deposit', 'credit', 'cr'])

    if narration_col:
        df.rename(columns={narration_col: 'narration'}, inplace=True)
    if withdraw_col:
        df.rename(columns={withdraw_col: 'withdrawal_amt'}, inplace=True)
    if credit_col:
        df.rename(columns={credit_col: 'deposit_amt'}, inplace=True)

    # Clean numeric columns
    df['withdrawal_amt'] = pd.to_numeric(df.get('withdrawal_amt', 0), errors='coerce').fillna(0)
    df['deposit_amt'] = pd.to_numeric(df.get('deposit_amt', 0), errors='coerce').fillna(0)

    # === Clean Narration Text ===
    def clean_narration(text):
        text = str(text).upper().strip()
        replacements = ['DMRC', 'ZOMATO', 'SWIGGY', 'AMAZON', 'FLIPKART', 'PHONEPE', 'PAYTM', 'GPAY']
        for r in replacements:
            text = re.sub(rf'{r}.*', r, text)
        text = re.sub(r'[-_.,:;0-9]+$', '', text).strip()
        return text

    df['Clean_Narration'] = df['narration'].apply(clean_narration)

    # === Categorize Transactions ===
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

    # Dynamic category naming
    def create_dynamic_category(narration):
        narration = str(narration).title()
        if len(narration) > 30:
            narration = narration[:30] + '...'
        return f'🔹 {narration}'

    df['Category'] = df.apply(
        lambda row: create_dynamic_category(row['Clean_Narration']) 
        if row['Category'] == 'Others 💼' and row['withdrawal_amt'] > 0
        else row['Category'], axis=1
    )

    df['Category'] = df['Category'].replace('Others 💼', 'Unclassified Payment 💼')

    # === Summary ===
    total_credit = df['deposit_amt'].sum()
    total_debit = df['withdrawal_amt'].sum()

    spending_df = (
        df[df['withdrawal_amt'] > 0]
        .groupby('Category')['withdrawal_amt']
        .sum()
        .sort_values(ascending=False)
    )

    return {
        "df": df,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "spending_df": spending_df
    }


# In[ ]:




