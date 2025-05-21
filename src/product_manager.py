# src/product_manager.py
import streamlit as st
import pandas as pd
from src.database import get_supabase_client
from datetime import datetime # Para consistência com created_at

def get_products_data():
    """Busca todos os produtos cadastrados."""
    supabase = get_supabase_client()
    try:
        with st.spinner("Carregando produtos..."): # Feedback de carregamento
            response = supabase.from_('produtos').select('id, nome_produto, unidade_medida, sku, created_at').order('nome_produto').execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar produtos: {e}")
        return []

def insert_new_product(nome_produto: str, unidade_medida: str, sku: str = None):
    """Insere um novo produto no cadastro."""
    supabase = get_supabase_client()
    data = {"nome_produto": nome_produto, "unidade_medida": unidade_medida}
    if sku:
        data["sku"] = sku
    try:
        with st.spinner(f"Cadastrando produto '{nome_produto}'..."): # Feedback de carregamento
            response = supabase.from_('produtos').insert(data).execute()
        return response.data
    except Exception as e:
        # Erro mais específico para nome duplicado (UNIQUE constraint)
        if "duplicate key value violates unique constraint" in str(e):
            st.error(f"Erro: Já existe um produto com o nome '{nome_produto}' ou SKU '{sku}'.")
        else:
            st.error(f"Erro ao cadastrar produto: {e}. Por favor, tente novamente.")
        return None

def render_product_management_section():
    """Renderiza a interface para cadastro e visualização de produtos."""
    st.header("📦 Gerenciar Produtos") # Título mais visível

    tab1, tab2 = st.tabs(["Visualizar Produtos", "Cadastrar Novo Produto"])

    with tab1:
        st.subheader("Lista de Produtos Cadastrados")
        products = get_products_data()
        if products:
            df_products = pd.DataFrame(products)
            # Formatação da data de criação
            df_products['created_at'] = pd.to_datetime(df_products['created_at']).dt.strftime('%d/%m/%Y %H:%M:%S')
            df_products = df_products.rename(columns={
                'nome_produto': 'Produto',
                'unidade_medida': 'Unidade',
                'sku': 'SKU',
                'id': 'ID do Produto',
                'created_at': 'Data Cadastro'
            })
            # Selecionar colunas e ordem para melhor visualização (especialmente em mobile)
            display_columns = ['Produto', 'Unidade', 'SKU', 'Data Cadastro']
            st.dataframe(df_products[display_columns], use_container_width=True, hide_index=True)
            st.info(f"Total de produtos cadastrados: **{len(products)}**")
        else:
            st.info("Nenhum produto cadastrado ainda. Use a aba 'Cadastrar Novo Produto' para começar.")

    with tab2:
        st.subheader("Formulário de Cadastro")
        with st.form("form_cadastro_produto", clear_on_submit=True): # clear_on_submit para UX
            st.markdown("**Informações do Novo Produto**")

            nome_produto = st.text_input("Nome do Produto", help="Nome único para identificar o produto.", key="cad_nome_produto")
            unidade_medida = st.selectbox(
                "Unidade de Medida",
                ['kg', 'un', 'litro', 'metro', 'caixa', 'pacote', 'g', 'ml'], # Mais opções
                index=0, # Define um valor padrão
                help="Unidade usada para medir a quantidade do produto (ex: quilogramas, unidades).",
                key="cad_unidade_medida"
            )
            sku = st.text_input("SKU (Código do Produto - Opcional)", help="Código de identificação único para o produto (ex: código de barras).", key="cad_sku")

            st.markdown("---")
            submitted = st.form_submit_button("Cadastrar Produto")

            if submitted:
                if not nome_produto: # Validação robusta
                    st.warning("O 'Nome do Produto' é obrigatório. Por favor, preencha.")
                    return
                if not unidade_medida:
                    st.warning("A 'Unidade de Medida' é obrigatória. Por favor, selecione.")
                    return

                # Normaliza o nome do produto para evitar entradas com espaços extras
                nome_produto_clean = nome_produto.strip()
                if insert_new_product(nome_produto_clean, unidade_medida, sku):
                    st.success(f"Produto '{nome_produto_clean}' cadastrado com sucesso!")
                    st.rerun() # Recarrega para mostrar o novo produto na lista e limpar o formulário
                # A mensagem de erro já é tratada dentro de insert_new_product
