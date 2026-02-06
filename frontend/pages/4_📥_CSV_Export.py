"""
CSV Export Page.
"""
import streamlit as st
from config import BACKEND_URL

st.set_page_config(page_title="Export Data", page_icon="📥", layout="wide")
st.title("📥 Export Data")

st.markdown("""
Here you can download the full resource inventory as a CSV file.
This export uses a streaming API, so it can handle larger datasets efficiently.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Configuration")
    subs = st.session_state.get("subscription_ids")
    
    st.info(f"Exporting for subscriptions: **{subs if subs else 'All Discovered'}**")
    
    # Construct export URL
    # Note: Streamlit buttons cannot directly trigger a browser download from a backend URL easily unless we use `st.link_button` (newer) or markdown link.
    # `st.download_button` requires data in memory.
    # For large streaming CSVs, a direct link is better to avoid loading into Streamlit server memory first.
    
    params = []
    if subs:
        params.append(f"subscription_ids={subs}")
    
    query_string = "&".join(params)
    export_url = f"{BACKEND_URL}/api/export-csv?{query_string}"
    
    st.markdown(f"""
    <a href="{export_url}" target="_blank">
        <button style="
            background-color: #0078D4;
            color: white;
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        ">
            ⬇️ Download Full Resource CSV
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    st.caption("Clicking the button will start a direct download from the backend API.")

with col2:
    st.image("https://learn.microsoft.com/en-us/azure/cost-management-billing/images/cost-management-overview/cost-management-overview.png", caption="Azure Cost Management")
