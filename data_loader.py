import streamlit as st 
import pandas as pd 

def initialize_ss_data():
    if 'metricas_agosto' not in st.session_state:
        df = pd.read_csv ("Jira_Agosto - Data_Base.csv")
        st.session_state['metricas_agosto'] = df
        