"""
Savings Dashboard Page.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.api_client import cached_get_orphaned_resources, cached_get_advisor_recommendations, cached_get_underutilized_vms, get_subscription_name_map

st.set_page_config(page_title="Savings Dashboard", page_icon="💰", layout="wide")
st.title("💰 Savings Dashboard")

# Refresh button and Zombie Duration filter
col_refresh, col_zombie, col_fast = st.columns([1, 2, 2])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

with col_zombie:
    zombie_days = st.selectbox(
        "Zombie Duration Threshold",
        options=[30, 60, 90, 180, 365],
        index=2,  # Default to 90 days
        help="Resources inactive longer than this threshold are flagged as zombies",
        format_func=lambda x: f"{x} days"
    )

with col_fast:
    include_costs = st.checkbox(
        "Include Actual Costs (slower)",
        value=True,
        help="Uncheck for faster loading with estimated costs only"
    )

# Get underutilized VM setting from session state (set in main app)
include_underutilized_vms = st.session_state.get("enable_underutilized_vm_check", False)

subs = st.session_state.get("subscription_ids")

# Show progress during load
progress_text = "Loading resources..."
if include_costs:
    progress_text = "Loading resources and fetching costs (this may take 30-60 seconds)..."
if include_underutilized_vms:
    progress_text = "Loading all data including VM metrics (this may take several minutes)..."

with st.spinner(progress_text):
    # Fetch data - CACHED
    orphaned = cached_get_orphaned_resources(subs, zombie_days=zombie_days, include_costs=include_costs)
    advisor = cached_get_advisor_recommendations(subs)
    
    # Only fetch underutilized VMs if enabled in main app settings
    underutilized = cached_get_underutilized_vms(subs) if include_underutilized_vms else []
    
    all_issues = orphaned + advisor + underutilized

# Show indicator if VM check is enabled
if include_underutilized_vms:
    st.info("🔍 Underutilized VM detection is enabled (configured in Home page)")


if not all_issues:
    st.success("No critical cost issues found! 🎉")
else:
    # Convert to DataFrame
    df = pd.DataFrame(all_issues)
    
    # Use subscription_name from API if available, fallback to lookup
    if "subscription_name" not in df.columns or df["subscription_name"].isna().all():
        try:
            sub_name_map = get_subscription_name_map()
        except:
            sub_name_map = {}
        df["subscription_name"] = df["subscription_id"].apply(
            lambda x: sub_name_map.get(x, x[:8] + "...") if sub_name_map else x[:8] + "..."
        )
    
    # Overview
    total_savings = df["potential_savings"].sum()
    st.subheader(f"Total Potential Savings: :green[${total_savings:,.2f} / month]")
    
    # Sidebar Filters
    st.sidebar.markdown("### 🔍 Filters")
    
    # Resource Category Filter (specific types)
    category_options = ["Orphaned Disk", "Unattached Public IP", "Old Snapshot", "Deallocated VM", "Idle Load Balancer", "Underutilized VM", "Advisor"]
    available_categories = [c for c in category_options if c in df["issue_type"].unique().tolist()]
    # Also include any other categories found in data
    for cat in df["issue_type"].unique().tolist():
        if cat not in available_categories:
            available_categories.append(cat)
    
    selected_categories = st.sidebar.multiselect(
        "Resource Category",
        options=available_categories,
        default=available_categories,
        help="Filter by resource type"
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
        (df["issue_type"].isin(selected_categories))
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
            group_col = "subscription_name"
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
        column_order=["issue_type", "resource_name", "description", "potential_savings", "recommendation", "severity", "resource_group", "subscription_name"],
        column_config={
            "potential_savings": st.column_config.NumberColumn("Last Month Cost ($)", format="$%.2f"),
            "issue_type": "Category",
            "resource_name": "Resource",
            "description": "Issue",
            "recommendation": "Action",
            "severity": st.column_config.TextColumn("Severity"),
            "resource_group": "Resource Group",
            "subscription_name": "Subscription"
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
        st.metric("Total Cost (Last Month)", f"${display_df['potential_savings'].sum():,.2f}")
    with col3:
        high_sev = len(display_df[display_df["severity"] == "High"]) if "High" in display_df["severity"].values else 0
        st.metric("High Severity", high_sev)
    
    # Download Options
    st.divider()
    st.markdown("### 📥 Download Report")
    
    # Prepare export DataFrame with renamed columns (includes both subscription name and ID)
    export_df = display_df[["issue_type", "resource_name", "description", "potential_savings", "recommendation", "severity", "resource_group", "subscription_name", "subscription_id", "resource_id"]].copy()
    export_df.columns = ["Category", "Resource Name", "Issue", "Last Month Cost ($)", "Recommendation", "Severity", "Resource Group", "Subscription Name", "Subscription ID", "Resource ID"]
    
    col_csv, col_excel = st.columns(2)
    
    with col_csv:
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            label="📄 Download CSV",
            data=csv_data,
            file_name="azure_savings_report.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_excel:
        # Excel export
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Savings Report', index=False)
        excel_data = buffer.getvalue()
        
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name="azure_savings_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
