"""
Resource Explorer Page.
"""
import streamlit as st
import pandas as pd
from services.api_client import api_client

st.set_page_config(page_title="Resource Explorer", page_icon="🔍", layout="wide")
st.title("🔍 Resource Explorer")

# Controls
col1, col2 = st.columns([2, 1])
with col1:
    search_term = st.text_input("Search (Name, Type, Group)", placeholder="Enter resource name...")
with col2:
    limit = st.select_slider("Row Limit", options=[100, 500, 1000, 5000], value=1000)

with st.spinner("Loading resources..."):
    subs = st.session_state.get("subscription_ids")
    resources = api_client.get_resources(subs, limit=limit)

if resources:
    df = pd.DataFrame(resources)
    
    # Client-side filtering (for responsiveness)
    if search_term:
        term = search_term.lower()
        mask = (
            df["name"].str.lower().str.contains(term, na=False) |
            df["resource_group"].str.lower().str.contains(term, na=False) |
            df["type"].str.lower().str.contains(term, na=False)
        )
        df = df[mask]

    st.write(f"Showing {len(df)} resources:")

    # Detailed Table
    st.dataframe(
        df,
        column_order=["name", "type", "resource_group", "location", "subscription_id", "tags"],
        column_config={
            "name": "Resource Name",
            "type": "Type",
            "resource_group": "Resource Group",
            "location": "Region",
            "subscription_id": "Subscription",
            "tags": "Tags"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No resources found or backend failed to return data.")
