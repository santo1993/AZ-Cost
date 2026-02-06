"""
Savings Dashboard Page.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.api_client import api_client

st.set_page_config(page_title="Savings Dashboard", page_icon="💰", layout="wide")
st.title("💰 Savings Dashboard")

with st.spinner("Fetching usage data..."):
    subs = st.session_state.get("subscription_ids")
    
    # Fetch data
    orphaned = api_client.get_orphaned_resources(subs)
    advisor = api_client.get_advisor_recommendations(subs)
    
    all_issues = orphaned + advisor

if not all_issues:
    st.success("No critical cost issues found! 🎉")
else:
    # Convert to DataFrame
    df = pd.DataFrame(all_issues)
    
    # Overview
    total_savings = df["potential_savings"].sum()
    st.subheader(f"Total Potential Savings: :green[${total_savings:,.2f} / month]")
    
    # Sidebar Filters
    st.sidebar.markdown("### 🔍 Filters")
    
    # Issue Type Filter (Zombie, Orphaned, Advisor)
    available_types = df["issue_type"].unique().tolist()
    selected_type = st.sidebar.multiselect(
        "Issue Type",
        options=available_types,
        default=available_types,
        help="Filter by issue category (Orphaned, Zombie, Advisor)"
    )
    
    # Severity Filter
    selected_severity = st.sidebar.multiselect(
        "Severity", 
        options=df["severity"].unique().tolist(), 
        default=df["severity"].unique().tolist()
    )

    # Filter Data
    filtered_df = df[
        (df["severity"].isin(selected_severity)) & 
        (df["issue_type"].isin(selected_type))
    ]
    
    # Chart Grouping Options
    st.markdown("### 📊 Savings Analysis")
    
    col_chart_opt, col_chart = st.columns([1, 3])
    
    with col_chart_opt:
        chart_group_by = st.radio(
            "Group chart by:",
            options=["Issue Type", "Subscription", "Resource Group"],
            index=0,
            help="Choose how to group the savings chart"
        )
    
    with col_chart:
        if chart_group_by == "Issue Type":
            group_col = "issue_type"
            chart_title = "Savings by Issue Type"
        elif chart_group_by == "Subscription":
            group_col = "subscription_id"
            chart_title = "Savings by Subscription"
        else:
            group_col = "resource_group"
            chart_title = "Savings by Resource Group"
        
        if not filtered_df.empty:
            grouped = filtered_df.groupby(group_col)["potential_savings"].sum().reset_index()
            grouped = grouped.sort_values("potential_savings", ascending=False)
            
            fig = px.bar(
                grouped, 
                x=group_col, 
                y="potential_savings",
                title=chart_title,
                labels={"potential_savings": "Potential Savings ($)", group_col: chart_group_by},
                color="potential_savings",
                color_continuous_scale="Greens"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data matches the current filters.")

    st.divider()

    # Detailed Table
    st.markdown("### 📋 Detailed Recommendations")
    
    # Add search
    search = st.text_input("🔎 Search resources", placeholder="Filter by name, group, or description...")
    
    display_df = filtered_df.copy()
    if search:
        search_lower = search.lower()
        mask = (
            display_df["resource_name"].str.lower().str.contains(search_lower, na=False) |
            display_df["resource_group"].str.lower().str.contains(search_lower, na=False) |
            display_df["description"].str.lower().str.contains(search_lower, na=False)
        )
        display_df = display_df[mask]
    
    st.dataframe(
        display_df,
        column_order=["issue_type", "resource_name", "description", "potential_savings", "recommendation", "severity", "resource_group", "subscription_id"],
        column_config={
            "potential_savings": st.column_config.NumberColumn("Savings ($)", format="$%.2f"),
            "issue_type": "Category",
            "resource_name": "Resource",
            "description": "Issue",
            "recommendation": "Action",
            "severity": st.column_config.TextColumn("Severity"),
            "resource_group": "Resource Group",
            "subscription_id": "Subscription"
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Summary Stats
    st.markdown("### 📈 Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Issues", len(display_df))
    with col2:
        st.metric("Total Savings", f"${display_df['potential_savings'].sum():,.2f}")
    with col3:
        high_sev = len(display_df[display_df["severity"] == "High"]) if "High" in display_df["severity"].values else 0
        st.metric("High Severity", high_sev)
