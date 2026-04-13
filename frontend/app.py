"""
Main Streamlit Application.
"""
import streamlit as st
import sys
import os
import time

# Adjust path to import services/components
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from services.api_client import api_client

# Page Config
st.set_page_config(
    page_title="Azure Cost Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'subscription_ids' not in st.session_state:
    st.session_state.subscription_ids = ""
if 'enable_underutilized_vm_check' not in st.session_state:
    st.session_state.enable_underutilized_vm_check = False

st.markdown("""
### Welcome

This dashboard helps you identify cost savings opportunities in your Azure environment.

**Key Features:**
- **Global Dashboard**: High-level cost summary and trends.
- **Savings Dashboard**: Actionable recommendations (Zombie resources, Advisor findings).
- **Resource Explorer**: Deep dive into your resources.
- **CSV Export**: Download data for offline analysis.

👈 **Select a page from the sidebar to get started.**
""")

st.info("System is running in **Active Verification Mode** connects to backend at `http://localhost:8080`")

# Sidebar Configuration
with st.sidebar:
    st.header("☁️ Azure Cost Dashboard")
    st.markdown("---")
    
    # Navigation
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_🏠_Global_Dashboard.py", label="Global Dashboard", icon="📊")
    st.page_link("pages/2_💰_Savings_Dashboard.py", label="Savings Dashboard", icon="💰")
    st.page_link("pages/3_📊_Cost_History.py", label="Cost History", icon="📈")
    
    st.markdown("---")
    
    # DATA SOURCE CONTROL
    st.subheader("Data Source")
    
    # Scan History Selector
    scans = api_client.list_scans()
    scan_options = {"Live/Cached Data": None}
    for s in scans:
        scan_id = s.get("scan_id")
        timestamp = s.get("timestamp", "").replace("T", " ")[:16]
        mode_label = "[EXP]" if s.get("mode") == "export" else "[API]"
        label = f"{mode_label} {timestamp} ({s.get('total_subscriptions')} subs)"
        scan_options[label] = scan_id
        
    selected_scan_label = st.selectbox("Select Snapshot", list(scan_options.keys()))
    selected_scan_id = scan_options[selected_scan_label]
    
    if selected_scan_id:
        st.session_state.scan_id = selected_scan_id
        st.info(f"Viewing snapshot: {selected_scan_label}")
    else:
        if 'scan_id' in st.session_state:
            del st.session_state.scan_id
    
    st.markdown("### Sync New Data")
    col1, col2 = st.columns(2)
    
    # Live Scan Button
    with col1:
        if st.button("🚀 Live API", help="Slow but fresh", use_container_width=True):
            try:
                response = api_client.start_scan(mode="live")
                if response and response.get("status") == "started":
                    st.session_state.scanning = True
                    st.session_state.scan_job_id = response.get("scan_id")
                    st.success("Started!")
                    st.rerun()
            except Exception as e:
                st.error(f"Err: {e}")

    # Export Sync Button
    with col2:
        if st.button("📦 From CSV", help="Fast (Blob Storage)", type="primary", use_container_width=True):
            try:
                response = api_client.start_scan(mode="export")
                if response and response.get("status") == "started":
                    st.session_state.scanning = True
                    st.session_state.scan_job_id = response.get("scan_id")
                    st.success("Started!")
                    st.rerun()
            except Exception as e:
                st.error(f"Err: {e}")

    # Progress Bar with Auto-Refresh
    if st.session_state.get("scanning"):
        status = api_client.get_scan_status()
        if status:
            progress = status.get("progress", 0)
            stage = status.get("current_stage", "Processing...")
            job_status = status.get("status")
            
            st.progress(progress / 100, text=f"{stage} ({progress}%)")
            
            if job_status == "completed":
                st.session_state.scanning = False
                st.success("Scan completed!")
                time.sleep(1)
                st.rerun()
            elif job_status == "failed":
                st.session_state.scanning = False
                st.error(f"Failed: {status.get('error')}")
            else:
                # Still running - auto-refresh every 2 seconds
                time.sleep(2)
                st.rerun()

    st.markdown("---")
    st.markdown("### Settings")
    
    if st.checkbox("Include Underutilized VMs (slow)", value=st.session_state.get("enable_underutilized_vm_check", False)):
        st.session_state.enable_underutilized_vm_check = True
    else:
        st.session_state.enable_underutilized_vm_check = False

    st.markdown("---")
    st.markdown("### 🗑️ Cache Management")
    
    # Show cache info
    scans = api_client.list_scans()
    scan_count = len(scans)
    
    if scan_count > 0:
        st.caption(f"📦 Stored Scans: {scan_count}")
        
        # Clear Frontend Cache
        if st.button("🧹 Clear Frontend Cache", use_container_width=True, help="Clear Streamlit session cache"):
            st.cache_data.clear()
            if "cached_cost_data" in st.session_state:
                del st.session_state.cached_cost_data
            if "cached_savings_data" in st.session_state:
                del st.session_state.cached_savings_data
            if "cached_savings_issues" in st.session_state:
                del st.session_state.cached_savings_issues
            st.success("✅ Frontend cache cleared!")
            st.rerun()
        
        # Clear Backend Cache
        if st.button("🔄 Clear Backend Cache", use_container_width=True, help="Clear backend memory cache"):
            result = api_client.clear_backend_cache()
            if result and result.get("status") == "success":
                st.success("✅ Backend cache cleared!")
            else:
                st.error("❌ Failed to clear backend cache")
        
        # Delete Old Scans
        with st.expander("🗂️ Manage Scan History"):
            keep_count = st.number_input(
                "Keep most recent scans",
                min_value=1,
                max_value=20,
                value=5,
                help="Delete older scans, keeping only this many recent ones"
            )
            
            if st.button(f"🗑️ Delete Old Scans (Keep {keep_count})", type="secondary"):
                if scan_count <= keep_count:
                    st.info(f"No cleanup needed. You have {scan_count} scans.")
                else:
                    with st.spinner("Deleting old scans..."):
                        result = api_client.cleanup_old_scans(keep_count)
                        if result and result.get("status") == "success":
                            deleted = result.get("deleted_count", 0)
                            st.success(f"✅ Deleted {deleted} old scans!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to cleanup scans")
            
            # Show scan list with delete buttons
            st.caption("Recent Scans:")
            for i, scan in enumerate(scans[:10]):
                scan_id = scan.get("scan_id")
                timestamp = scan.get("timestamp", "").replace("T", " ")[:16]
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"{i+1}. {timestamp}")
                with col2:
                    if st.button("🗑️", key=f"del_{scan_id}", help=f"Delete {scan_id}"):
                        result = api_client.delete_scan(scan_id)
                        if result and result.get("status") == "success":
                            st.success(f"Deleted!")
                            st.rerun()
                        else:
                            st.error("Failed")
    else:
        st.caption("No cached scans found.")
