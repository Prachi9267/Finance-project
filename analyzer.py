import pandas as pd
import re
import tabula
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import os
import uuid


def detect_column(df, keywords):
    for col in df.columns:
        col_lower = col.lower().strip()

        for keyword in keywords:
            if keyword in col_lower:
                return col

    return None

def detect_narration_column(df):
    for col in df.columns:
        if re.search(r'narration|description|transaction|details', col.lower()):
            return col
    return None


def clean_narration(text):
    text = str(text).upper().strip()

    text = re.sub(r'DMRC.*', 'DMRC', text)
    text = re.sub(r'ZOMATO.*', 'ZOMATO', text)
    text = re.sub(r'SWIGGY.*', 'SWIGGY', text)
    text = re.sub(r'AMAZON.*', 'AMAZON', text)
    text = re.sub(r'FLIPKART.*', 'FLIPKART', text)
    text = re.sub(r'PHONEPE.*', 'PHONEPE', text)
    text = re.sub(r'GPAY.*', 'GPAY', text)
    text = re.sub(r'PAYTM.*', 'PAYTM', text)

    text = re.sub(r'[-_.,:;0-9]+$', '', text).strip()

    return text

def extract_merchant(narration):

    narration = str(narration).upper()

    # Remove payment platforms
    remove_words = [
        "UPI","TO","FROM",
        "GOOGLEPAY",
        "GPAY",
        "PHONEPE",
        "PAYTM",
        "SUPERMONEY",
        "NEFT",
        "IMPS",
        "RTGS","MR","AXIS","OKAXIS"
        "TRANSFER",
        "PAYMENT"
    ]

    for word in remove_words:
        narration = re.sub(rf'\b{re.escape(word)}\b', ' ', narration)

    narration = re.sub(r'[^A-Z ]', ' ', narration)

    words = narration.split()
    cleaned_words = []

    for word in words:
        if len(word) <= 2:
            continue
        if len(word) > 15:
            continue

        cleaned_words.append(word)

    if cleaned_words:
        return " " + " ".join(cleaned_words[:2]).title()

    return "Unclassified"

def categorize_transaction(narration):

    narration = str(narration).upper()

    if any(x in narration for x in ['ZOMATO', 'SWIGGY', 'FOOD', 'RESTAURANT']):
        return 'Food & Dining'

    elif any(x in narration for x in ['DMRC', 'UBER', 'OLA', 'CAB', 'PETROL', 'FUEL', 'TRAVEL']):
        return 'Travel & Fuel'

    elif any(x in narration for x in ['AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'SHOP', 'NYKAA', 'H AND M']):
        return 'Online Shopping'

    elif any(x in narration for x in ['ELECTRICITY', 'WATER', 'BILL', 'RECHARGE', 'INTERNET']):
        return 'Utilities'

    elif any(x in narration for x in ['INSURANCE', 'SIP', 'MUTUAL FUND', 'GROWW']):
        return 'Investments'

    elif any(x in narration for x in ['BLINKIT', 'BIGBASKET', 'GROCERY', 'MART', 'ZEPTO', 'INSTAMART']):
        return 'Groceries'

    return extract_merchant(narration)


def analyze_statement(pdf_path):

    csv_path = pdf_path.replace(".pdf", ".csv")

    tabula.convert_into(
        pdf_path,
        csv_path,
        output_format = "csv",
        pages="all",
        stream=True
    )

    df = pd.read_csv(csv_path)
    print("COLUMNS FOUND:")
    print(df.columns.tolist())

    df = df.dropna(how="all")

    summary_keywords = [
        "STATEMENT SUMMARY",
        "ACCOUNT SUMMARY",
        "TRANSACTION SUMMARY"
]

    for idx in df.index:

        row_text = " ".join(
            str(x)
            for x in df.loc[idx].values
        ).upper()

        if any(
            keyword in row_text
            for keyword in summary_keywords
        ):

            print(
                f"Summary section starts at row {idx}"
            )

            df = df.iloc[:idx]

            break
    
    # Merge multi-line narrations

    for idx in range(1, len(df)):

        current_date = df.iloc[idx]["Date"]

    
        if pd.isna(current_date):

            prev_idx = idx - 1

            current_narration = str(
                df.iloc[idx]["Narration"]
            )

            prev_narration = str(
                df.iloc[prev_idx]["Narration"]
            )

            if current_narration != "nan":

                df.at[
                    df.index[prev_idx],
                    "Narration"
                ] = (
                    prev_narration
                    + " "
                    + current_narration
                )
    df = df[df["Date"].notna()].copy()
    
    money_columns = [
    ("withdraw_col", "credit_col"),
    ("credit_col", "balance_col")
]

    for source_col, target_col in money_columns:
        if source_col not in df.columns:
           continue

        if target_col not in df.columns:
            continue

        for idx in df.index:

            value = str(df.at[idx, source_col])

            amounts = re.findall(
                r'[\d,]+\.\d{2}',
                value
        )

            if (
                len(amounts) == 2
                and (
                    pd.isna(df.at[idx, target_col])
                    or str(df.at[idx, target_col]).strip() in ["", "nan"]
                )
            ):

                df.at[idx, source_col] = amounts[0]

                df.at[idx, target_col] = amounts[1]

                print(
                    f"Fixed row {idx}: "
                    f"{amounts[0]} -> {source_col}, "
                    f"{amounts[1]} -> {target_col}"
            )
    
    df.columns = df.columns.str.strip()

    narration_col = detect_narration_column(df)

    withdraw_col = detect_column(
        df,
        ['withdraw', 'debit', 'dr']
    )

    credit_col = detect_column(
        df,
        ['deposit', 'credit', 'cr']
    )

    if narration_col is None:
        raise Exception(
            f"Narration column not detected.\nColumns found: {list(df.columns)}"
        )

    if withdraw_col is None:
        raise Exception(
            f"Withdrawal column not detected.\nColumns found: {list(df.columns)}"
        )

    if credit_col is None:
        raise Exception(
            f"Credit column not detected.\nColumns found: {list(df.columns)}"
        )

    df.rename(
        columns={
            narration_col: "narration",
            withdraw_col: "withdrawal_amt",
            credit_col: "deposit_amt"
        },
        inplace=True
    )

    df["withdrawal_amt"] = (
        df["withdrawal_amt"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    df["deposit_amt"] = (
        df["deposit_amt"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    df["withdrawal_amt"] = pd.to_numeric(
        df["withdrawal_amt"],
        errors="coerce"
    ).fillna(0)

    df["deposit_amt"] = pd.to_numeric(
        df["deposit_amt"],
        errors="coerce"
    ).fillna(0)

    df = df[
    (df["withdrawal_amt"] > 0)
    |
    (df["deposit_amt"] > 0)
    ]

    df["Clean_Narration"] = df["narration"].apply(
        clean_narration
    )

    df["Category"] = df["Clean_Narration"].apply(
        categorize_transaction
    )
    
    print(
    df[
        [
            "Date",
            "narration",
            "withdrawal_amt",
            "deposit_amt",
            "Category"
        ]
    ].to_string()
)

    total_credit = float(
        df["deposit_amt"].sum()
    )

    total_debit = float(
        df["withdrawal_amt"].sum()
    )

    spending_df = (
        df[df["withdrawal_amt"] > 0]
        .groupby("Category")["withdrawal_amt"]
        .sum()
        .sort_values(ascending=False)
    )

    os.makedirs("static", exist_ok=True)

    chart_filename = f"{uuid.uuid4().hex}.png"

    chart_path = os.path.join(
        "static",
        chart_filename
    )

    highest_category = "N/A"
    highest_amount = 0

    if not spending_df.empty:

        highest_category = spending_df.idxmax()
        highest_amount = float(spending_df.max())

        plt.figure(figsize=(10, max(6, len(spending_df)*0.5)))

        plt.barh(
            spending_df.index,
            spending_df.values
        )

        plt.title(
            "Total Spending per Category"
        )

        plt.xlabel("Amount(₹)")
        plt.ylabel("Category")

        plt.tight_layout()

        plt.savefig(chart_path)

        plt.close()

    return {
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "highest_category": highest_category,
        "highest_amount": round(highest_amount, 2),
        "transaction_count": len(df),
        "spending": spending_df.to_dict(),
        "chart_file": chart_filename
    }