# src/auth.py
import streamlit as st
from src.database import get_supabase_client # Importa do novo módulo

def render_login_page():
    """Renderiza a interface da página de login."""
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Senha", type="password", key="login_password")

    if st.button("Entrar", key="login_button"):
        if not email or not password:
            st.error("Por favor, preencha o email e a senha.")
            return

        try:
            supabase = get_supabase_client()
            user_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.success("Login realizado com sucesso!")
            # st.session_state['user_id'] = user_response.user.id # Opcional: Armazenar o ID do usuário
            st.session_state['user'] = user_response.user.email # Armazena o email
            st.rerun() # Recarrega a aplicação para o Dashboard
        except Exception as e:
            st.error(f"Erro no login: Verifique suas credenciais. Detalhes: {e}")

def handle_logout():
    """Lida com o logout do usuário."""
    if st.sidebar.button("Sair", key="logout_button_sidebar"):
        try:
            supabase = get_supabase_client()
            supabase.auth.sign_out()
            if 'user' in st.session_state:
                del st.session_state['user']
            # if 'user_id' in st.session_state: # Opcional
            #     del st.session_state['user_id']
            st.success("Logout realizado.")
            st.rerun() # Recarrega para voltar à página de login
        except Exception as e:
            st.error(f"Erro ao fazer logout: {e}")
