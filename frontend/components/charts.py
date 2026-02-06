"""
Chart Components.
"""
import plotly.express as px
import pandas as pd
import streamlit as st
from typing import Dict, Any

def render_savings_pie_chart(savings_by_category: Dict[str, float]):
    """
    Renders a pie chart of savings by category.
    """
    if not savings_by_category:
        st.info("No savings data available to chart.")
        return

    df = pd.DataFrame(list(savings_by_category.items()), columns=["Category", "Savings"])
    
    fig = px.pie(
        df, 
        values="Savings", 
        names="Category", 
        title="Potential Savings by Category",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    st.plotly_chart(fig, use_container_width=True)

def render_cost_trend_chart(data: pd.DataFrame):
    # Placeholder for cost trend if we had time-series data
    st.info("Cost trend data not available in this view.")
