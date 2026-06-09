# ─────────────────────────────────────────────
# app.py — Financial Intelligence Dashboard
# Versions: streamlit==1.58.0 | pandas==3.0.3
#           numpy==2.4.0      | plotly==6.8.0
# ─────────────────────────────────────────────

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
    .block-container { padding-top: 1rem; }
    .stMetric {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("unified_financial_dataset.csv")

    # pandas 3.0.3 compatible datetime parsing
    df['InvoiceDate'] = pd.to_datetime(
        df['InvoiceDate'], errors='coerce'
    )
    df['DueDate'] = pd.to_datetime(
        df['DueDate'], errors='coerce'
    )
    df['PaymentDate'] = pd.to_datetime(
        df['PaymentDate'], errors='coerce'
    )

    # numpy 2.4.0 compatible numeric conversion
    df['NetAmount']   = pd.to_numeric(df['NetAmount'],   errors='coerce')
    df['GrossAmount'] = pd.to_numeric(df['GrossAmount'], errors='coerce')
    df['VATAmount']   = pd.to_numeric(df['VATAmount'],   errors='coerce')

    # Risk level flag
    if 'RiskLevel' not in df.columns:
        p99 = float(np.percentile(
            df['NetAmount'].dropna().values, 99
        ))
        df['RiskLevel'] = 'Low'
        df.loc[df['NetAmount'] >= p99, 'RiskLevel'] = 'High'
        df.loc[
            df['NetAmount'].apply(
                lambda x: x % 500 == 0 or x % 1000 == 0
                if pd.notna(x) else False
            ),
            'RiskLevel'
        ] = 'Medium'

    return df

df = load_data()

# ── SIDEBAR ───────────────────────────────────
st.sidebar.title("📊 Dashboard Filters")
st.sidebar.markdown("---")

# Date filter
st.sidebar.subheader("📅 Date Range")
min_date = df['InvoiceDate'].min().date()
max_date = df['InvoiceDate'].max().date()
date_from = st.sidebar.date_input(
    "From", value=min_date,
    min_value=min_date, max_value=max_date
)
date_to = st.sidebar.date_input(
    "To", value=max_date,
    min_value=min_date, max_value=max_date
)

# Vendor filter
st.sidebar.subheader("🏢 Vendor")
vendors = ["All Vendors"] + sorted(
    df['SupplierName'].dropna().unique().tolist()
)
selected_vendor = st.sidebar.selectbox("Select Vendor", vendors)

# Category filter
st.sidebar.subheader("🗂️ Category")
categories = ["All Categories"] + sorted(
    df['ExpenseCategory'].dropna().unique().tolist()
)
selected_cat = st.sidebar.selectbox("Select Category", categories)

# Status filter
st.sidebar.subheader("💳 Payment Status")
selected_status = st.sidebar.selectbox(
    "Select Status",
    ["All", "Paid", "Pending", "Overdue"]
)

# Risk filter
st.sidebar.subheader("⚠️ Risk Level")
selected_risk = st.sidebar.selectbox(
    "Select Risk Level",
    ["All", "High", "Medium", "Low"]
)

# Fiscal year filter
st.sidebar.subheader("📅 Fiscal Year")
fiscal_years = ["All"] + sorted(
    df['FiscalYear'].dropna().unique().tolist()
)
selected_fy = st.sidebar.selectbox("Fiscal Year", fiscal_years)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset All Filters"):
    st.rerun()

# ── APPLY FILTERS ────────────────────────────
filtered = df.copy()
filtered = filtered[
    (filtered['InvoiceDate'] >= pd.to_datetime(date_from)) &
    (filtered['InvoiceDate'] <= pd.to_datetime(date_to))
]
if selected_vendor != "All Vendors":
    filtered = filtered[
        filtered['SupplierName'] == selected_vendor
    ]
if selected_cat != "All Categories":
    filtered = filtered[
        filtered['ExpenseCategory'] == selected_cat
    ]
if selected_status != "All":
    filtered = filtered[
        filtered['PaymentStatus'] == selected_status
    ]
if selected_risk != "All":
    filtered = filtered[
        filtered['RiskLevel'] == selected_risk
    ]
if selected_fy != "All":
    filtered = filtered[
        filtered['FiscalYear'] == selected_fy
    ]

inv_pos = filtered[
    (filtered['TransactionType'] == 'Invoice') &
    (filtered['NetAmount'] > 0)
].copy()

# ── HEADER ────────────────────────────────────
st.title("💷 Financial Intelligence Dashboard")
st.caption(
    f"Unified Financial Dataset  ·  "
    f"{len(filtered):,} records  ·  "
    f"FY 2023/24–2024/25  ·  GBP"
)
st.divider()

# ── KPI ROW ───────────────────────────────────
total_spend = float(inv_pos['NetAmount'].sum())
avg_inv     = float(inv_pos['NetAmount'].mean()) if len(inv_pos) else 0
high_risk   = int((filtered['RiskLevel'] == 'High').sum())
overdue_n   = int((filtered['PaymentStatus'] == 'Overdue').sum())
paid_n      = int((filtered['PaymentStatus'] == 'Paid').sum())
pending_n   = int((filtered['PaymentStatus'] == 'Pending').sum())
paid_pct    = paid_n / max(len(filtered), 1) * 100
overdue_amt = float(
    filtered[filtered['PaymentStatus'] == 'Overdue']['NetAmount']
    .abs().sum()
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("💷 Total Spend",    f"£{total_spend/1e6:.2f}M")
c2.metric("📄 Transactions",   f"{len(filtered):,}")
c3.metric("📊 Avg Invoice",    f"£{avg_inv:,.0f}")
c4.metric("🚨 High Risk",      f"{high_risk}")
c5.metric("⏰ Overdue",        f"{overdue_n}")
c6.metric("✅ Paid Rate",      f"{paid_pct:.1f}%")

st.divider()

# ── TABS ──────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Spend Trends",
    "🏢 Vendor Analysis",
    "⚠️ Risk Analysis",
    "🗂️ Categories",
    "📋 Transactions"
])

# ══════════════════════════════════════════════
# TAB 1 — SPEND TRENDS
# ══════════════════════════════════════════════
with tab1:
    st.subheader("Monthly Net Spend Trend")

    if len(inv_pos) > 0:
        # pandas 3.0.3 compatible groupby
        monthly = (
            inv_pos
            .assign(Month=inv_pos['InvoiceDate'].dt.to_period('M')
                    .astype(str))
            .groupby('Month', as_index=False)['NetAmount']
            .sum()
            .sort_values('Month')
        )
        monthly['MA3'] = (
            monthly['NetAmount']
            .rolling(3, min_periods=1)
            .mean()
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly['Month'],
            y=monthly['NetAmount'] / 1000,
            fill='tozeroy',
            name='Monthly Spend',
            line=dict(color='#0066cc', width=2),
            fillcolor='rgba(0,102,204,0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=monthly['Month'],
            y=monthly['MA3'] / 1000,
            name='3-Month Moving Avg',
            line=dict(color='#cc3300', width=2, dash='dash')
        ))
        fig.update_layout(
            yaxis_title='£ Thousands',
            xaxis_title='Month',
            hovermode='x unified',
            height=380,
            legend=dict(
                orientation='h',
                yanchor='bottom', y=1.02,
                xanchor='right',  x=1
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Fiscal Year")
        if len(inv_pos) > 0:
            fy_data = (
                inv_pos
                .groupby('FiscalYear', as_index=False)['NetAmount']
                .sum()
            )
            fig2 = px.bar(
                fy_data, x='FiscalYear', y='NetAmount',
                labels={
                    'NetAmount': '£ Net Spend',
                    'FiscalYear': 'Fiscal Year'
                },
                color_discrete_sequence=['#0066cc'],
                text_auto=True
            )
            fig2.update_layout(height=320, showlegend=False)
            fig2.update_traces(
                texttemplate='£%{y:,.0f}',
                textposition='outside'
            )
            st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Payment Status Breakdown")
        status_data = (
            filtered['PaymentStatus']
            .value_counts()
            .reset_index()
        )
        status_data.columns = ['Status', 'Count']
        fig3 = px.pie(
            status_data,
            values='Count',
            names='Status',
            hole=0.45,
            color='Status',
            color_discrete_map={
                'Paid':    '#28a745',
                'Pending': '#ffc107',
                'Overdue': '#dc3545'
            }
        )
        fig3.update_layout(height=320)
        st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 — VENDOR ANALYSIS
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Top 15 Vendors by Net Spend")

    if len(inv_pos) > 0:
        vendor_data = (
            inv_pos
            .groupby('SupplierName', as_index=False)['NetAmount']
            .sum()
            .sort_values('NetAmount', ascending=False)
            .head(15)
        )
        vendor_data['Pct'] = (
            vendor_data['NetAmount'] /
            vendor_data['NetAmount'].sum() * 100
        ).round(1)

        fig4 = px.bar(
            vendor_data,
            x='NetAmount', y='SupplierName',
            orientation='h',
            text=vendor_data['NetAmount'].apply(
                lambda x: f'£{x/1000:.0f}K'
            ),
            color_discrete_sequence=['#0066cc']
        )
        fig4.update_layout(
            height=520,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title='£ Net Spend',
            yaxis_title='',
            showlegend=False
        )
        fig4.update_traces(textposition='outside')
        st.plotly_chart(fig4, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Vendor Spend Share (Top 10)")
        if len(inv_pos) > 0:
            top10 = vendor_data.head(10)
            fig5 = px.pie(
                top10,
                values='NetAmount',
                names='SupplierName',
                hole=0.4
            )
            fig5.update_layout(height=360)
            fig5.update_traces(
                textposition='inside',
                textinfo='percent'
            )
            st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.subheader("Invoice Count per Vendor (Top 10)")
        if len(inv_pos) > 0:
            inv_count = (
                inv_pos
                .groupby('SupplierName', as_index=False)
                .size()
                .rename(columns={'size': 'Count'})
                .sort_values('Count', ascending=False)
                .head(10)
            )
            fig6 = px.bar(
                inv_count,
                x='Count', y='SupplierName',
                orientation='h',
                color_discrete_sequence=['#6610f2']
            )
            fig6.update_layout(
                height=360,
                yaxis={'categoryorder': 'total ascending'},
                yaxis_title=''
            )
            st.plotly_chart(fig6, use_container_width=True)

    st.subheader("Full Vendor Summary Table")
    if len(inv_pos) > 0:
        vendor_table = (
            inv_pos
            .groupby('SupplierName', as_index=False)
            .agg(
                Total_Spend=('NetAmount', 'sum'),
                Invoice_Count=('NetAmount', 'count'),
                Avg_Invoice=('NetAmount', 'mean')
            )
            .sort_values('Total_Spend', ascending=False)
        )
        vendor_table['Total_Spend'] = vendor_table[
            'Total_Spend'
        ].apply(lambda x: f"£{x:,.0f}")
        vendor_table['Avg_Invoice'] = vendor_table[
            'Avg_Invoice'
        ].apply(lambda x: f"£{x:,.0f}")
        st.dataframe(
            vendor_table,
            use_container_width=True,
            hide_index=True
        )

# ══════════════════════════════════════════════
# TAB 3 — RISK ANALYSIS
# ══════════════════════════════════════════════
with tab3:
    st.subheader("Risk Overview")

    high_n   = int((filtered['RiskLevel'] == 'High').sum())
    medium_n = int((filtered['RiskLevel'] == 'Medium').sum())
    low_n    = int((filtered['RiskLevel'] == 'Low').sum())

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("🔴 High Risk",    high_n)
    r2.metric("🟡 Medium Risk",  medium_n)
    r3.metric("🟢 Low Risk",     low_n)
    r4.metric("💸 Overdue Amt",  f"£{overdue_amt/1e3:.0f}K")

    col1, col2 = st.columns(2)

    with col1:
        risk_data = (
            filtered['RiskLevel']
            .value_counts()
            .reset_index()
        )
        risk_data.columns = ['Risk', 'Count']
        fig7 = px.pie(
            risk_data,
            values='Count',
            names='Risk',
            hole=0.5,
            color='Risk',
            color_discrete_map={
                'High':   '#dc3545',
                'Medium': '#ffc107',
                'Low':    '#28a745'
            },
            title='Risk Level Distribution'
        )
        fig7.update_layout(height=360)
        st.plotly_chart(fig7, use_container_width=True)

    with col2:
        overdue_df = filtered[
            filtered['PaymentStatus'] == 'Overdue'
        ].copy()
        if len(overdue_df) > 0:
            overdue_df['Month'] = (
                overdue_df['InvoiceDate']
                .dt.strftime('%Y-%m')
            )
            od_monthly = (
                overdue_df
                .groupby('Month', as_index=False)['NetAmount']
                .sum()
                .assign(NetAmount=lambda x: x['NetAmount'].abs())
                .sort_values('Month')
            )
            fig8 = px.bar(
                od_monthly,
                x='Month', y='NetAmount',
                labels={
                    'NetAmount': '£ Overdue',
                    'Month': 'Month'
                },
                color_discrete_sequence=['#dc3545'],
                title='Overdue Amount by Month'
            )
            fig8.update_layout(height=360)
            st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("No overdue invoices in current filter.")

    st.subheader("High-Risk Transaction Records")
    high_risk_df = (
        filtered[filtered['RiskLevel'] == 'High']
        .sort_values('NetAmount', ascending=False)
        [[
            'TransactionID', 'InvoiceDate', 'SupplierName',
            'Department', 'NetAmount', 'PaymentStatus',
            'RiskLevel'
        ]]
        .copy()
    )
    high_risk_df['NetAmount'] = high_risk_df['NetAmount'].apply(
        lambda x: f"£{x:,.2f}"
    )
    high_risk_df['InvoiceDate'] = (
        high_risk_df['InvoiceDate'].dt.strftime('%Y-%m-%d')
    )
    st.dataframe(
        high_risk_df,
        use_container_width=True,
        hide_index=True
    )

# ══════════════════════════════════════════════
# TAB 4 — CATEGORIES
# ══════════════════════════════════════════════
with tab4:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spend by Expense Category")
        if len(inv_pos) > 0:
            cat_data = (
                inv_pos
                .groupby('ExpenseCategory', as_index=False)
                ['NetAmount'].sum()
            )
            fig9 = px.pie(
                cat_data,
                values='NetAmount',
                names='ExpenseCategory',
                color_discrete_sequence=[
                    '#0066cc', '#6610f2', '#28a745'
                ]
            )
            fig9.update_layout(height=340)
            st.plotly_chart(fig9, use_container_width=True)

    with col2:
        st.subheader("Top 10 Expense Types")
        if len(inv_pos) > 0:
            etype_data = (
                inv_pos
                .groupby('ExpenseType', as_index=False)
                ['NetAmount'].sum()
                .sort_values('NetAmount', ascending=False)
                .head(10)
            )
            fig10 = px.bar(
                etype_data,
                x='NetAmount', y='ExpenseType',
                orientation='h',
                color_discrete_sequence=['#0066cc']
            )
            fig10.update_layout(
                height=340,
                yaxis={'categoryorder': 'total ascending'},
                yaxis_title=''
            )
            st.plotly_chart(fig10, use_container_width=True)

    st.subheader("Department Spend Ranking")
    if len(inv_pos) > 0:
        dept_data = (
            inv_pos
            .groupby('Department', as_index=False)
            ['NetAmount'].sum()
            .sort_values('NetAmount', ascending=False)
        )
        dept_data['NetAmount_K'] = (
            dept_data['NetAmount'] / 1000
        ).round(1)
        fig11 = px.bar(
            dept_data,
            x='Department', y='NetAmount_K',
            labels={
                'NetAmount_K': '£ Thousands',
                'Department': ''
            },
            color_discrete_sequence=['#0066cc']
        )
        fig11.update_layout(
            height=380,
            xaxis_tickangle=-30
        )
        st.plotly_chart(fig11, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 5 — TRANSACTIONS
# ══════════════════════════════════════════════
with tab5:
    st.subheader(f"Transaction Explorer — {len(filtered):,} records")

    search = st.text_input(
        "🔍 Search by vendor, transaction ID, or department"
    )

    display_df = filtered.copy()
    if search:
        mask = (
            display_df['SupplierName']
            .str.contains(search, case=False, na=False) |
            display_df['TransactionID']
            .str.contains(search, case=False, na=False) |
            display_df['Department']
            .str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]

    show_cols = [
        'TransactionID', 'InvoiceDate', 'SupplierName',
        'Department', 'ExpenseCategory', 'NetAmount',
        'PaymentStatus', 'RiskLevel', 'FiscalYear'
    ]
    display_df = display_df[show_cols].copy()
    display_df['InvoiceDate'] = (
        display_df['InvoiceDate'].dt.strftime('%Y-%m-%d')
    )
    display_df['NetAmount'] = display_df['NetAmount'].apply(
        lambda x: f"£{x:,.2f}"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    csv_data = filtered.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_financial_data.csv",
        mime="text/csv"
    )

# ── FOOTER ────────────────────────────────────
st.divider()
st.caption(
    "Financial Intelligence Dashboard  ·  "
    "Unified Financial Dataset  ·  "
    "500 transactions  ·  35 vendors  ·  "
    "FY 2023/24–2024/25"
)
