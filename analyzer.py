#!/usr/bin/env python
# coding: utf-8

# In[2]:




# In[3]:
import pdfplumber
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
        rows = []

        # === Extract tables from PDF ===
        with pdfplumber.open(uploaded_pdf) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:

                        if not row or len(row) < 4:
                            continue

                        date = row[0]
                        narration = row[1]
                        withdrawal_amt = row[2]
                        deposit_amt = row[3]

                        # Validate date
                        if not re.match(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", str(date)):
                            continue

                        rows.append([
                            date,
                            narration,
                            clean_amount(withdrawal_amt),
                            clean_amount(deposit_amt),
                        ])

        if len(rows) == 0:
            return {
                "error": "No valid transaction rows found in the PDF. Try another statement."
            }

        df = pd.DataFrame(rows, columns=["date", "narration", "withdrawal_amt", "deposit_amt"])

        # ================================================================
        # 🔥🔥  YOUR EXACT CATEGORIZATION CODE STARTS HERE  🔥🔥
        # ================================================================

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

        # === Dynamic category naming ===
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

        # ================================================================
        # 🔥🔥  YOUR EXACT CATEGORIZATION CODE ENDS HERE  🔥🔥
        # ================================================================

        # Summary table
        df['amount'] = df['withdrawal_amt'].fillna(0) * -1 + df['deposit_amt'].fillna(0)
        spending_df = df[df['amount'] < 0].groupby("Category")["amount"].sum().abs()

        return {
            "df": df,
            "spending_df": spending_df,
            "total_credit": df['deposit_amt'].sum(),
            "total_debit": df['withdrawal_amt'].sum()
        }

    except Exception as e:
        return {"error": str(e)}


# In[ ]:




