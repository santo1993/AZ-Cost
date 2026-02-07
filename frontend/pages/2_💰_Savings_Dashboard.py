"""
Savings Dashboard Page.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.api_client import api_client, cached_get_orphaned_resources, cached_get_advisor_recommendations, cached_get_underutilized_vms, get_subscription_name_map

st.set_page_config(page_title="Savings Dashboard", page_icon="💰", layout="wide")
st.title("💰 Savings Dashboard")

# Refresh button and Zombie Duration filter
col_refresh, col_zombie, col_fast = st.columns([1, 2, 2])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        # Force backend refresh to update memory cache (e.g. schema changes)
        try:
            with st.spinner("Refreshing backend data..."):
                # Get current zombie setting or default
                current_zombie = st.session_state.get("zombie_days_input", 90)
                sub_ids = st.session_state.get("subscription_ids")
                api_client.get_orphaned_resources(
                    subscription_ids=sub_ids, 
                    zombie_days=current_zombie, 
                    force_refresh=True
                )
        except Exception as e:
            st.warning(f"Backend refresh warning: {e}")
            
        # Clear Streamlit cache and rerun
        st.cache_data.clear()
        st.rerun()

with col_zombie:
    zombie_days = st.selectbox(
        "Zombie Duration Threshold",
        options=[0, 30, 60, 90, 180, 365],
        index=3,  # Default to 90 days (0, 30, 60, 90 is index 3)
        help="Resources inactive longer than this threshold are flagged as zombies",
        format_func=lambda x: "All (Show all)" if x == 0 else f"{x} days",
        key="zombie_days_input"
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

# Helper to load scan data
def get_cached_savings_data(zombie_days: int = 90):
    """Check session state first, then try to load from scan.
    Filters Old Snapshots by the zombie_days threshold.
    """
    def filter_by_zombie_days(issues, threshold):
        """Filter resources by days_inactive threshold."""
        filtered = []
        for issue in issues:
            # Filter Old Snapshots and Orphaned Disks
            # Both now return 'days_inactive' from backend
            if issue.get("issue_type") in ["Old Snapshot", "Orphaned Disk"]:
                # If threshold is 0 ("Show All"), include everything
                if threshold == 0:
                    filtered.append(issue)
                else:
                    days = issue.get("days_inactive")
                    # Include if days_inactive is None (unknown) or >= threshold
                    if days is None or days >= threshold:
                        filtered.append(issue)
            else:
                # Other issue types are always included
                filtered.append(issue)
        return filtered
    
    # Check session state cache
    if "cached_savings_issues" in st.session_state:
        last_zombie_days = st.session_state.get("last_zombie_days", 90)
        
        # If we have data for X days, we can answer queries for Y days where Y >= X
        # But if user wants Y < X (e.g. 30 days but cache has 90), we need more data -> Invalid
        if zombie_days < last_zombie_days:
            # Cache is insufficient
            return None, None
            
        # Apply zombie_days filter to cached data
        issues = filter_by_zombie_days(st.session_state.cached_savings_issues, zombie_days)
        return issues, "Cached (Session)"
    
    try:
        scans = api_client.list_scans()
        if scans:
            latest = scans[0]
            scan_data = api_client.get_scan_data(latest.get("scan_id"))
            if scan_data:
                orphaned = scan_data.get("orphaned", [])
                advisor = scan_data.get("advisor", [])
                # Combine issues
                all_issues = orphaned + advisor
                
                # Check metadata if available, otherwise assume default 30
                scan_zombie_days = scan_data.get("metadata", {}).get("zombie_days", 30)
                
                # Cache UNFILTERED data in session state
                st.session_state.cached_savings_issues = all_issues
                st.session_state.last_zombie_days = scan_zombie_days
                
                # If scan data covers the request
                if zombie_days >= scan_zombie_days:
                    filtered_issues = filter_by_zombie_days(all_issues, zombie_days)
                    return filtered_issues, f"Scan: {latest.get('scan_id', '')[:8]}..."
                else:
                    # Scan data insufficient
                    return None, None
    except Exception as e:
        st.warning(f"Could not load from scan: {e}")
    return None, None

# Show progress during load
with st.spinner("Loading savings data..."):
    all_issues, data_source = get_cached_savings_data(zombie_days=zombie_days)
    
    if all_issues is not None:
        st.success(f"📦 Using cached scan data. {data_source}")
    else:
        # Fallback to live API (slower)
        st.warning("⏳ No recent scan found. Fetching live data (this may take 30-60 seconds)...")
        orphaned = cached_get_orphaned_resources(subs, zombie_days=zombie_days, include_costs=include_costs)
        advisor = cached_get_advisor_recommendations(subs)
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
        
    # Ensure days_inactive column exists
    if "days_inactive" not in df.columns:
        df["days_inactive"] = None
    
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
    
    # Cost by Issue Type Table
    st.markdown("### 💵 Cost by Issue Type")
    
    if not filtered_df.empty:
        # Group by issue type and calculate sum and count
        issue_summary = filtered_df.groupby("issue_type").agg({
            "potential_savings": "sum",
            "resource_name": "count"
        }).reset_index()
        issue_summary.columns = ["Issue Type", "Total Savings ($)", "Count"]
        issue_summary = issue_summary.sort_values("Total Savings ($)", ascending=False)
        
        # Add percentage column
        total = issue_summary["Total Savings ($)"].sum()
        issue_summary["% of Total"] = (issue_summary["Total Savings ($)"] / total * 100).round(1)
        
        st.dataframe(
            issue_summary,
            column_config={
                "Issue Type": st.column_config.TextColumn("Issue Type", width="medium"),
                "Total Savings ($)": st.column_config.NumberColumn("Total Cost ($)", format="$%.2f"),
                "Count": st.column_config.NumberColumn("# of Issues", format="%d"),
                "% of Total": st.column_config.NumberColumn("% of Total", format="%.1f%%")
            },
            use_container_width=True,
            hide_index=True
        )
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
        column_order=["issue_type", "resource_name", "description", "days_inactive", "potential_savings", "recommendation", "severity", "resource_group", "subscription_name"],
        column_config={
            "potential_savings": st.column_config.NumberColumn("Last Month Cost ($)", format="$%.2f"),
            "issue_type": "Category",
            "resource_name": "Resource",
            "description": "Issue",
            "days_inactive": st.column_config.NumberColumn("Days Inactive", format="%d"),
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
