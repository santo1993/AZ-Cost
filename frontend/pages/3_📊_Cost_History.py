"""
Cost History Page - Stacked Bar Chart like AWS Cost Explorer.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.api_client import api_client, cached_get_monthly_cost_history

st.set_page_config(page_title="Cost History", page_icon="📊", layout="wide")
st.title("📊 Cost History")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Options Bar (similar to AWS Cost Explorer)
st.markdown("### Filter Options")
col1, col2, col3, col4 = st.columns(4)

with col1:
    interval = st.selectbox(
        "Interval",
        options=["Monthly"],
        index=0,
        help="Time granularity for the chart"
    )

with col2:
    months = st.slider(
        "Months",
        min_value=3,
        max_value=12,
        value=3,  # Default to 3 months for faster loading
        help="Number of months to display (more months = slower loading)"
    )

with col3:
    category = st.selectbox(
        "Category",
        options=["Service Name", "Resource Group", "Subscription"],
        index=0,
        help="How to group the cost breakdown"
    )

with col4:
    chart_type = st.selectbox(
        "Chart Type",
        options=["Stacked Bar", "Grouped Bar", "Line"],
        index=0,
        help="Visualization style"
    )

# Helper to get cached history data from scan
def get_cached_cost_history():
    """Check session state first, then try to load from scan."""
    # Check session state cache
    if "cached_cost_history" in st.session_state:
        return st.session_state.cached_cost_history, "Cached (Session)"
    
    try:
        scans = api_client.list_scans()
        if scans:
            latest = scans[0]
            scan_data = api_client.get_scan_data(latest.get("scan_id"))
            if scan_data and scan_data.get("costs"):
                costs = scan_data.get("costs", {})
                history = costs.get("history", {})
                
                if history:
                    # Transform daily history into format for display
                    # Group by month and aggregate
                    monthly_data = {}
                    for date_str, cost in history.items():
                        # Extract month (YYYY-MM format)
                        month = date_str[:7]
                        if month not in monthly_data:
                            monthly_data[month] = 0
                        monthly_data[month] += cost
                    
                    # Create data format for display
                    data = []
                    for month, total_cost in sorted(monthly_data.items()):
                        data.append({
                            "month": month,
                            "service": "All Services",
                            "cost": total_cost
                        })
                    
                    result = {
                        "months": sorted(monthly_data.keys()),
                        "services": ["All Services"],
                        "data": data
                    }
                    
                    st.session_state.cached_cost_history = result
                    return result, f"Scan: {latest.get('scan_id', '')[:8]}..."
    except Exception as e:
        st.warning(f"Could not load from scan: {e}")
    return None, None

# Fetch Data - Check scan cache first, then fallback to API
subs = st.session_state.get("subscription_ids")

with st.spinner("Loading cost history..."):
    cost_history, data_source = get_cached_cost_history()
    
    if cost_history:
        st.success(f"📦 Using cached scan data. {data_source}")
    else:
        # Fallback to live API (slower)
        st.warning("⏳ No recent scan found. Fetching live data (this may take a while)...")
        cost_history = cached_get_monthly_cost_history(subs, months=months)
    
    data = cost_history.get("data", []) if cost_history else []
    services = cost_history.get("services", []) if cost_history else []
    unique_months = cost_history.get("months", []) if cost_history else []

if not data:
    st.warning("No cost history data available. This could be because:")
    st.markdown("""
    - Cost Management API access is not enabled for these subscriptions
    - No cost data exists for the selected period
    - The API request is still processing (try refreshing)
    """)
else:
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Service filter
    st.sidebar.markdown("### 🎨 Services")
    if services:
        # Show top 10 services by default, allow user to select
        top_services = df.groupby("service")["cost"].sum().nlargest(15).index.tolist()
        selected_services = st.sidebar.multiselect(
            "Select Services",
            options=services,
            default=top_services[:10] if len(top_services) > 10 else top_services,
            help="Filter which services to display"
        )
        
        if selected_services:
            df = df[df["service"].isin(selected_services)]
    
    # Create the chart
    st.markdown("### 📈 Cost History by Months and Service Items")
    
    if not df.empty:
        # Pivot data for stacked chart
        if chart_type == "Stacked Bar":
            fig = px.bar(
                df,
                x="month",
                y="cost",
                color="service",
                title=f"Cost History ({months} Months)",
                labels={"cost": "Cost ($)", "month": "Months", "service": "Service"},
                barmode="stack"
            )
        elif chart_type == "Grouped Bar":
            fig = px.bar(
                df,
                x="month",
                y="cost",
                color="service",
                title=f"Cost History ({months} Months)",
                labels={"cost": "Cost ($)", "month": "Months", "service": "Service"},
                barmode="group"
            )
        else:  # Line
            fig = px.line(
                df,
                x="month",
                y="cost",
                color="service",
                title=f"Cost History ({months} Months)",
                labels={"cost": "Cost ($)", "month": "Months", "service": "Service"},
                markers=True
            )
        
        fig.update_layout(
            xaxis_title="Months",
            yaxis_title="Cost ($)",
            legend_title="Services",
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary Table
        st.divider()
        st.markdown("### 📋 Monthly Cost Summary")
        
        # Pivot table: months as columns, services as rows
        pivot = df.pivot_table(
            index="service",
            columns="month",
            values="cost",
            aggfunc="sum",
            fill_value=0
        )
        
        # Add total column
        pivot["Total"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("Total", ascending=False)
        
        # Format as currency
        st.dataframe(
            pivot.style.format("${:,.2f}"),
            use_container_width=True
        )
        
        # Total cost
        total = df["cost"].sum()
        st.metric("Total Cost (All Selected Services)", f"${total:,.2f}")
    else:
        st.info("No data matches the current service filter.")

# Footer
st.divider()
st.caption("Data sourced from Azure Cost Management API. Costs may have up to 24-hour delay.")
