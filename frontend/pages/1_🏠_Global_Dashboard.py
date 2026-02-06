"""
Global Dashboard Page.
"""
import streamlit as st
import pandas as pd
from services.api_client import cached_get_costs, cached_get_savings_summary, get_subscription_name_map
from components.cards import render_kpi_card, render_savings_card
from components.charts import render_savings_pie_chart

st.set_page_config(page_title="Global Dashboard", page_icon="🏠", layout="wide")

st.title("🏠 Global Dashboard")

# Refresh button
col_header_1, col_header_2 = st.columns([8, 1])
with col_header_2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Fetch Data (CACHED - will only fetch once per hour or until refresh clicked)
subs = st.session_state.get("subscription_ids")

with st.spinner("Loading data..."):
    # Fetch actual costs (last 30 days) - CACHED
    cost_data = cached_get_costs(subs, days=30)
    
    # Fetch savings recommendations - CACHED
    savings_data = cached_get_savings_summary(subs)
    
    # Calculate totals
    total_spend = cost_data.get("total", 0.0)
    total_savings = savings_data.get("total_potential_monthly_savings", 0.0)
    total_recs = savings_data.get("total_recommendations", 0)
    savings_by_cat = savings_data.get("savings_by_category", {})

# KPI Row
st.subheader("📊 Cost Overview (Last 30 Days)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    render_kpi_card(
        "Total Spend", 
        f"${total_spend:,.2f}", 
        f"{cost_data.get('period_days', 30)} days",
        color="blue"
    )

with col2:
    render_kpi_card(
        "Potential Savings", 
        f"${total_savings:,.2f}/mo", 
        f"{total_recs} recommendations",
        color="green"
    )

with col3:
    # Savings as percentage of spend
    savings_pct = (total_savings / total_spend * 100) if total_spend > 0 else 0
    render_kpi_card("Savings Opportunity", f"{savings_pct:.1f}%", "of monthly spend")

with col4:
    render_kpi_card("Active Recommendations", str(total_recs))

st.divider()

# Cost by Subscription
st.subheader("💰 Cost by Subscription")
sub_costs = cost_data.get("subscriptions", [])
if sub_costs:
    df_subs = pd.DataFrame(sub_costs)
    if not df_subs.empty and "cost" in df_subs.columns:
        # Use subscription_name from API response if available (new), fallback to lookup
        if "subscription_name" not in df_subs.columns:
            try:
                sub_name_map = get_subscription_name_map()
            except:
                sub_name_map = {}
            df_subs["subscription_name"] = df_subs["subscription_id"].apply(
                lambda x: sub_name_map.get(x, x[:8] + "...") if sub_name_map else x[:8] + "..."
            )
        
        # Show chart with subscription names
        st.bar_chart(df_subs.set_index("subscription_name")["cost"])
        
        # Show table with subscription names
        st.dataframe(
            df_subs,
            column_order=["subscription_name", "cost", "period_days"],
            column_config={
                "subscription_name": "Subscription",
                "cost": st.column_config.NumberColumn("Cost (USD)", format="$%.2f"),
                "period_days": "Days",
                "subscription_id": None  # Hide subscription ID
            },
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No cost data available.")

st.divider()

# Charts & Insights
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📈 Savings Opportunities")
    render_savings_pie_chart(savings_by_cat)

with c2:
    st.subheader("🔝 Top Insights")
    breakdown = savings_data.get("breakdown", [])
    if breakdown:
        df = pd.DataFrame(breakdown)
        if not df.empty:
            df = df.sort_values(by="potential_savings", ascending=False).head(5)
            st.dataframe(
                df[["description", "potential_savings", "issue_type", "severity"]],
                column_config={
                    "potential_savings": st.column_config.NumberColumn("Savings ($)", format="$%.2f"),
                    "issue_type": "Type",
                    "description": "Issue",
                    "severity": "Severity"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recommendations found.")
    else:
        st.info("No recommendations data available.")

# WAF Optimization Score
st.markdown("### 🎯 WAF Cost Optimization Score")
optimization_score = min(100, int((total_savings / max(total_spend, 1)) * 100))
st.progress(
    optimization_score,
    text=f"Optimization Score: {optimization_score}% (Potential savings vs spend)"
)
