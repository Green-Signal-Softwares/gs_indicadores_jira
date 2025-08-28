import pandas as pd 
import streamlit as st
import plotly.express as px 
from data_loader import initialize_ss_data

st.set_page_config(
    layout = "wide"
)

def converter_para_horas(tempo_str):
    if pd.isna(tempo_str):
        return np.nan
    try:
        partes = str(tempo_str).split(':')
        if len(partes) == 2: # Formato MM:SS
            minutos, segundos = map(float, partes)
            return minutos / 60 + segundos / 3600
        elif len(partes) == 3: # Formato HH:MM:SS ou HH:MM:SS.ms
            horas, minutos, segundos = map(float, partes[0:2] + [partes[2].split('.')[0]])
            return horas + minutos / 60 + segundos / 3600
        else:
            return np.nan
    except (ValueError, IndexError):
        return np.nan

initialize_ss_data()
dados_agosto = st.session_state['metricas_agosto']


dados_agosto['criado'] = pd.to_datetime(dados_agosto['criado'], format='%d/%m/%Y')
dados_agosto['primeira_resposta_horas'] = dados_agosto['primeira_resoista'].apply(converter_para_horas)
dados_agosto['tempo_resolucao_horas'] = dados_agosto['tempo_de_resolucao'].apply(converter_para_horas)

# --- BARRA LATERAL DE FILTROS ---
st.sidebar.title("Filtros Gerais")
min_date = dados_agosto['criado'].min().date()
max_date = dados_agosto['criado'].max().date()

filtro_data_geral = st.sidebar.date_input(
    "Selecione uma Data",
    min_value = min_date, 
    max_value = max_date,
    value = (min_date, max_date)
)
st.sidebar.divider()
st.sidebar.write("Cliente")
lista_clientes = dados_agosto['Organizacoes'].unique().tolist()
filtro_cliente = st.sidebar.multiselect("Selecione o(s) Cliente(s)",
                                        options = lista_clientes, 
                                        placeholder ="Selecione os Clientes")
st.sidebar.divider()
st.sidebar.write("Issue Type")
lista_issuetype = dados_agosto['Tipo_Chamado'].unique().tolist()
filtro_issuetype = st.sidebar.multiselect("Selecione o(s) Issue Type(s)",
                                            options=lista_issuetype, 
                                            placeholder="Selecione o Issue")

lista_status = dados_agosto['Status'].unique().tolist()
filtro_status = st.sidebar.multiselect("Selecione o(s) Status",
                                        options=lista_status,
                                        placeholder="Selecione os Status"
)


#Filtro por DATA
if len(filtro_data_geral) == 2:
    start_date, end_date = filtro_data_geral
else:
    start_date = end_date = filtro_data_geral[0]
mask_data = (dados_agosto['criado'].dt.date >= start_date) & (dados_agosto['criado'].dt.date <= end_date)
df_filtrado_1 = dados_agosto[mask_data]

# Filtro por CLIENTE 
if filtro_cliente:
    df_filtrado_2 = df_filtrado_1[df_filtrado_1['Organizacoes'].isin(filtro_cliente)]
else:
    df_filtrado_2 = df_filtrado_1

#Filtro por ISSUE TYPE 
if filtro_issuetype:
    df_filtrado_3 = df_filtrado_2[df_filtrado_2['Tipo_Chamado'].isin(filtro_issuetype)]
else:
    df_filtrado_3 = df_filtrado_2

#Filtro por STATUS 
if filtro_status:
    df_final_filtrado = df_filtrado_3[df_filtrado_3['Status'].isin(filtro_status)]
else:
    df_final_filtrado = df_filtrado_3
    
# --- CÁLCULO DE TODAS AS MÉTRICAS ---
status_finalizados = ['Entregue', 'Resolvido']
ticket_aberto = df_final_filtrado[~df_final_filtrado['Status'].isin(status_finalizados)].shape[0]
ticket_entregue = df_final_filtrado[df_final_filtrado['Status'].isin(status_finalizados)].shape[0]
primeira_resposta = df_final_filtrado['primeira_resposta_horas'].mean()
tempo_conclusao = df_final_filtrado['tempo_resolucao_horas'].mean()
total_tickets = df_final_filtrado.shape[0]
clientes_atendidos = df_final_filtrado['Organizacoes'].nunique()


st.title("Indicadores SLA 📉")
colquantidade,coltempo, colgraficos= st.columns([33,33,33])
with colquantidade:
    st.subheader("Relatório Tickets")
    st.metric("Tickets Aberto:", value=ticket_aberto)
    st.metric("Tickets Finalizados:", value=ticket_entregue) 
with coltempo:
    st.subheader("Tempo Médio de Resposta")
    st.metric("Primeira Resposta:", value=f"{primeira_resposta:.1f} horas" if not pd.isna(primeira_resposta) else "N/A")
    st.metric("Resolução:", value=f"{tempo_conclusao:.1f} horas" if not pd.isna(tempo_conclusao) else "N/A")
with colgraficos:
    st.subheader("Visão Geral do Período")
    st.metric("Total de Tickets:", value = total_tickets)
    st.metric("Total de Clientes Atendidos:", value=clientes_atendidos)
st.divider()

# --- GRÁFICO DE RANKING ---
st.subheader("Ranking de Chamados por Cliente")
ranking_data = df_final_filtrado.groupby(['Organizacoes', 'Tipo_Chamado']).size().reset_index(name='Quantidade')
total_por_org = ranking_data.groupby('Organizacoes')['Quantidade'].sum().sort_values(ascending=False).index
if not ranking_data.empty:
    ranking_data['Organizacoes'] = pd.Categorical(ranking_data['Organizacoes'], categories=total_por_org, ordered=True)
    ranking_data = ranking_data.sort_values('Organizacoes')
color_map = {'Bug': '#591C21', 'HelpDesk Support': '#D8B08C', 'New Feature': '#034159'}
grafico_ranking = px.bar(
    ranking_data, x='Organizacoes', y='Quantidade', color='Tipo_Chamado',
    title="Ranking de Chamados por Cliente e Tipo",
    labels={'Organizacoes': 'Cliente', 'Quantidade': 'Total de Tickets'},
    color_discrete_map=color_map, text_auto=True
)
grafico_ranking.update_traces(textfont_weight='bold')
grafico_ranking.update_layout(
    xaxis_title="Cliente", yaxis_title="Quantidade de Tickets", legend_title="Tipo de Chamado",
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="right", x=-0.1)
)
st.plotly_chart(grafico_ranking, use_container_width=True)



colissuetype, colticketstatus = st.columns([50, 50])

#grafico pizza
with colissuetype:
    st.subheader("Distribuição por Issue Type")
    data_pie = df_final_filtrado['Tipo_Chamado'].value_counts().reset_index()
    data_pie.columns = ['Tipo_Chamado', 'Quantidade']
    
    color_map_pie = {
        'Bug': '#591C21',
        'HelpDesk Support': '#D8B08C',
        'New Feature': '#034159'
    }

    pie_chart = px.pie(
        data_pie,
        values='Quantidade',
        names='Tipo_Chamado',
        color='Tipo_Chamado', 
        color_discrete_map=color_map_pie
    )

    pie_chart.update_traces(textinfo='percent+value')

    pie_chart.update_layout(
        legend_title="Tipo de Chamado",
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="right",
            x=-0.1
        )
    )
    st.plotly_chart(pie_chart, use_container_width=True)


with colticketstatus:
    st.subheader("Distribuição por Status")
    data_bar = df_final_filtrado['Status'].value_counts().reset_index()
    data_bar.columns = ['Status', 'Quantidade']

    data_bar['Categoria'] = np.where(data_bar['Status'].isin(['Resolvido', 'Entregue']), 'Finalizado', 'Em Andamento')
    
    color_map_bar = {
        'Finalizado': '#D2E8E3',
        'Em Andamento': '#69A6D1' 
    }

    bar_chart = px.bar(
        data_bar, 
        x='Quantidade', 
        y='Status', 
        orientation='h', 
        text_auto=True,
        color='Categoria', 
        color_discrete_map=color_map_bar
    )

    bar_chart.update_layout(
        legend_title="Categoria",
        legend=dict(
        )
    )
    bar_chart.update_traces(textposition='outside')
    st.plotly_chart(bar_chart, use_container_width=True)




    
    
    

    
        






