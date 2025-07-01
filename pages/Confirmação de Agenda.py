# app.py (versão com Streamlit)

# --- MÓDULOS NECESSÁRIOS ---
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import time
import random

# --- MÓDULOS DA SUA APLICAÇÃO ---
from login_auth import get_auth_new
from digisac_sender import enviar_mensagem_digisac

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(
    page_title="Automação AmorSaúde",
    page_icon="🤖",
    layout="wide"
)

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO (semelhantes às anteriores) ---

def carregar_template_mensagem():
    caminho_arquivo = "mensagem.txt"
    if not os.path.exists(caminho_arquivo):
        st.error(f"Arquivo de mensagem '{caminho_arquivo}' não encontrado.")
        return None
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return f.read()

def formatar_telefone_para_envio(numero_bruto):
    if pd.isna(numero_bruto): return None
    numeros = re.sub(r'\D', '', str(numero_bruto))
    return f'55{numeros}' if len(numeros) <= 11 else numeros

def run_full_process(log_placeholder):
    """
    Função principal que executa todo o processo, atualizando a interface
    em tempo real através do placeholder.
    """
    def log(message):
        """Função interna para adicionar logs e atualizar a tela."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        st.session_state.logs.append(log_entry)
        log_placeholder.text_area("Logs em Tempo Real", value='\n'.join(st.session_state.logs), height=400, key=f"log_area_{len(st.session_state.logs)}")

    try:
        # --- PARTE 1: BUSCA E GERAÇÃO DA PLANILHA ---
        st.session_state.status_text = "Buscando agendamentos..."
        log("Iniciando busca de agendamentos na API AMEI...")
        
        hoje = datetime.now()
        data_inicio_obj = hoje + timedelta(days=1)
        dia_da_semana_hoje = hoje.weekday()
        data_fim_obj = hoje + timedelta(days=4) if dia_da_semana_hoje in [3, 4] else hoje + timedelta(days=3)
        DATA_INICIO_API = data_inicio_obj.strftime('%Y%m%d')
        DATA_FIM_API = data_fim_obj.strftime('%Y%m%d')
        log(f"Hoje é {hoje.strftime('%A')}. Buscando de {data_inicio_obj.strftime('%d/%m/%Y')} a {data_fim_obj.strftime('%d/%m/%Y')}")

        params = {"statusAppointmentId": [2, 16], "dateInit": DATA_INICIO_API, "dateFinish": DATA_FIM_API, "unitId": 932, "limit": 100}
        headers = {'Authorization': f'Bearer {get_auth_new()}'}

        # --- LÓGICA DE PAGINAÇÃO CORRIGIDA ---
        todos_os_itens = []
        pagina_atual = 1
        total_paginas = 1 # Começa com 1 para garantir a primeira execução do loop

        while pagina_atual <= total_paginas:
            params['page'] = pagina_atual
            st.session_state.status_text = f"Buscando agendamentos... (Página {pagina_atual}/{total_paginas})"
            log(f"Buscando API - Página {pagina_atual} de {total_paginas}...")
            
            response = requests.get("https://amei.amorsaude.com.br/api/v1/appointments/confirm/status", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            todos_os_itens.extend(data.get("items", []))
            
            # AQUI ESTÁ A LÓGICA QUE FALTAVA:
            if pagina_atual == 1:
                # Atualiza o total de páginas com o valor real vindo da API
                total_paginas = data.get("meta", {}).get("totalPages", 1) or 1

            pagina_atual += 1
        
        if not todos_os_itens:
            log("Nenhum agendamento encontrado para o período.")
            st.session_state.status_text = "Concluído (sem dados)"
            return

        log(f"Busca finalizada! {len(todos_os_itens)} agendamentos encontrados. Gerando planilha...")
        df = pd.DataFrame([{'Data': datetime.fromisoformat(item['dataHoraInicio']).strftime('%d/%m/%Y'),'Hora': datetime.fromisoformat(item['dataHoraInicio']).strftime('%H:%M'),'Nome': item['pacienteNome'],'Profissional': item['profissionalNome'],'Celular': item.get('pacienteCelular')} for item in todos_os_itens])
        df.to_excel("agendamentos_confirmacao.xlsx", index=False)
        log("Planilha 'agendamentos_confirmacao.xlsx' gerada com sucesso.")
        st.session_state.dataframe_gerado = df

        # --- PARTE 2: ENVIO DAS MENSAGENS ---
        template_mensagem = carregar_template_mensagem()
        if not template_mensagem: return
        
        df.dropna(subset=['Celular'], inplace=True)
        total_registros = len(df)
        log(f"Iniciando processo de envio para {total_registros} contatos.")

        for i, (index, linha) in enumerate(df.iterrows()):
            nome = linha.get('Nome')
            st.session_state.status_text = f"Enviando mensagem {i + 1}/{total_registros} para {nome}"
            telefone_formatado = formatar_telefone_para_envio(linha.get('Celular'))
            
            if not telefone_formatado:
                log(f"({i + 1}/{total_registros}) Ignorando {nome}: sem número de celular válido.")
                continue

            mensagem_personalizada = template_mensagem.format(nome=nome, profissional=linha.get('Profissional'), data=linha.get('Data'), hora=linha.get('Hora'))
            log(f"({i + 1}/{total_registros}) Preparando para enviar para: {nome} ({telefone_formatado})")
            
            enviar_mensagem_digisac(telefone_formatado, mensagem_personalizada) # Descomente para produção
            time.sleep(1) # Simulação de envio
            log(f"Mensagem enviada com sucesso para {nome}.")
            
            if i < total_registros - 1:
                tempo_pausa = random.randint(30, 60)
                log(f"Pausa de {tempo_pausa} segundos...")
                time.sleep(tempo_pausa)
        
        log("✅ Processo de envio finalizado!")
        st.session_state.status_text = f"Concluído! {total_registros} mensagens processadas."
        st.balloons()

    except Exception as e:
        log(f"Ocorreu um erro fatal: {e}")
        st.session_state.status_text = "Processo finalizado com erro."
        st.error(f"Erro: {e}")

# --- INTERFACE DO USUÁRIO (UI) ---

st.title("🤖 Dashboard de Automação AmorSaúde")

# Inicialização do estado da sessão
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = ["Aguardando início do processo..."]
if 'status_text' not in st.session_state:
    st.session_state.status_text = "Parado"
if 'dataframe_gerado' not in st.session_state:
    st.session_state.dataframe_gerado = None

# Painel de controle
col1, col2 = st.columns([1, 3])
with col1:
    start_button = st.button("▶ Iniciar Processo de Confirmação", type="primary", disabled=st.session_state.process_running)
with col2:
    st.status(st.session_state.status_text, state=("running" if st.session_state.process_running else "complete"))

# Área de logs
log_placeholder = st.empty()
log_placeholder.text_area("Logs em Tempo Real", value='\n'.join(st.session_state.logs), height=400)

# Exibe a tabela de dados após a geração
if st.session_state.dataframe_gerado is not None:
    st.subheader("Pré-visualização dos Dados Gerados")
    st.dataframe(st.session_state.dataframe_gerado)

# Lógica de execução
if start_button:
    st.session_state.process_running = True
    st.session_state.logs = [] # Limpa logs antigos
    st.session_state.dataframe_gerado = None
    run_full_process(log_placeholder)
    st.session_state.process_running = False
    st.rerun() # Força um re-run final para reativar o botão