# app.py
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

from src.auth import render_login_page, handle_logout
from src.product_manager import render_product_management_section
from src.stock_manager import render_stock_summary_section, render_detailed_movements_section
from src.shipment_manager import render_shipment_management_section # Apenas confirmar que está aqui

st.set_page_config(
    page_title="Sistema de Estoque",
    page_icon="📦",
    layout="wide"
)

st.title("Sistema de Gerenciamento de Estoque")

if 'user' not in st.session_state:
    render_login_page()
else:
    st.sidebar.markdown(f"**Usuário:** {st.session_state['user']}")
    handle_logout()

    st.subheader("Painel de Controle")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Resumo de Estoque",
        "Movimentos Detalhados",
        "Remessas",
        "Gerenciar Produtos"
    ])

    with tab1:
        render_stock_summary_section()

    with tab2:
        render_detailed_movements_section()

    with tab3: # Esta aba chama a nova função de renderização do shipment_manager
        render_shipment_management_section()

    with tab4:
        render_product_management_section()
