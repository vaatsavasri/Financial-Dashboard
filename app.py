

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ── Page Configuration ───────────────────────
st.set_page_config(
    page_title="Financial Intelligence Dashboard",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Load Data ────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("unified_financial_dataset.csv")
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
    df['NetAmount']   = pd.to_numeric(df['NetAmount'],   errors='coerce')
    df['GrossAmount'] = pd.to_numeric(df['GrossAmount'], errors='coerce')
    df['VATAmount']   = pd.to_numeric(df['VATAmount'],   errors='coerce')

    # Add risk level if not present
    if 'RiskLevel' not in df.columns:
        p99 = df['NetAmount'].quantile(0.99)
        df['RiskLevel'] = 'Low'
        df.loc[df['NetAmount'] >= p99, 'RiskLevel'] = 'High'
        df.loc[df['NetAmount'].apply(
            lambda x: x % 500 == 0 or x % 1000 == 0
        ), 'RiskLevel'] = 'Medium'

    return df

df = load_data()

# ── Sidebar ──────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/financial-analytics.png", width=60)
st.sidebar.title("Dashboard Filters")
st.sidebar.markdown("---")

# Date filter
st.sidebar.subheader(" Date Range")
min_date = df['InvoiceDate'].min().date()
max_date = df['InvoiceDate'].max().date()
date_from = st.sidebar.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
date_to   = st.sidebar.date_input("To",   value=max_date, min_value=min_date, max_value=max_date)

# Vendor filter
st.sidebar.subheader("Vendor")
vendors = ["All Vendors"] + sorted(df['SupplierName'].dropna().unique().tolist())
selected_vendor = st.sidebar.selectbox("Select Vendor", vendors)

# Category filter
st.sidebar.subheader("Category")
categories = ["All Categories"] + sorted(df['ExpenseCategory'].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Select Category", categories)

# Status filter
st.sidebar.subheader(" Payment Status")
selected_status = st.sidebar.selectbox("Select Status",
    ["All", "Paid", "Pending", "Overdue"])

# Risk filter
st.sidebar.subheader("Risk Level")
selected_risk = st.sidebar.selectbox("Select Risk Level",
    ["All", "High", "Medium", "Low"])

# Fiscal year filter
st.sidebar.subheader("Fiscal Year")
fiscal_years = ["All"] + sorted(df['FiscalYear'].dropna().unique().tolist())
selected_fy = st.sidebar.selectbox("Fiscal Year", fiscal_years)

st.sidebar.markdown("---")
if st.sidebar.button("Reset All Filters"):
    st.rerun()

# ── Apply Filters ────────────────────────────
filtered = df.copy()
filtered = filtered[
    (filtered['InvoiceDate'] >= pd.to_datetime(date_from)) &
    (filtered['InvoiceDate'] <= pd.to_datetime(date_to))
]
if selected_vendor != "All Vendors":
    filtered = filtered[filtered['SupplierName'] == selected_vendor]
if selected_cat != "All Categories":
    filtered = filtered[filtered['ExpenseCategory'] == selected_cat]
if selected_status != "All":
    filtered = filtered[filtered['PaymentStatus'] == selected_status]
if selected_risk != "All":
    filtered = filtered[filtered['RiskLevel'] == selected_risk]
if selected_fy != "All":
    filtered = filtered[filtered['FiscalYear'] == selected_fy]

inv_pos = filtered[
    (filtered['TransactionType'] == 'Invoice') &
    (filtered['NetAmount'] > 0)
].copy()

# ── Header ───────────────────────────────────
st.title("Financial Intelligence Dashboard")
st.markdown(
    f"**Unified Financial Dataset** · "
    f"{len(filtered):,} records shown · "
    f"FY 2023/24–2024/25 · All amounts in GBP"
)
st.markdown("---")

# ── KPI Row ──────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

total_spend  = inv_pos['NetAmount'].sum()
total_txn    = len(filtered)
avg_inv      = inv_pos['NetAmount'].mean() if len(inv_pos) else 0
high_risk    = (filtered.get('RiskLevel', pd.Series()) == 'High').sum()
overdue_n    = (filtered['PaymentStatus'] == 'Overdue').sum()
paid_pct     = (filtered['PaymentStatus'] == 'Paid').sum() / max(len(filtered), 1) * 100

c1.metric("Total Spend",       f"£{total_spend/1e6:.2f}M")
c2.metric(" Transactions",      f"{total_txn:,}")
c3.metric(" Avg Invoice",       f"£{avg_inv:,.0f}")
c4.metric(" High Risk",         f"{high_risk}")
c5.metric(" Overdue",           f"{overdue_n}")
c6.metric(" Paid Rate",         f"{paid_pct:.1f}%")

st.markdown("---")

# ── TABS ─────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " Spend Trends",
    " Vendor Analysis",
    " Risk Analysis",
    " Categories",
    " Transactions"
])

# ── TAB 1: SPEND TRENDS ──────────────────────
with tab1:
    st.subheader("Monthly Net Spend Trend")

    if len(inv_pos) > 0:
        monthly = (inv_pos.groupby(
            inv_pos['InvoiceDate'].dt.to_period('M').astype(str)
        )['NetAmount'].sum().reset_index())
        monthly.columns = ['Month', 'Spend']
        monthly = monthly.sort_values('Month')
        monthly['MA3'] = monthly['Spend'].rolling(3, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly['Month'], y=monthly['Spend']/1000,
            fill='tozeroy', name='Monthly Spend',
            line=dict(color='#0066cc', width=2),
            fillcolor='rgba(0,102,204,0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=monthly['Month'], y=monthly['MA3']/1000,
            name='3-Month Moving Avg',
            line=dict(color='#cc3300', width=2, dash='dash')
        ))
        fig.update_layout(
            yaxis_title='£ Thousands',
            xaxis_title='Month',
            hovermode='x unified',
            height=380
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Fiscal Year")
        fy_data = inv_pos.groupby('FiscalYear')['NetAmount'].sum().reset_index()
        fig2 = px.bar(fy_data, x='FiscalYear', y='NetAmount',
        labels={'NetAmount': '£ Net Spend', 'FiscalYear': 'Fiscal Year'},
        color_discrete_sequence=['#0066cc'])
        fig2.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Payment Status Breakdown")
        status_data = filtered['PaymentStatus'].value_counts().reset_index()
        status_data.columns = ['Status', 'Count']
        fig3 = px.pie(status_data, values='Count', names='Status',
        color_discrete_sequence=['#28a745','#ffc107','#dc3545'])
        fig3.update_layout(height=300)
        st.plotly_chart(fig3, use_container_width=True)

# ── TAB 2: VENDOR ANALYSIS ───────────────────
with tab2:
    st.subheader("Top 15 Vendors by Net Spend")

    vendor_data = (inv_pos.groupby('SupplierName')['NetAmount']
                .sum().sort_values(ascending=False).head(15).reset_index())
    vendor_data.columns = ['Vendor', 'TotalSpend']
    vendor_data['Pct'] = (vendor_data['TotalSpend'] / vendor_data['TotalSpend'].sum() * 100).round(1)

    fig4 = px.bar(vendor_data, x='TotalSpend', y='Vendor', orientation='h',
                text=vendor_data['TotalSpend'].apply(lambda x: f'£{x/1000:.0f}K'),
                color_discrete_sequence=['#0066cc'])
    fig4.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig4, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vendor Spend Share (Top 10)")
        top10 = vendor_data.head(10)
        fig5 = px.pie(top10, values='TotalSpend', names='Vendor', hole=0.4)
        fig5.update_layout(height=350)
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.subheader("Invoice Count by Vendor")
        inv_count = (inv_pos.groupby('SupplierName').size() .sort_values(ascending=False).head(10).reset_index())
        inv_count.columns = ['Vendor', 'Count']
        fig6 = px.bar(inv_count, x='Count', y='Vendor', orientation='h', color_discrete_sequence=['#6610f2'])
        fig6.update_layout(height=350, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig6, use_container_width=True)

    st.subheader("Vendor Summary Table")
    vendor_table = (inv_pos.groupby('SupplierName').agg(
        Total_Spend=('NetAmount', 'sum'),
        Invoice_Count=('NetAmount', 'count'),
        Avg_Invoice=('NetAmount', 'mean')
    ).sort_values('Total_Spend', ascending=False).reset_index())
    vendor_table['Total_Spend']   = vendor_table['Total_Spend'].apply(lambda x: f"£{x:,.0f}")
    vendor_table['Avg_Invoice']   = vendor_table['Avg_Invoice'].apply(lambda x: f"£{x:,.0f}")
    st.dataframe(vendor_table, use_container_width=True, hide_index=True)

# ── TAB 3: RISK ANALYSIS ─────────────────────
with tab3:
    st.subheader("Risk Distribution Overview")

    r1, r2, r3 = st.columns(3)
    high_n   = (filtered['RiskLevel'] == 'High').sum()
    medium_n = (filtered['RiskLevel'] == 'Medium').sum()
    low_n    = (filtered['RiskLevel'] == 'Low').sum()
    r1.metric("High Risk",   high_n)
    r2.metric(" Medium Risk", medium_n)
    r3.metric(" Low Risk",    low_n)

    col1, col2 = st.columns(2)

    with col1:
        risk_data = filtered['RiskLevel'].value_counts().reset_index()
        risk_data.columns = ['Risk', 'Count']
        fig7 = px.pie(risk_data, values='Count', names='Risk', hole=0.5, color='Risk',color_discrete_map={'High':'#dc3545','Medium':'#ffc107','Low':'#28a745'})
        fig7.update_layout(title='Risk Level Distribution', height=350)
        st.plotly_chart(fig7, use_container_width=True)

    with col2:
        overdue_data = filtered[filtered['PaymentStatus'] == 'Overdue'].copy()
        if len(overdue_data) > 0:
            overdue_data['Month'] = overdue_data['InvoiceDate'].dt.strftime('%Y-%m')
            od_monthly = overdue_data.groupby('Month')['NetAmount'].sum().abs().reset_index()
            fig8 = px.bar(od_monthly, x='Month', y='NetAmount',labels={'NetAmount': '£ Overdue', 'Month': 'Month'},color_discrete_sequence=['#dc3545'])
            fig8.update_layout(title='Overdue Amount by Month', height=350)
            st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("No overdue invoices in current filter.")

    st.subheader("High-Risk Transaction Records")
    high_risk_df = filtered[filtered['RiskLevel'] == 'High'].sort_values(
        'NetAmount', ascending=False
    )[['TransactionID','InvoiceDate','SupplierName','Department','NetAmount','PaymentStatus','RiskLevel']].copy()
    high_risk_df['NetAmount'] = high_risk_df['NetAmount'].apply(lambda x: f"£{x:,.2f}")
    high_risk_df['InvoiceDate'] = high_risk_df['InvoiceDate'].dt.strftime('%Y-%m-%d')
    st.dataframe(high_risk_df, use_container_width=True, hide_index=True)

# ── TAB 4: CATEGORIES ────────────────────────
with tab4:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Expense Category")
        cat_data = inv_pos.groupby('ExpenseCategory')['NetAmount'].sum().reset_index()
        fig9 = px.pie(cat_data, values='NetAmount', names='ExpenseCategory',color_discrete_sequence=['#0066cc','#6610f2','#28a745'])
        fig9.update_layout(height=320)
        st.plotly_chart(fig9, use_container_width=True)

    with col2:
        st.subheader("Top 10 Expense Types")
        etype_data = (inv_pos.groupby('ExpenseType')['NetAmount'].sum().sort_values(ascending=False).head(10).reset_index())
        fig10 = px.bar(etype_data, x='NetAmount', y='ExpenseType', orientation='h',color_discrete_sequence=['#0066cc'])
        fig10.update_layout(height=320, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig10, use_container_width=True)

    st.subheader("Department Spend Ranking")
    dept_data = (inv_pos.groupby('Department')['NetAmount'].sum().sort_values(ascending=False).reset_index())
    dept_data['NetAmount_K'] = (dept_data['NetAmount'] / 1000).round(1)
    fig11 = px.bar(dept_data, x='Department', y='NetAmount_K',labels={'NetAmount_K': '£ Thousands', 'Department': ''},color_discrete_sequence=['#0066cc'])
    fig11.update_layout(height=350, xaxis_tickangle=-30)
    st.plotly_chart(fig11, use_container_width=True)

# ── TAB 5: TRANSACTIONS ──────────────────────
with tab5:
    st.subheader(f"Transaction Explorer — {len(filtered):,} records")

    search = st.text_input("🔍 Search by vendor name, transaction ID, or department")

    display_df = filtered.copy()
    if search:
        mask = (
            display_df['SupplierName'].str.contains(search, case=False, na=False) |
            display_df['TransactionID'].str.contains(search, case=False, na=False) |
            display_df['Department'].str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]

    show_cols = ['TransactionID','InvoiceDate','SupplierName','Department','ExpenseCategory','NetAmount','PaymentStatus','RiskLevel','FiscalYear']
    display_df = display_df[show_cols].copy()
    display_df['InvoiceDate'] = display_df['InvoiceDate'].dt.strftime('%Y-%m-%d')
    display_df['NetAmount']   = display_df['NetAmount'].apply(lambda x: f"£{x:,.2f}")

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

    csv = filtered.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Filtered Data as CSV",
        data=csv,
        file_name="filtered_financial_data.csv",
        mime="text/csv"
    )

# ── Footer ───────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#999;font-size:12px'>"
    "Financial Intelligence Dashboard · Unified Financial Dataset · "
    "500 transactions · 35 vendors · FY 2023/24–2024/25"
    "</div>",
    unsafe_allow_html=True
)