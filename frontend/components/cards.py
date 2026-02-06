"""
Card Components.
"""
import streamlit as st

def render_kpi_card(title: str, value: str, subtext: str = None, color: str = "blue"):
    """
    Renders a KPI card.
    Note: Streamlit metrics are standard, but custom styling can be added via CSS.
    """
    st.metric(label=title, value=value, delta=subtext)

def render_savings_card(title: str, amount: float, count: int):
    """
    Renders a savings summary card.
    """
    st.container(border=True).markdown(
        f"""
        <div style="text-align: center;">
            <h4 style="margin-bottom: 0;">{title}</h4>
            <h2 style="color: #28a745; margin: 0;">${amount:,.2f}</h2>
            <p style="color: gray; font-size: 0.8em;">{count} recommendations</p>
        </div>
        """,
        unsafe_allow_html=True
    )
