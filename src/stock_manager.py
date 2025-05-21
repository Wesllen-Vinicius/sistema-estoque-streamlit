# src/stock_manager.py
import streamlit as st
import pandas as pd
from src.database import get_supabase_client
from datetime import datetime, date, timedelta
from src.product_manager import get_products_data # Importado no topo
import plotly.express as px # Importando Plotly para gráficos

# --- Funções de Interação com o Banco de Dados ---

def insert_stock_movement(product_id: str, movement_type: str, quantity_moved: float, observation: str = None, transaction_ref_id: str = None, movement_date: date = None):
    """
    Insere um novo movimento de estoque.
    Permite especificar a data do movimento. Se não fornecida, usa a data atual.
    """
    supabase = get_supabase_client()
    data = {
        "produto_id": product_id,
        "tipo_movimento": movement_type,
        "quantidade_movimentada": quantity_moved,
        "observacao": observation,
        "referencia_transacao_id": transaction_ref_id
    }
    if movement_date:
        data["data_movimento"] = str(movement_date) + "T00:00:00Z"

    try:
        with st.spinner("Registrando movimento de estoque..."):
            response = supabase.from_('movimentos_estoque').insert(data).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao registrar movimento: {e}. Por favor, verifique os dados e tente novamente.")
        return None

def get_all_products_for_stock_calc():
    """Busca todos os produtos para uso interno no cálculo de estoque."""
    return get_products_data()

def get_current_stock_summary(start_date: date = None, end_date: date = None):
    """
    Calcula o saldo atual de cada produto com base nos movimentos, considerando um período para cálculo de entradas/saídas.
    O 'saldo_atual' sempre considera todos os movimentos até a `end_date`.
    """
    supabase = get_supabase_client()

    products_data = get_all_products_for_stock_calc()
    if not products_data:
        return []

    processed_data = []
    for product in products_data:
        # A. Calcular saldo TOTAL acumulado ATÉ end_date (para o "Saldo Atual Acumulado")
        query_total_balance = supabase.from_('movimentos_estoque').select(
            'tipo_movimento, quantidade_movimentada'
        ).eq('produto_id', product['id'])

        if end_date:
            end_date_plus_one = end_date + timedelta(days=1)
            query_total_balance = query_total_balance.lt('data_movimento', str(end_date_plus_one))

        try:
            response_total_balance = query_total_balance.execute()
        except Exception as e:
            st.error(f"Erro ao buscar saldo acumulado para {product['nome_produto']}: {e}")
            response_total_balance = None

        current_balance = 0.0
        if response_total_balance and response_total_balance.data:
            for mov in response_total_balance.data:
                if mov['tipo_movimento'].startswith('entrada') or mov['tipo_movimento'] == 'ajuste_positivo':
                    current_balance += float(mov['quantidade_movimentada'])
                elif mov['tipo_movimento'].startswith('saida') or mov['tipo_movimento'] == 'ajuste_negativo':
                    current_balance -= float(mov['quantidade_movimentada'])

        # B. Calcular entradas e saídas DENTRO do período filtrado (para "Total Entradas/Saídas (Período)")
        total_entries_period = 0.0
        total_exits_period = 0.0

        query_period_movements = supabase.from_('movimentos_estoque').select(
            'tipo_movimento, quantidade_movimentada'
        ).eq('produto_id', product['id'])

        if start_date:
            query_period_movements = query_period_movements.gte('data_movimento', str(start_date))
        if end_date:
            end_date_plus_one = end_date + timedelta(days=1)
            query_period_movements = query_period_movements.lt('data_movimento', str(end_date_plus_one))

        try:
            response_period_movements = query_period_movements.execute()
        except Exception as e:
            st.error(f"Erro ao buscar movimentos do período para {product['nome_produto']}: {e}")
            response_period_movements = None

        if response_period_movements and response_period_movements.data:
            for mov in response_period_movements.data:
                if mov['tipo_movimento'].startswith('entrada'):
                    total_entries_period += float(mov['quantidade_movimentada'])
                elif mov['tipo_movimento'].startswith('saida') or mov['tipo_movimento'] == 'ajuste_negativo':
                    total_exits_period += float(mov['quantidade_movimentada'])

        processed_data.append({
            'produto_id': product['id'],
            'nome_produto': product['nome_produto'],
            'unidade_medida': product['unidade_medida'],
            'total_entradas_periodo': total_entries_period,
            'total_saidas_periodo': total_exits_period,
            'saldo_atual': current_balance
        })
    return processed_data


def get_detailed_movements(start_date: date = None, end_date: date = None):
    """
    Busca todos os movimentos de estoque com nome do produto, filtrados por data.
    """
    supabase = get_supabase_client()
    try:
        with st.spinner("Carregando histórico de movimentos..."):
            query = supabase.from_('movimentos_estoque').select('*, produtos(nome_produto)').order('data_movimento', desc=True)

            if start_date:
                query = query.gte('data_movimento', str(start_date))
            if end_date:
                end_date_plus_one = end_date + timedelta(days=1)
                query = query.lt('data_movimento', str(end_date_plus_one))

            response = query.execute()

            data = []
            if response.data:
                for item in response.data:
                    name_product = item['produtos']['nome_produto'] if item['produtos'] else 'N/A'
                    data.append({
                        "ID Movimento": item['id'],
                        "Produto": name_product,
                        "Tipo": item['tipo_movimento'],
                        "Quantidade": item['quantidade_movimentada'],
                        "Data": item['data_movimento'],
                        "Observação": item['observacao'],
                        "Ref. Transação": item['referencia_transacao_id']
                    })
            return data
    except Exception as e:
        st.error(f"Erro ao carregar movimentos detalhados: {e}")
        return []

# --- Funções de Renderização da UI ---

def render_stock_summary_section():
    """Renderiza a interface para o resumo do estoque com filtros de data e gráficos."""
    st.header("📊 Saldo e Resumo de Estoque")

    # Definir um período padrão para os filtros de data
    default_start_date = datetime.now().date().replace(day=1)
    default_end_date = datetime.now().date()

    col1, col2 = st.columns(2)
    with col1:
        start_date_summary = st.date_input(
            "Data Inicial (para Resumo de Período)",
            value=default_start_date,
            key="start_date_summary",
            help="Define o início do período para o 'Resumo de Movimentos no Período'."
        )
    with col2:
        end_date_summary = st.date_input(
            "Data Final (para Saldo Acumulado e Resumo de Período)",
            value=default_end_date,
            key="end_date_summary",
            help="Define o fim do período para o 'Resumo de Movimentos no Período' e a data limite para o 'Saldo Atual Acumulado'."
        )

    st.markdown("---")
    st.subheader("Saldo Atual Acumulado (até a Data Final Selecionada)")
    full_stock_summary_data = get_current_stock_summary(start_date=None, end_date=end_date_summary)

    # --- KPIs (Key Performance Indicators) ---
    st.markdown("##### Métricas Chave")
    if full_stock_summary_data:
        df_full_balance = pd.DataFrame(full_stock_summary_data)

        total_unique_products = len(df_full_balance['produto_id'].unique())
        total_stock_quantity = df_full_balance['saldo_atual'].sum()

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(label="Total de Produtos com Saldo", value=total_unique_products)
        with kpi2:
            st.metric(label="Quantidade Total em Estoque", value=f"{total_stock_quantity:,.2f}")
        with kpi3:
            # Para total de entradas/saídas no período, precisamos usar o period_stock_summary_data
            period_stock_summary_temp = get_current_stock_summary(start_date=start_date_summary, end_date=end_date_summary)
            if period_stock_summary_temp:
                df_period_temp = pd.DataFrame(period_stock_summary_temp)
                total_entries_period = df_period_temp['total_entradas_periodo'].sum()
                total_exits_period = df_period_temp['total_saidas_periodo'].sum()
                st.metric(label="Movimento Líquido no Período", value=f"{total_entries_period - total_exits_period:,.2f}", delta=f"Entradas: {total_entries_period:,.2f} / Saídas: {total_exits_period:,.2f}")
            else:
                st.metric(label="Movimento Líquido no Período", value="N/A")


        # --- Gráfico de Saldo Atual ---
        st.markdown("---")
        st.subheader("Visualização do Saldo Atual por Produto")

        # Filtra produtos com saldo maior que zero para o gráfico
        df_chart_data = df_full_balance[df_full_balance['saldo_atual'] > 0]

        if not df_chart_data.empty:
            fig = px.bar(
                df_chart_data,
                x='nome_produto',
                y='saldo_atual',
                color='unidade_medida', # Usa unidade de medida para cor
                title='Saldo Atual de Produtos no Estoque',
                labels={'nome_produto': 'Produto', 'saldo_atual': 'Saldo Atual'},
                hover_data={'unidade_medida': True} # Exibe unidade de medida ao passar o mouse
            )
            fig.update_layout(xaxis_title="Produto", yaxis_title="Saldo Atual")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum produto com saldo positivo para exibir no gráfico.")


        # --- Tabela de Saldo Atual Acumulado ---
        st.markdown("---")
        st.subheader("Detalhes do Saldo Atual Acumulado")
        df_full_balance = df_full_balance.rename(columns={
            'nome_produto': 'Produto',
            'unidade_medida': 'Unidade',
            'saldo_atual': 'Saldo Atual'
        })
        df_full_balance = df_full_balance[['Produto', 'Unidade', 'Saldo Atual']]
        st.dataframe(df_full_balance, use_container_width=True, hide_index=True)
        st.info(f"Total de produtos com saldo: **{len(df_full_balance)}**")

        # --- Botão de Exportar Saldo Atual ---
        csv_full_balance = df_full_balance.to_csv(index=False, sep=';', decimal=',')
        st.download_button(
            label="📊 Exportar Saldo Atual (CSV)",
            data=csv_full_balance,
            file_name=f"saldo_estoque_acumulado_{end_date_summary}.csv",
            mime="text/csv",
            key="download_full_balance"
        )

    else:
        st.info("Nenhum produto cadastrado ou sem movimentos de estoque para calcular o saldo acumulado.")

    st.markdown("---")
    st.subheader("Resumo de Movimentos no Período Selecionado")
    period_stock_summary_data = get_current_stock_summary(start_date=start_date_summary, end_date=end_date_summary)
    if period_stock_summary_data:
        df_period_balance = pd.DataFrame(period_stock_summary_data)
        df_period_balance = df_period_balance.rename(columns={
            'nome_produto': 'Produto',
            'unidade_medida': 'Unidade',
            'total_entradas_periodo': 'Entradas no Período',
            'total_saidas_periodo': 'Saídas no Período'
        })
        df_period_balance = df_period_balance[['Produto', 'Unidade', 'Entradas no Período', 'Saídas no Período']]
        st.dataframe(df_period_balance, use_container_width=True, hide_index=True)
        st.info(f"Total de produtos com movimentos no período: **{len(df_period_balance)}**")

        # --- Botão de Exportar Resumo do Período ---
        csv_period_balance = df_period_balance.to_csv(index=False, sep=';', decimal=',')
        st.download_button(
            label="📈 Exportar Resumo do Período (CSV)",
            data=csv_period_balance,
            file_name=f"resumo_movimentos_{start_date_summary}_a_{end_date_summary}.csv",
            mime="text/csv",
            key="download_period_balance"
        )
    else:
        st.info("Nenhum movimento de estoque registrado no período selecionado para o resumo.")


def render_detailed_movements_section():
    """Renderiza a interface para o histórico de movimentos e o formulário de registro com filtros de data, usando abas."""
    st.header("📝 Movimentos de Estoque") # Título mais visível

    tab1, tab2 = st.tabs(["Histórico Detalhado", "Registrar Novo Movimento"]) # <-- Aplicando o padrão de abas

    with tab1:
        st.subheader("Histórico Detalhado de Movimentos")

        default_start_date = datetime.now().date().replace(day=1)
        default_end_date = datetime.now().date()

        col1, col2 = st.columns(2)
        with col1:
            start_date_movements = st.date_input(
                "Data Inicial (Histórico)",
                value=default_start_date,
                key="start_date_movements_hist",
                help="Filtra os movimentos a partir desta data."
            )
        with col2:
            end_date_movements = st.date_input(
                "Data Final (Histórico)",
                value=default_end_date,
                key="end_date_movements_hist",
                help="Filtra os movimentos até esta data."
            )

        movements = get_detailed_movements(start_date=start_date_movements, end_date=end_date_movements) # <-- Correção da variável
        if movements:
            df_movements = pd.DataFrame(movements)
            df_movements['Data'] = pd.to_datetime(df_movements['Data']).dt.strftime('%d/%m/%Y %H:%M:%S')
            display_cols = ['Produto', 'Tipo', 'Quantidade', 'Data', 'Observação']
            st.dataframe(df_movements[display_cols], use_container_width=True, hide_index=True)
            st.info(f"Total de movimentos no período: **{len(df_movements)}**")
        else:
            st.info("Nenhum movimento de estoque registrado no período selecionado.")

    with tab2: # <-- Conteúdo do formulário de registro agora dentro desta aba
        st.subheader("Registrar Novo Movimento de Estoque")

        products = get_products_data()
        if not products:
            st.warning("Nenhum produto cadastrado. Por favor, cadastre produtos na aba 'Gerenciar Produtos' antes de registrar movimentos.")
            return

        products_dict = {p['nome_produto']: p['id'] for p in products}
        list_product_names = list(products_dict.keys())

        with st.form("form_movimento_estoque", clear_on_submit=True):
            st.markdown("**Informações do Movimento**")

            selected_product_name = st.selectbox(
                "Produto",
                list_product_names,
                key="mov_product_select",
                help="Selecione o produto envolvido neste movimento."
            )
            selected_product_id = products_dict.get(selected_product_name)

            movement_type = st.selectbox(
                "Tipo de Movimento",
                ['entrada_compra', 'entrada_producao', 'saida_venda', 'saida_remessa', 'saida_perda', 'ajuste_positivo', 'ajuste_negativo'],
                key="mov_type_select",
                help="Define se o movimento é uma entrada (soma) ou saída (subtrai) do estoque, e sua natureza."
            )
            quantity = st.number_input(
                "Quantidade",
                min_value=0.01,
                value=1.0,
                step=0.1,
                format="%.2f",
                key="mov_quantity_input",
                help="A quantidade do produto movimentada. Deve ser um valor positivo."
            )

            movement_date = st.date_input(
                "Data do Movimento",
                value=datetime.now().date(),
                key="mov_date_input",
                help="A data real em que o movimento de estoque ocorreu."
            )

            observation = st.text_area("Observação (Opcional)", help="Detalhes adicionais sobre este movimento.", key="mov_observation_input")

            st.markdown("---")
            submitted = st.form_submit_button("Registrar Movimento")

            if submitted:
                if not selected_product_id:
                    st.warning("Selecione um produto para registrar o movimento.")
                    return
                if quantity <= 0:
                    st.warning("A quantidade deve ser maior que zero.")
                    return

                if insert_stock_movement(selected_product_id, movement_type, quantity, observation, movement_date=movement_date):
                    st.success("Movimento registrado com sucesso!")
                    st.rerun()
