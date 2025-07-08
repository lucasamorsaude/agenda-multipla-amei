# VERSÃO SIMPLIFICADA - FOCO APENAS NA AGENDA CONSOLIDADA
import streamlit as st
import requests
import pandas as pd
from datetime import date
from login_auth import get_auth_new

# --- 1. CONFIGURAÇÃO E FUNÇÕES ---

st.set_page_config(page_title="Agenda Múltipla", layout="wide")

auth = get_auth_new()

# As credenciais continuam sendo lidas do mesmo arquivo secrets.toml
HEADERS = {
    'Authorization': f"Bearer {auth}",
    'Cookie': st.secrets["api_credentials_dashboard"]["cookie"]
}

# URLs das APIs que vamos usar
PROFISSIONAIS_URL = 'https://amei.amorsaude.com.br/api/v1/profissionais/by-unidade'
SLOTS_URL = 'https://amei.amorsaude.com.br/api/v1/slots/list-slots-by-professional'

# Dicionário de Estilos para os Status
STATUS_STYLES = {
    "Livre": "background-color: #E3F2FD; border: 1px solid #90CAF9; color: #1565C0;", # Fundo azul claro, borda e texto azul escuro
    "Bloqueado": "background-color: #F5F5F5; color: #9E9E9E; border: 1px solid #E0E0E0;", # Cinza claro
    "Atendido": "background-color: #7ff57f; border: 1px solid #1b8c0a; color: #1b8c0a;",
    "Atendido pós-consulta": "background-color: #73ff7a; border: 1px solid #1b8c0a; color: #1b8c0a;",
    "Marcado - confirmado": "background-color: #96f2ef; border: 1px solid #1565C0; color: #1565C0;",
    "Em atendimento": "background-color: #FFFDE7; border: 1px solid #FBC02D; color: #F57F17;",
    "Não compareceu": "background-color: #fa7d90; border: 1px solid #E57373; color: #C62828;", # Vermelho claro, texto escuro
    "Agendado": "background-color: #f5d5a6; border: 1px solid #E57373; color: #C62828;",
    "Encaixe": "background-color: #a88ef5; border: 1px solid #7649fc; color: #7649fc;",
    "Aguardando atendimento": "background-color: #ffe770; border: 1px solid #a89a1d; color: #a89a1d;",
    "Aguardando pós-consulta": "background-color: #c2ffd4; border: 1px solid #07ab38; color: #07ab38;",
    "Não compareceu pós-consulta": "background-color: #c2ffd4; border: 1px solid #07ab38; color: #07ab38;",
    # Adicione outros status que encontrar aqui
    "Bloqueado": "background-color: #bfbfbf; border: 1px solid #7d7d7d; color: #7d7d7d;",
    "default": "background-color: #FAFAFA; border: 1px solid #E0E0E0; color: #757575;"
}

@st.cache_data(ttl=600)
def get_all_professionals():
    try:
        response = requests.get(PROFISSIONAIS_URL, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao buscar profissionais: {e}")
        return None

def get_slots_for_professional(professional_id, selected_date):
    params = {
        'idClinic': 932,
        'idSpecialty': 'null',
        'idProfessional': professional_id,
        'initialDate': selected_date.strftime('%Y%m%d'),
        'finalDate': selected_date.strftime('%Y%m%d'),
        'initialHour': '00:00',
        'endHour': '23:59'
    }
    try:
        response = requests.get(SLOTS_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get('hours', [])
        else:
            return []
    except requests.exceptions.RequestException:
        return []
    

def create_html_progress_bar(percentage, color):
    # Garante que a porcentagem esteja entre 0 e 100
    percentage = max(0, min(100, percentage))
    return f"""
    <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; overflow: hidden; height: 20px; margin-top: 5px; margin-bottom: 10px;">
        <div style="width: {percentage}%; background-color: {color}; height: 100%; border-radius: 5px; text-align: center; color: white; line-height: 20px; font-size: 0.8em;">
        </div>
    </div>
    """

# --- 2. INTERFACE PRINCIPAL DO SITE ---

st.title('📅 Agenda Múltipla')
st.markdown("Visualize todos os horários (livres, agendados, etc.) lado a lado. **Clique no nome do profissional para abrir no sistema Amei.**")

AGENDA_URL_TEMPLATE = "https://amei.amorsaude.com.br/schedule/schedule-appointment?profissionalId={}&date={}"

selected_date = st.date_input("Selecione a data:", date.today())

if st.button("Buscar Agendas"):
    profissionais = get_all_professionals()
    
    if profissionais:
        agendas_por_profissional = {}
        resumo_geral = {}
        
        total_profissionais = len(profissionais)
        progress_bar = st.progress(0, text="Iniciando busca...")
        
        for i, prof in enumerate(profissionais):
            prof_id = prof.get('id')
            prof_nome = prof.get('nome', f'Profissional ID {prof_id}')
            
            progress_bar.progress((i + 1) / total_profissionais, text=f"Buscando agenda de {prof_nome}...")
            
            slots = get_slots_for_professional(prof_id, selected_date)
            
            horarios_processados = []
            contagem_status = {}

            for slot in slots:
                status_atual = slot.get('status', 'Indefinido')
                horarios_processados.append({
                    'horario': slot.get('formatedHour', 'N/A'),
                    'status': status_atual,
                    'paciente': slot.get('patient'),
                    'numeric_hour': slot.get('hour', 0.0)
                })
                contagem_status[status_atual] = contagem_status.get(status_atual, 0) + 1
            
            if horarios_processados:
                agendas_por_profissional[prof_nome] = {
                    "id": prof_id,
                    "horarios": sorted(horarios_processados, key=lambda x: x['numeric_hour'])
                }
                resumo_geral[prof_nome] = contagem_status

        progress_bar.empty()

        if agendas_por_profissional:
            with st.expander("📊 Ver Resumo Geral das Agendas", expanded=False):
                dados_resumo = []
                for profissional, status_dict in resumo_geral.items():
                    linha = {"Profissional": profissional}
                    for status, valor in status_dict.items():
                        try:
                            linha[status] = int(valor)
                        except:
                            linha[status] = 0
                    dados_resumo.append(linha)

                df_resumo = pd.DataFrame(dados_resumo).fillna(0)

                for col in df_resumo.columns:
                    if col != "Profissional":
                        df_resumo[col] = df_resumo[col].astype(int)

                df_resumo = df_resumo.set_index("Profissional")

                # Soma geral excluindo "Bloqueado" e "Livre"
                status_excluir = ["Bloqueado", "Livre"]
                colunas_para_somar = [col for col in df_resumo.columns if col not in status_excluir]
                df_resumo["Total Agendado"] = df_resumo[colunas_para_somar].sum(axis=1)

                # Transpõe
                df_transposto = df_resumo.T

                # Aplica estilo para destacar a linha 'Total Agendado'
                def highlight_total(row):
                    return ['background-color: #242424; font-weight: bold;' if row.name == "Total Agendado" else '' for _ in row]

                styled_df = df_transposto.style.apply(highlight_total, axis=1)

                st.dataframe(styled_df, use_container_width=True)

            
            # --- Lógica para % de confirmação e barra de progresso (USANDO HTML CUSTOMIZADO) ---
            with st.expander("📊 Confirmação Geral de Agendamentos e Ocupação", expanded=False): # Nome do expander ajustado
                # Criação das abas (tabs)
                tab1, tab2, tab3, tab4 = st.tabs([
                    "Confirmação Total", 
                    "Confirmação por Profissional", 
                    "Taxa de Ocupação Total", # Renomeado para clareza
                    "Taxa de Ocupação por Profissional" # Nova aba
                ])

                with tab1: # Conteúdo da Confirmação Total
                    st.subheader("Visão Geral de Confirmação")
                    total_agendado_geral = df_resumo["Total Agendado"].sum() if "Total Agendado" in df_resumo.columns else 0
                    total_confirmado_geral = df_resumo["Marcado - confirmado"].sum() if "Marcado - confirmado" in df_resumo.columns else 0


                    if total_agendado_geral > 0:
                        percentual_confirmacao = (total_confirmado_geral / total_agendado_geral) * 100
                        st.write(f"**Total de Agendados:** {total_agendado_geral}")
                        st.write(f"**Total de Confirmados:** {total_confirmado_geral}")
                        st.write(f"**Percentual de Confirmação:** {percentual_confirmacao:.2f}%")

                        progress_color = ""
                        if percentual_confirmacao < 60:
                            progress_color = "#FF4B4B"  # Vermelho mais forte
                        elif 60 <= percentual_confirmacao < 80:
                            progress_color = "#FFA500"  # Laranja (amarelo)
                        else:
                            progress_color = "#4CAF50"  # Verde mais forte
                        
                        # Usa a função auxiliar para gerar a barra HTML
                        st.markdown(create_html_progress_bar(percentual_confirmacao, progress_color), unsafe_allow_html=True)
                        

                    else:
                        st.info("Não há agendamentos válidos (exceto Livre/Bloqueado) para calcular a porcentagem de confirmação.")

                with tab2: # Conteúdo da Confirmação por Profissional
                    st.subheader("Confirmação por Profissional")

                    if not df_resumo.empty:
                        for profissional, row in df_resumo.iterrows():
                            agendados_prof = row.get("Total Agendado", 0)
                            confirmados_prof = row.get("Marcado - confirmado", 0)
                            
                            percentual_prof = 0
                            if agendados_prof > 0:
                                percentual_prof = (confirmados_prof / agendados_prof) * 100
                            
                            st.markdown(f"{profissional}")
                            st.write(f"  Total Agendado: {agendados_prof}, Confirmados: {confirmados_prof}")
                            st.write(f"  Percentual de Confirmação: {percentual_prof:.2f}%")

                            progress_color_prof = ""
                            if percentual_prof < 60:
                                progress_color_prof = "#FF4B4B"
                            elif 60 <= percentual_prof < 80:
                                progress_color_prof = "#FFA500"
                            else:
                                progress_color_prof = "#4CAF50"
                            
                            # Usa a função auxiliar para gerar a barra HTML para cada profissional
                            st.markdown(create_html_progress_bar(percentual_prof, progress_color_prof), unsafe_allow_html=True)
                            st.markdown("---") # Separador para cada profissional
                    else:
                        st.info("Nenhum dado de confirmação por profissional disponível.")
                
                with tab3: # Nova aba para Taxa de Ocupação Total
                    st.subheader("Taxa de Ocupação Geral")

                    # Numerador: "agendamentos gerais, incluindo encaixes" (Total Agendado)
                    total_ocupados = df_resumo["Total Agendado"].sum() if "Total Agendado" in df_resumo.columns else 0
                    
                    # Denominador: Soma de TODOS os slots (todas as colunas de status)
                    all_status_cols = [col for col in df_resumo.columns if col not in ["Profissional", "Total Agendado"]]
                    total_slots_disponiveis = df_resumo[all_status_cols].sum().sum()


                    if total_slots_disponiveis > 0:
                        percentual_ocupacao = (total_ocupados / total_slots_disponiveis) * 100
                        st.write(f"**Total de Horários Ocupados:** {total_ocupados}")
                        st.write(f"**Total de Slots Disponíveis:** {total_slots_disponiveis}")
                        st.write(f"**Taxa de Ocupação:** {percentual_ocupacao:.2f}%")

                        # Definição da cor da barra de progresso para a taxa de ocupação
                        ocupacao_color = ""
                        if percentual_ocupacao < 60:
                            ocupacao_color = "#FF4B4B"  # Vermelho
                        elif 60 <= percentual_ocupacao < 80:
                            ocupacao_color = "#FFA500"  # Laranja
                        else:
                            ocupacao_color = "#4CAF50"  # Verde
                        
                        st.markdown(create_html_progress_bar(percentual_ocupacao, ocupacao_color), unsafe_allow_html=True)
                    else:
                        st.info("Não há slots disponíveis para calcular a taxa de ocupação.")

                with tab4: # Nova aba para Taxa de Ocupação por Profissional
                    st.subheader("Taxa de Ocupação por Profissional")

                    if not df_resumo.empty:
                        for profissional, row in df_resumo.iterrows():
                            # Horários ocupados para o profissional
                            ocupados_prof = row.get("Total Agendado", 0)
                            
                            # Total de slots para o profissional (todas as contagens de status para a linha do profissional)
                            total_slots_prof = row[all_status_cols].sum() # all_status_cols já foi definida e exclui "Profissional", "Total Agendado"
                            
                            percentual_ocupacao_prof = 0
                            if total_slots_prof > 0:
                                percentual_ocupacao_prof = (ocupados_prof / total_slots_prof) * 100
                            
                            st.markdown(f"{profissional}")
                            st.write(f"  Horários Ocupados: {ocupados_prof}, Total de Slots: {total_slots_prof}")
                            st.write(f"  Taxa de Ocupação: {percentual_ocupacao_prof:.2f}%")

                            ocupacao_color_prof = ""
                            if percentual_ocupacao_prof < 60:
                                ocupacao_color_prof = "#FF4B4B"
                            elif 60 <= percentual_ocupacao_prof < 80:
                                ocupacao_color_prof = "#FFA500"
                            else:
                                ocupacao_color_prof = "#4CAF50"
                            
                            st.markdown(create_html_progress_bar(percentual_ocupacao_prof, ocupacao_color_prof), unsafe_allow_html=True)
                            st.markdown("---") # Separador para cada profissional
                    else:
                        st.info("Nenhum dado de ocupação por profissional disponível.")


            st.markdown("---")

            cols = st.columns(len(agendas_por_profissional))
            
            for i, (nome, agenda_data) in enumerate(agendas_por_profissional.items()):
                with cols[i]:
                    prof_id = agenda_data['id']
                    horarios = agenda_data['horarios']
                    
                    data_formatada = selected_date.strftime('%Y-%m-%d')
                    link_agenda = AGENDA_URL_TEMPLATE.format(prof_id, data_formatada)
                    
                    st.markdown(
                        f"<h3><a href='{link_agenda}' target='_blank' style='color: #FFFFFF; text-decoration: none;'>{nome}</a></h3>",
                        unsafe_allow_html=True
                    )

                    for slot in horarios:
                        status = slot['status']
                        paciente = slot['paciente']
                        estilo_div = STATUS_STYLES.get(status, STATUS_STYLES['default'])
                        conteudo_card = f"<strong>{slot['horario']}</strong>"
                        if paciente:
                            estilo_paciente = "color: #424242; font-size: 12px; font-weight: 500;"
                            nome_paciente_curto = (paciente[:20] + '...') if len(paciente) > 20 else paciente
                            conteudo_card += f"<br><span style='{estilo_paciente}'>{nome_paciente_curto}</span>"
                        st.markdown(
                            f"<div style='{estilo_div} border-radius: 8px; padding: 10px; margin: 4px; text-align:center; font-size:16px; min-height: 65px;'>"
                            f"{conteudo_card}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
        else:
            st.warning(f"Nenhum horário encontrado para a data {selected_date.strftime('%d/%m/%Y')}.")
    else:
        st.error("Não foi possível obter a lista de profissionais.")