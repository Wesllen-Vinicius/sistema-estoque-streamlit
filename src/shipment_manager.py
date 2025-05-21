# src/shipment_manager.py
import streamlit as st
import pandas as pd
from src.database import get_supabase_client
from src.product_manager import get_products_data
from src.stock_manager import insert_stock_movement # Usado para registrar a saída de estoque
from datetime import datetime, date, timedelta

# --- Funções de Interação com o Banco de Dados ---

def insert_new_shipment(destination: str, shipment_observation: str = None, shipment_date: date = None):
    """
    Insere uma nova remessa na tabela 'remessas'.
    Retorna o ID da remessa inserida.
    """
    supabase = get_supabase_client()
    data = {"destino": destination}
    if shipment_observation:
        data["observacao_remessa"] = shipment_observation
    if shipment_date:
        data["data_remessa"] = str(shipment_date) + "T00:00:00Z"

    try:
        with st.spinner("Registrando remessa principal..."):
            response = supabase.from_('remessas').insert(data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        else:
            st.error("Erro desconhecido ao registrar a remessa principal. Nenhum dado de retorno.")
            return None
    except Exception as e:
        st.error(f"Erro ao registrar remessa principal: {e}. Por favor, verifique os dados e tente novamente.")
        return None

def insert_shipment_item(remessa_id: str, produto_id: str, quantidade_remetida: float, preco_unitario: float = 0.0):
    """
    Insere um item em uma remessa na tabela 'itens_remessa'.
    Calcula o subtotal_item.
    """
    supabase = get_supabase_client()
    subtotal_item = quantidade_remetida * preco_unitario
    data = {
        "remessa_id": remessa_id,
        "produto_id": produto_id,
        "quantidade_remetida": quantidade_remetida,
        "preco_unitario_na_remessa": preco_unitario,
        "subtotal_item": subtotal_item
    }
    try:
        response = supabase.from_('itens_remessa').insert(data).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao adicionar item à remessa no banco de dados: {e}. Tente novamente.")
        return None

def get_detailed_shipments(start_date: date = None, end_date: date = None):
    """
    Busca todas as remessas com seus itens detalhados (via join), filtradas por data.
    """
    supabase = get_supabase_client()
    try:
        with st.spinner("Carregando histórico de remessas..."): # Adicionado spinner
            query = supabase.from_('remessas').select(
                """
                *,
                itens_remessa(
                    id,
                    produto_id,
                    quantidade_remetida,
                    preco_unitario_na_remessa,
                    subtotal_item,
                    produtos(nome_produto, unidade_medida)
                )
                """
            ).order('data_remessa', desc=True) # Ordena as remessas

            if start_date:
                query = query.gte('data_remessa', str(start_date))
            if end_date:
                end_date_plus_one = end_date + timedelta(days=1)
                query = query.lt('data_remessa', str(end_date_plus_one))

            response = query.execute()

            processed_data = []
            if response.data: # Verifica se há dados antes de processar
                for shipment in response.data:
                    shipment_total = 0.0
                    if shipment['itens_remessa']:
                        for item in shipment['itens_remessa']:
                            item_subtotal = float(item['subtotal_item']) # Garante que é float para soma
                            shipment_total += item_subtotal
                            processed_data.append({
                                "ID Remessa": shipment['id'],
                                "Data da Remessa": datetime.fromisoformat(shipment['data_remessa']).strftime('%d/%m/%Y %H:%M:%S'),
                                "Destino": shipment['destino'],
                                "Observação da Remessa": shipment['observacao_remessa'],
                                "Produto": item['produtos']['nome_produto'] if item['produtos'] else 'N/A',
                                "Unidade": item['produtos']['unidade_medida'] if item['produtos'] else 'N/A',
                                "Quantidade": float(item['quantidade_remetida']), # Garante que é float
                                "Preço Unitário": float(item['preco_unitario_na_remessa']), # Garante que é float
                                "Subtotal Item": item_subtotal,
                                "Total Remessa": None # Será preenchido no loop externo para cada linha da mesma remessa
                            })
                    else: # Caso a remessa não tenha itens (apenas para exibição)
                        processed_data.append({
                            "ID Remessa": shipment['id'],
                            "Data da Remessa": datetime.fromisoformat(shipment['data_remessa']).strftime('%d/%m/%Y %H:%M:%S'),
                            "Destino": shipment['destino'],
                            "Observação da Remessa": shipment['observacao_remessa'],
                            "Produto": "N/A (sem itens)", "Unidade": "", "Quantidade": 0.0,
                            "Preço Unitário": 0.0, "Subtotal Item": 0.0,
                            "Total Remessa": 0.0 # Remessa sem itens tem total 0
                        })

                    # Preenche o Total Remessa para todos os itens daquela remessa ou na linha da própria remessa
                    # Fazemos isso em um segundo loop para garantir que o total seja calculado antes de ser atribuído
                    for item_dict in processed_data:
                        if item_dict["ID Remessa"] == shipment['id'] and item_dict["Total Remessa"] is None:
                            item_dict["Total Remessa"] = shipment_total

            return processed_data
    except Exception as e:
        st.error(f"Erro ao carregar remessas detalhadas: {e}")
        return []

# --- Funções de Renderização da UI ---

def render_shipment_management_section():
    """Renderiza a interface para o registro e visualização de remessas com filtros de data."""
    st.header("🚚 Gerenciamento de Remessas") # Título mais visível

    tab1, tab2 = st.tabs(["Visualizar Remessas", "Registrar Nova Remessa"])

    # Definir um período padrão para os filtros de data
    default_start_date = datetime.now().date().replace(day=1) # Primeiro dia do mês atual
    default_end_date = datetime.now().date() # Data de hoje

    with tab1:
        st.subheader("Histórico Detalhado de Remessas")
        col1, col2 = st.columns(2)
        with col1:
            start_date_shipments = st.date_input(
                "Data Inicial (Remessas)",
                value=default_start_date,
                key="start_date_shipments_view",
                help="Filtra as remessas a partir desta data."
            )
        with col2:
            end_date_shipments = st.date_input(
                "Data Final (Remessas)",
                value=default_end_date,
                key="end_date_shipments_view",
                help="Filtra as remessas até esta data."
            )

        shipments_data = get_detailed_shipments(start_date=start_date_shipments, end_date=end_date_shipments)
        if shipments_data:
            df_shipments = pd.DataFrame(shipments_data)
            df_shipments = df_shipments.sort_values(by=["Data da Remessa", "Destino", "Produto"], ascending=[False, True, True])

            # Formatação de valores monetários
            df_shipments['Preço Unitário'] = df_shipments['Preço Unitário'].apply(lambda x: f"R$ {x:,.2f}")
            df_shipments['Subtotal Item'] = df_shipments['Subtotal Item'].apply(lambda x: f"R$ {x:,.2f}")
            df_shipments['Total Remessa'] = df_shipments['Total Remessa'].apply(lambda x: f"R$ {x:,.2f}")

            # IDs da Remessa só aparecem na primeira linha do grupo para clareza
            df_shipments['ID Remessa Exibição'] = df_shipments['ID Remessa'].mask(df_shipments['ID Remessa'].duplicated(), "")

            # Colunas para exibição otimizada para mobile
            display_columns = [
                'ID Remessa Exibição', 'Data da Remessa', 'Destino', 'Produto',
                'Quantidade', 'Unidade', 'Preço Unitário', 'Subtotal Item', 'Total Remessa'
            ]

            st.dataframe(df_shipments[display_columns], use_container_width=True, hide_index=True)
            st.info(f"Total de remessas no período: **{len(df_shipments['ID Remessa'].unique())}** (com **{len(df_shipments)}** itens).")
            st.markdown(
                """
                <small>As tabelas podem requerer rolagem horizontal em dispositivos móveis com muitas colunas.
                O 'Total Remessa' se repete para cada item da mesma remessa para fins de visualização agrupada.</small>
                """, unsafe_allow_html=True
            )
        else:
            st.info("Nenhuma remessa registrada no período selecionado.")

    with tab2:
        st.subheader("Registrar Nova Remessa")
        st.info("Você pode adicionar múltiplos itens a uma única remessa. Clique 'Adicionar Item' para cada produto.")

        products = get_products_data()
        if not products:
            st.warning("Nenhum produto cadastrado. Cadastre produtos na aba 'Gerenciar Produtos' antes de registrar remessas.")
            return

        products_dict = {p['nome_produto']: p['id'] for p in products}
        list_product_names = list(products_dict.keys())

        # Inicializa a lista de itens da remessa no session_state se não existir
        if 'current_shipment_items' not in st.session_state:
            st.session_state.current_shipment_items = []

        with st.form("form_add_item_to_shipment", clear_on_submit=True):
            st.markdown("##### Adicionar Item à Remessa")
            # Usando colunas que se empilham bem em mobile
            col_item1, col_item2, col_item3 = st.columns([3, 1.5, 2]) # Proporções para melhor visualização
            with col_item1:
                selected_product_name_item = st.selectbox(
                    "Produto",
                    list_product_names,
                    key="rem_item_product_select",
                    help="Selecione o produto a ser adicionado à remessa."
                )
            with col_item2:
                quantity_item = st.number_input(
                    "Quantidade",
                    min_value=0.01,
                    value=1.0,
                    step=0.1,
                    format="%.2f",
                    key="rem_item_quantity_input",
                    help="Quantidade do produto a ser remetida."
                )
            with col_item3:
                price_unit_item = st.number_input(
                    "Preço Unitário (Opcional)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="rem_item_price_input",
                    help="Preço de venda unitário do produto no momento da remessa."
                )

            st.markdown("---")
            add_item_button = st.form_submit_button("Adicionar Item à Remessa")

            if add_item_button:
                if not selected_product_name_item:
                    st.warning("Selecione um produto para adicionar o item.")
                    return
                if quantity_item <= 0:
                    st.warning("A quantidade do item deve ser maior que zero.")
                    return

                product_id_item = products_dict.get(selected_product_name_item)
                if product_id_item:
                    st.session_state.current_shipment_items.append({
                        "produto_id": product_id_item,
                        "nome_produto": selected_product_name_item,
                        "quantidade_remetida": quantity_item,
                        "preco_unitario_na_remessa": price_unit_item,
                        "subtotal_item": quantity_item * price_unit_item
                    })
                    st.success(f"Item '{selected_product_name_item}' ({quantity_item}) adicionado. Adicione mais ou finalize a remessa.")
                else:
                    st.error("Produto selecionado para item não encontrado. Por favor, tente novamente.")

        st.markdown("---")
        st.markdown("##### Itens Adicionados à Remessa Atual")
        if st.session_state.current_shipment_items:
            df_current_items = pd.DataFrame(st.session_state.current_shipment_items)
            df_current_items_display = df_current_items[['nome_produto', 'quantidade_remetida', 'preco_unitario_na_remessa', 'subtotal_item']]
            df_current_items_display.columns = ['Produto', 'Qtd.', 'Preço Unit.', 'Subtotal']

            # Formatação para exibição
            df_current_items_display['Preço Unit.'] = df_current_items_display['Preço Unit.'].apply(lambda x: f"R$ {x:,.2f}")
            df_current_items_display['Subtotal'] = df_current_items_display['Subtotal'].apply(lambda x: f"R$ {x:,.2f}")

            st.dataframe(df_current_items_display, use_container_width=True, hide_index=True)

            total_current_shipment = sum(item['subtotal_item'] for item in st.session_state.current_shipment_items)
            st.metric("Total da Remessa Atual (preliminar)", f"R$ {total_current_shipment:,.2f}")

            if st.button("Limpar Todos os Itens da Remessa", key="clear_shipment_items_button"):
                st.session_state.current_shipment_items = []
                st.info("Lista de itens da remessa limpa.")
                st.rerun()
        else:
            st.info("Nenhum item adicionado à remessa ainda.")

        st.markdown("---")
        st.markdown("##### Detalhes Finais da Remessa")
        with st.form("form_finalize_shipment", clear_on_submit=False): # Não limpa automaticamente para dar feedback
            destination = st.text_input(
                "Destino da Remessa",
                help="Nome do destinatário ou local para onde os produtos estão sendo remetidos (ex: Cliente X, Filial Y).",
                key="final_rem_destination"
            )
            shipment_date = st.date_input(
                "Data da Remessa",
                value=datetime.now().date(),
                key="final_rem_date_input",
                help="A data real em que a remessa foi realizada."
            )
            shipment_observation = st.text_area("Observação da Remessa (Opcional)", help="Detalhes adicionais sobre a remessa.", key="final_rem_obs")

            st.markdown("---")
            finalize_button = st.form_submit_button("Finalizar Remessa")

            if finalize_button:
                if not st.session_state.current_shipment_items:
                    st.warning("Adicione pelo menos um item à remessa antes de finalizar.")
                    # Nao retorna para permitir que o usuario adicione itens
                elif not destination:
                    st.warning("O 'Destino da Remessa' é obrigatório. Por favor, preencha.")
                    # Nao retorna para permitir que o usuario preencha
                else:
                    try:
                        with st.spinner("Finalizando e registrando remessa..."):
                            remessa_id = insert_new_shipment(destination, shipment_observation, shipment_date)

                            if remessa_id:
                                items_registered_count = 0
                                for item in st.session_state.current_shipment_items:
                                    # Inserir Item da Remessa
                                    if insert_shipment_item(
                                        remessa_id,
                                        item['produto_id'],
                                        item['quantidade_remetida'],
                                        item['preco_unitario_na_remessa']
                                    ):
                                        items_registered_count += 1
                                        # Registrar o Movimento de Saída para cada item
                                        insert_stock_movement(
                                            item['produto_id'],
                                            'saida_remessa',
                                            item['quantidade_remetida'],
                                            f"Remessa {remessa_id[:8]} para {destination}",
                                            remessa_id,
                                            movement_date=shipment_date
                                        )

                                if items_registered_count == len(st.session_state.current_shipment_items):
                                    st.success(f"Remessa para '{destination}' (ID: {remessa_id[:8]}...) registrada com sucesso com {items_registered_count} itens!")
                                    st.session_state.current_shipment_items = [] # Limpa a lista de itens
                                    st.rerun() # Recarrega para limpar formulários e mostrar na lista
                                else:
                                    st.error(f"Atenção: Houve um problema ao registrar alguns itens da remessa. {items_registered_count}/{len(st.session_state.current_shipment_items)} itens registrados.")
                            else:
                                st.error("Não foi possível finalizar a remessa. A remessa principal não foi registrada. Tente novamente.")
                    except Exception as e:
                        st.error(f"Erro inesperado ao finalizar remessa: {e}. Contate o suporte.")
