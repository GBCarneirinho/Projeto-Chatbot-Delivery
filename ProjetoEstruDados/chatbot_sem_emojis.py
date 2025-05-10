
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import time
from threading import Thread

app = Flask(__name__)

CARDAPIO = {
    "1": "Pizza - R$25,00",
    "2": "Hamburguer - R$15,00",
    "3": "Lasanha - R$30,00",
    "4": "Salada - R$12,00"
}

usuarios_temp = {}
STATUS_PEDIDO = ["Em producao", "A caminho", "Entregue"]

def criar_banco():
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        telefone TEXT,
        pedido TEXT,
        endereco TEXT,
        status TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido TEXT
    )''')
    banco.commit()
    banco.close()

def atualizar_status_pedido(telefone):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        for status in STATUS_PEDIDO:
            time.sleep(15)
            cursor.execute("UPDATE pedidos SET status = ? WHERE telefone = ?", (status, telefone))
            banco.commit()
        banco.close()
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar status do pedido: {e}")

def adicionar_pedido(cliente, telefone, pedido, endereco):
    try:
        print(f"[DEBUG] Inserindo no banco: Cliente={cliente}, Telefone={telefone}, Pedido={pedido}, Endereco={endereco}")
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute(
            "INSERT INTO pedidos (cliente, telefone, pedido, endereco, status) VALUES (?, ?, ?, ?, ?)",
            (cliente, telefone, pedido, endereco, "Em producao")
        )
        cursor.execute("INSERT INTO vendas (pedido) VALUES (?)", (pedido,))
        banco.commit()
        banco.close()
        print("[DEBUG] Pedido inserido com sucesso.")
        Thread(target=atualizar_status_pedido, args=(telefone,)).start()
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar pedido: {e}")

def verificar_status_pedido(telefone):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute("SELECT status FROM pedidos WHERE telefone = ?", (telefone,))
        resultado = cursor.fetchone()
        banco.close()
        return resultado[0] if resultado else "Pedido nao encontrado."
    except Exception as e:
        print(f"[ERRO] Falha ao verificar status: {e}")
        return "Erro ao verificar o status."

def cancelar_pedido(telefone):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute("DELETE FROM pedidos WHERE telefone = ?", (telefone,))
        banco.commit()
        banco.close()
        return "Seu pedido foi cancelado."
    except Exception as e:
        print(f"[ERRO] Falha ao cancelar pedido: {e}")
        return "Erro ao cancelar o pedido."

def chatbot_resposta(mensagem, telefone):
    telefone = telefone.replace("whatsapp:", "")
    mensagem = mensagem.strip().lower()
    print(f"[DEBUG] Mensagem de {telefone}: {mensagem}")
    resposta = ""

    if telefone not in usuarios_temp:
        usuarios_temp[telefone] = {"etapa": "inicio"}

    etapa = usuarios_temp[telefone]["etapa"]
    print(f"[DEBUG] Etapa atual: {etapa}")

    if mensagem in ["oi", "olá", "menu"]:
        menu = "\n".join([f"{num} - {desc}" for num, desc in CARDAPIO.items()])
        usuarios_temp[telefone] = {"etapa": "aguardando_pedido"}
        resposta = f"Olá! Escolha uma opcao do cardapio:\n{menu}"

    elif etapa == "aguardando_pedido" and mensagem in CARDAPIO:
        usuarios_temp[telefone]["pedido"] = CARDAPIO[mensagem]
        usuarios_temp[telefone]["etapa"] = "aguardando_nome"
        resposta = "Otima escolha! Agora, por favor, digite seu nome."

    elif etapa == "aguardando_nome":
        nome = mensagem.title()
        if len(nome) < 2:
            resposta = "Nome invalido. Por favor, digite seu nome completo."
        else:
            usuarios_temp[telefone]["nome"] = nome
            usuarios_temp[telefone]["etapa"] = "aguardando_endereco"
            resposta = "Perfeito! Agora, informe seu endereco completo."

    elif etapa == "aguardando_endereco":
        endereco = mensagem.strip()
        dados = usuarios_temp.get(telefone, {})
        nome = dados.get("nome")
        pedido = dados.get("pedido")
        print(f"[DEBUG] Nome: {nome}, Pedido: {pedido}, Endereco: {endereco}")

        if nome and pedido and len(endereco) > 5:
            adicionar_pedido(nome, telefone, pedido, endereco)
            resposta = f"Pedido realizado com sucesso!\nPedido: {pedido}\nEndereco: {endereco}\nPara acompanhar, digite: status do meu pedido."
            usuarios_temp[telefone]["etapa"] = "pedido_realizado"
        else:
            resposta = "ATENCAO: Erro ao processar o endereco. Por favor, envie novamente ou digite 'menu' para reiniciar."

    elif "status do meu pedido" in mensagem:
        status = verificar_status_pedido(telefone)
        resposta = f"Status do seu pedido: {status}"

    elif "cancelar pedido" in mensagem:
        resposta = cancelar_pedido(telefone)
        usuarios_temp.pop(telefone, None)

    else:
        resposta = "Desculpe, nao entendi. Digite 'menu' para ver as opcoes."

    print(f"[DEBUG] Resposta enviada: {resposta}")
    return resposta

@app.route("/bot", methods=["POST"])
def bot():
    msg = request.form.get("Body")
    telefone = request.form.get("From")
    print(f"[DEBUG] Requisicao recebida: {telefone} -> {msg}")
    resposta = chatbot_resposta(msg, telefone)
    resp = MessagingResponse()
    resp.message(resposta)
    return str(resp)

if __name__ == "__main__":
    criar_banco()
    app.run(port=5000, debug=True)
