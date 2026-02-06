"""
Sidebar Component.
"""
import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.header("Configuration")
        
        # Subscription Filter
        st.session_state.subscription_ids = st.text_input(
            "Subscription IDs (comma-separated)",
            value=st.session_state.subscription_ids,
            placeholder="e.g., sub-guid-1, sub-guid-2",
            help="Leave empty to specific all subscriptions."
        )
        
        st.divider()
        st.markdown("### About")
        st.markdown("v1.0.0")
        st.caption("Built with FastAPI & Streamlit")
