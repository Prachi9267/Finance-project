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
            if keyword.lower() in col_lower:
                return col

    return None


def detect_narration_column(df):
    for col in df.columns:
        if re.search(
            r"narration|description|transaction|details|particulars", col.lower()
        ):
            return col
    return None


def detect_date_column(df):

    for col in df.columns:

        col_lower = col.lower().strip()

        if any(
            keyword in col_lower
            for keyword in ["date", "tran date", "transaction date", "txn date"]
        ):
            return col

    return None


def clean_narration(text):
    text = str(text).upper().strip()

    text = re.sub(r"DMRC.*", "DMRC", text)
    text = re.sub(r"ZOMATO.*", "ZOMATO", text)
    text = re.sub(r"SWIGGY.*", "SWIGGY", text)
    text = re.sub(r"AMAZON.*", "AMAZON", text)
    text = re.sub(r"FLIPKART.*", "FLIPKART", text)
    text = re.sub(r"PHONEPE.*", "PHONEPE", text)
    text = re.sub(r"GPAY.*", "GPAY", text)
    text = re.sub(r"PAYTM.*", "PAYTM", text)

    text = re.sub(r"[-_.,:;0-9]+$", "", text).strip()

    return text


def extract_merchant(narration):

    narration = str(narration).upper()

    # Remove payment platforms
    remove_words = [
        "UPI",
        "P2A",
        "P2M",
        "P2V",
        "BANK",
        "TO",
        "FROM",
        "ICIC",
        "HDFC",
        "GOOGLEPAY",
        "SBI",
        "AXIS",
        "PAID",
        "GPAY",
        "TO",
        "FROM",
        "PHONEPE",
        "PAYTM",
        "PAY",
        "SUPERMONEY",
        "NEFT",
        "IMPS",
        "RTGS",
        "MR",
        "AXIS",
        "OKAXIS",
        "TRANSFER",
        "PAYMENT",
        "YES",
        "KOTAK",
        "SBIN",
        "IDIB",
        "UTIB",
        "SENT",
        "YESB",
        "MAH",
        "VIA",
    ]

    for word in remove_words:
        narration = re.sub(rf"\b{re.escape(word)}\b", " ", narration)

    narration = re.sub(r"[^A-Z ]", " ", narration)

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

    if any(
        x in narration
        for x in [
            "ZOMATO",
            "SWIGGY",
            "FOOD",
            "RESTAURANT",
            "SNACKS",
            "CAFE",
            "DHABA",
            "KITCHEN",
            "HALDI RAM",
        ]
    ):
        return "Food & Dining"

    elif any(
        x in narration
        for x in ["DMRC", "UBER", "OLA", "CAB", "PETROL", "FUEL", "TRAVEL", "RAPIDO"]
    ):
        return "Travel & Fuel"

    elif any(
        x in narration
        for x in [
            "AMAZON",
            "FLIPKART",
            "MYNTRA",
            "AJIO",
            "SHOP",
            "NYKAA",
            "H AND M",
            "HANDM",
            "TIRA BEAUTY",
            "TIRABEAUTY",
            "TIRA",
        ]
    ):
        return "Online Shopping"

    elif any(
        x in narration for x in ["ELECTRICITY", "WATER", "BILL", "RECHARGE", "INTERNET"]
    ):
        return "Utilities"

    elif any(x in narration for x in ["INSURANCE", "SIP", "MUTUAL FUND", "GROWW"]):
        return "Investments"

    elif any(
        x in narration
        for x in [
            "BLINKIT",
            "BIGBASKET",
            "GROCERY",
            "MART",
            "ZEPTO",
            "INSTAMART",
            "ALL MART",
        ]
    ):
        return "Groceries"

    return extract_merchant(narration)


def build_hdfc_transactions(
    df,
    date_col,
    narration_col,
    withdraw_col,
    credit_col,
    closingamt_col,
):

    transactions = []

    current_transaction = None

    for idx in df.index:

        withdrawal = str(df.at[idx, withdraw_col]).strip()

        deposit = str(df.at[idx, credit_col]).strip()

        has_amount = withdrawal not in ["", "nan", "NaN"] or deposit not in [
            "",
            "nan",
            "NaN",
        ]

        narration = str(df.at[idx, narration_col]).strip()

        if has_amount:

            if current_transaction is not None:
                transactions.append(current_transaction)

            current_transaction = {
                "Date": df.at[idx, date_col],
                "narration": narration if narration.lower() != "nan" else "",
                "withdrawal_amt": withdrawal,
                "deposit_amt": deposit,
                "Closing Balance": df.at[idx, closingamt_col],
            }

        else:

            if (
                current_transaction is not None
                and narration
                and narration.lower() != "nan"
            ):
                current_transaction["narration"] += " " + narration

    if current_transaction is not None:
        transactions.append(current_transaction)

    return pd.DataFrame(transactions)


def build_axis_transactions(
    df,
    date_col,
    narration_col,
    withdraw_col,
    credit_col,
    closingamt_col,
):

    transactions = []

    pending_narration = ""

    for idx in df.index:

        narration = str(df.at[idx, narration_col]).strip()

        date_value = str(df.at[idx, date_col]).strip()

        has_date = date_value and date_value.lower() != "nan"

        if not has_date:

            if narration and narration.lower() != "nan":
                pending_narration += " " + narration

        else:

            transactions.append(
                {
                    "Date": date_value,
                    "narration": (pending_narration + " " + narration).strip(),
                    "withdrawal_amt": df.at[idx, withdraw_col],
                    "deposit_amt": df.at[idx, credit_col],
                    "Closing Balance": df.at[idx, closingamt_col],
                }
            )

            pending_narration = ""

    return pd.DataFrame(transactions)


def analyze_statement(pdf_path):

    csv_path = pdf_path.replace(".pdf", ".csv")

    tabula.convert_into(
        pdf_path,
        csv_path,
        output_format="csv",
        pages="all",
        stream=True,
        force_subprocess=True,
    )
    df = pd.read_csv(csv_path)
    if "Particulars" in df.columns:
        print("Kotak detected -> retrying with lattice")

        tabula.convert_into(
            pdf_path,
            csv_path,
            output_format="csv",
            pages="all",
            lattice=True,
            force_subprocess=True,
        )
        df = pd.read_csv(csv_path)

    df = df.dropna(how="all")

    print("COLUMNS FOUND:")
    print(df.columns.tolist())
    # Find where statement summary starts

    summary_row = None
    end_markers = [
        "STATEMENT SUMMARY",
        "SUMMARY",
        "TRANSACTION SUMMARY",
        "TOTAL TRANSACTIONS",
        "ACCOUNT SUMMARY",
    ]

    for idx in df.index:

        row_text = " ".join(str(x) for x in df.loc[idx].values).upper()

        if any(marker in row_text for marker in end_markers):
            summary_row = idx
            print(f"End section found at row {idx}")
            break

    if summary_row is not None:
        df = df.iloc[:summary_row]

    df.columns = df.columns.str.strip()

    date_col = detect_date_column(df)

    narration_col = detect_narration_column(df)

    if narration_col and "particulars" in narration_col.lower():
        pattern = "axis"
    else:
        pattern = "hdfc"

    withdraw_col = detect_column(df, ["withdraw", "debit", "dr"])

    credit_col = detect_column(df, ["deposit", "credit", "cr"])

    closingamt_col = detect_column(
        df, ["Closing Balance", "Closing Balance*", "balance"]
    )

    if pattern == "axis":
        df = build_axis_transactions(
            df,
            date_col,
            narration_col,
            withdraw_col,
            credit_col,
            closingamt_col,
        )
    else:
        df = build_hdfc_transactions(
            df,
            date_col,
            narration_col,
            withdraw_col,
            credit_col,
            closingamt_col,
        )

    if date_col is None:
        raise Exception(f"Date column not detected.\nColumns found: {list(df.columns)}")
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

    if closingamt_col is None:
        raise Exception(
            f"Closing Amount column not detected.\nColumns found: {list(df.columns)}"
        )

    money_columns = [
        ("withdrawal_amt", "deposit_amt"),
        ("deposit_amt", "Closing Balance"),
    ]

    for source_col, target_col in money_columns:
        if source_col not in df.columns:
            continue

        if target_col not in df.columns:
            continue

        for idx in df.index:

            value = str(df.at[idx, source_col])

            amounts = re.findall(r"[\d,]+\.\d{2}", value)

            if len(amounts) == 2 and (
                pd.isna(df.at[idx, target_col])
                or str(df.at[idx, target_col]).strip() in ["", "nan"]
            ):

                df.at[idx, source_col] = amounts[0]

                df.at[idx, target_col] = amounts[1]

                print(
                    f"Fixed row {idx}: "
                    f"{amounts[0]} -> {source_col}, "
                    f"{amounts[1]} -> {target_col}"
                )

    df["withdrawal_amt"] = (
        df["withdrawal_amt"].astype(str).str.replace(",", "", regex=False).str.strip()
    )

    df["deposit_amt"] = (
        df["deposit_amt"].astype(str).str.replace(",", "", regex=False).str.strip()
    )

    df["withdrawal_amt"] = pd.to_numeric(df["withdrawal_amt"], errors="coerce").fillna(
        0
    )

    df["deposit_amt"] = pd.to_numeric(df["deposit_amt"], errors="coerce").fillna(0)

    df = df[(df["withdrawal_amt"] > 0) | (df["deposit_amt"] > 0)]

    df["Clean_Narration"] = df["narration"].apply(clean_narration)

    df["Category"] = df["Clean_Narration"].apply(categorize_transaction)

    total_credit = float(df["deposit_amt"].sum())

    total_debit = float(df["withdrawal_amt"].sum())

    print(df[["narration", "Category"]].to_string())

    spending_df = (
        df[df["withdrawal_amt"] > 0]
        .groupby("Category")["withdrawal_amt"]
        .sum()
        .sort_values(ascending=False)
    )

    os.makedirs("static", exist_ok=True)

    chart_filename = f"{uuid.uuid4().hex}.png"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    chart_path = os.path.join(BASE_DIR, "static", chart_filename)

    highest_category = "N/A"
    highest_amount = 0

    if not spending_df.empty:

        highest_category = spending_df.idxmax()
        highest_amount = float(spending_df.max())

        plt.figure(figsize=(10, max(6, len(spending_df) * 0.5)))

        plt.barh(spending_df.index, spending_df.values, color="#FF8F63")

        plt.title("Total Spending per Category")

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
        "chart_file": chart_filename,
    }
