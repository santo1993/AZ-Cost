"""
Main Streamlit Application.
"""
import streamlit as st
import sys
import os

# Adjust path to import services/components
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from components.sidebar import render_sidebar

# Page Config
st.set_page_config(
    page_title="Azure Cost Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'subscription_ids' not in st.session_state:
    st.session_state.subscription_ids = ""
if 'enable_underutilized_vm_check' not in st.session_state:
    st.session_state.enable_underutilized_vm_check = False

# Sidebar
render_sidebar()

# Landing Page Content (if not navigating)
st.title("💸 Azure Cost Optimization Dashboard")

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

st.info("System is running in **Active Verification Mode** connects to backend at `http://localhost:8000`")

# Advanced Options Section
st.divider()
st.subheader("⚙️ Advanced Scan Options")

col1, col2 = st.columns([2, 3])
with col1:
    enable_vm_check = st.checkbox(
        "Enable Underutilized VM Detection",
        value=st.session_state.enable_underutilized_vm_check,
        help="When enabled, Savings Dashboard will scan ALL VMs for low CPU utilization (<5%)"
    )
    st.session_state.enable_underutilized_vm_check = enable_vm_check

with col2:
    if enable_vm_check:
        st.warning("⚠️ **VM scan enabled** - This will query Azure Monitor for each VM and may take several minutes depending on VM count. Results are cached after first scan.")
    else:
        st.info("VM utilization scan is disabled. Enable to find VMs with low CPU usage.")

