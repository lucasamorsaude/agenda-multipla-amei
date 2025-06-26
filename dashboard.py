# VERSÃO SIMPLIFICADA - FOCO APENAS NA AGENDA CONSOLIDADA
import streamlit as st
import requests
import pandas as pd
from datetime import date
from login_auth import get_auth_new

# --- 1. CONFIGURAÇÃO E FUNÇÕES ---

st.set_page_config(page_title="Agenda Consolidada", layout="wide")

auth = get_auth_new()

# As credenciais continuam sendo lidas do mesmo arquivo secrets.toml
HEADERS = {
    'Authorization': f"Bearer {auth}",
    'Cookie': st.secrets["api_credentials"]["cookie"]
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

# --- 2. INTERFACE PRINCIPAL DO SITE ---

st.title('📅 Agenda Consolidada do Dia')
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