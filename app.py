#!/usr/bin/env python
# coding: utf-8

# In[1]:


# In[2]:


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from analyzer import analyze_bank_statement

st.set_page_config(page_title="Bank Statement Analyzer", layout="wide")

st.title("💰 Bank Statement Analyzer")
st.write("Upload your bank statement PDF to extract transactions, categorize spending, and view insights.")

uploaded_file = st.file_uploader(
    "📄 Upload Bank Statement (PDF)",
    type=["pdf"]
)

if uploaded_file:
    st.info("Processing the PDF… This may take a few seconds.")

    result = analyze_bank_statement(uploaded_file)

    if "error" in result:
        st.error(result["error"])
    else:
        df = result["df"]
        spending_df = result["spending_df"]

        st.success("Analysis complete! ✔")

        # === Summary Cards ===
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Credited", f"₹ {result['total_credit']:,.2f}")
        col2.metric("💸 Total Debited", f"₹ {result['total_debit']:,.2f}")

        # === Category Chart ===
        if not spending_df.empty:
            # === Category-wise Spending Table ===
            st.subheader("📊 Category-wise Spending Table")

            category_table = spending_df.reset_index()
            category_table.columns = ["Category", "Amount Spent"]

            st.dataframe(category_table, use_container_width=True)

            
            st.subheader("💸 Spending by Category")

            st.bar_chart(spending_df)

            st.subheader("🥇 Highest Spending Category")
            highest_cat = spending_df.idxmax()
            highest_amt = spending_df.max()

            st.write(f"### {highest_cat}")
            st.write(f"**₹ {highest_amt:,.2f}** spent here")


# In[ ]:




