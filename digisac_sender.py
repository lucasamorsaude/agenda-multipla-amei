import requests
import json
import os
import streamlit as st

# --- DADOS DA SUA CONTA (MANTENHA-OS SEGUROS) ---
# É uma boa prática manter essas informações aqui ou em variáveis de ambiente.
BASE_URL =  st.secrets["api_digisac"]["base_url"]

API_TOKEN = st.secrets["api_digisac"]["base_url"]  # <-- Use um novo token aqui!
SERVICE_ID = st.secrets["api_digisac"]["service_id"]
# ----------------------------------------------------

def enviar_mensagem_digisac(numero_destino, texto_mensagem):
    """
    Envia uma mensagem de texto para um número específico via API Digisac.

    Args:
        numero_destino (str): O número do destinatário no formato '5532999999999'.
        texto_mensagem (str): O conteúdo da mensagem a ser enviada.

    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário.
        dict or str: O corpo da resposta da API em caso de sucesso ou o texto do erro.
    """
    url = f"{BASE_URL}/api/v1/messages"
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": texto_mensagem,
        "number": numero_destino,
        "serviceId": SERVICE_ID,
        "origin": "bot",
        "dontOpenticket": True
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)

        if response.status_code in [200, 201, 202]:
            return True, response.json()
        else:
            print(f"Falha ao enviar para {numero_destino}. Status: {response.status_code}")
            return False, response.text

    except requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro de conexão ou timeout: {e}")
        return False, str(e)


# --- Exemplo de como chamar a função ---
if __name__ == "__main__":
    # Você só precisa mudar os dados aqui para testar
    numero_para_enviar = "5532920009196" # Coloque o número de teste aqui
    mensagem_para_enviar = "Teste da nossa nova função de envio! Funciona!"

    sucesso, resposta = enviar_mensagem_digisac(numero_para_enviar, mensagem_para_enviar)

    print("\n--- Resultado do Envio ---")
    print(f"Envio bem-sucedido: {sucesso}")