from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import time
from threading import Thread

app = Flask(__name__)

CARDAPIO = {
    "1": "Pizza - R$25,00",
    "2": "Hambúrguer - R$15,00",
    "3": "Lasanha - R$30,00",
    "4": "Salada - R$12,00"
}

usuarios_temp = {}
STATUS_PEDIDO = ["Em produção", "A caminho", "Entregue"]


def criar_banco():
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
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


def atualizar_status_pedido(cliente):
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    for status in STATUS_PEDIDO:
        time.sleep(15)
        cursor.execute(
            "UPDATE pedidos SET status = ? WHERE cliente = ?", (status, cliente))
        banco.commit()
    banco.close()


def adicionar_pedido(cliente, pedido, endereco):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute("INSERT INTO pedidos (cliente, pedido, endereco, status) VALUES (?, ?, ?, ?)",
                       (cliente, pedido, endereco, "Em produção"))
        cursor.execute("INSERT INTO vendas (pedido) VALUES (?)", (pedido,))
        banco.commit()
        banco.close()
        print(
            f"[DEBUG] Pedido adicionado com sucesso: {cliente}, {pedido}, {endereco}")
        Thread(target=atualizar_status_pedido, args=(cliente,)).start()
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar pedido: {e}")


def verificar_status_pedido(cliente):
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute("SELECT status FROM pedidos WHERE cliente = ?", (cliente,))
    resultado = cursor.fetchone()
    banco.close()
    return resultado[0] if resultado else "Pedido não encontrado."


def cancelar_pedido(cliente):
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute("DELETE FROM pedidos WHERE cliente = ?", (cliente,))
    banco.commit()
    banco.close()
    return "Seu pedido foi cancelado."


def chatbot_resposta(mensagem, telefone):
    mensagem = mensagem.strip().lower()
    print(f"[DEBUG] Mensagem de {telefone}: {mensagem}")
    resposta = ""

    if telefone not in usuarios_temp:
        usuarios_temp[telefone] = {"etapa": "inicio"}

    etapa = usuarios_temp[telefone]["etapa"]
    print(f"[DEBUG] Etapa: {etapa}")

    if mensagem in ["oi", "olá", "menu"]:
        menu = "\n".join([f"{num} - {desc}" for num, desc in CARDAPIO.items()])
        usuarios_temp[telefone]["etapa"] = "aguardando_pedido"
        resposta = f"Olá! Escolha uma opção do cardápio:\n{menu}"

    elif etapa == "aguardando_pedido" and mensagem in CARDAPIO:
        usuarios_temp[telefone]["pedido"] = CARDAPIO[mensagem]
        usuarios_temp[telefone]["etapa"] = "aguardando_nome"
        resposta = "Ótima escolha! Agora, por favor, digite seu nome."

    elif etapa == "aguardando_nome":
        nome = mensagem.title()
        if len(nome) < 2:
            resposta = "Nome inválido. Por favor, digite seu nome completo."
        else:
            usuarios_temp[telefone]["nome"] = nome
            usuarios_temp[telefone]["etapa"] = "aguardando_endereco"
            resposta = "Perfeito! Agora, informe seu endereço completo."

    elif etapa == "aguardando_endereco":
        endereco = mensagem.strip()
        dados = usuarios_temp.get(telefone)
        nome = dados.get("nome")
        pedido = dados.get("pedido")

        print(f"[DEBUG] Nome: {nome}, Pedido: {pedido}, Endereço: {endereco}")

        if nome and pedido and len(endereco) > 5:
            adicionar_pedido(nome, pedido, endereco)
            resposta = f"✅ Pedido realizado com sucesso!\n🧾 {pedido}\n📍 Endereço: {endereco}\nPara acompanhar, digite: *status do meu pedido*."
            usuarios_temp[telefone]["etapa"] = "pedido_realizado"
        else:
            resposta = "❗ Erro ao processar o endereço. Por favor, envie novamente ou digite 'menu' para reiniciar."

    elif "status do meu pedido" in mensagem:
        nome = usuarios_temp[telefone].get("nome")
        if nome:
            status = verificar_status_pedido(nome)
            resposta = f"📦 Status do seu pedido: {status}"
        else:
            resposta = "❗ Nome não encontrado. Digite 'menu' para iniciar um novo pedido."

    elif "cancelar pedido" in mensagem:
        nome = usuarios_temp[telefone].get("nome")
        if nome:
            resposta = cancelar_pedido(nome)
            usuarios_temp.pop(telefone, None)
        else:
            resposta = "❗ Nenhum pedido encontrado para cancelar."

    else:
        resposta = "Desculpe, não entendi. Digite 'menu' para ver as opções."

    print(f"[DEBUG] Resposta: {resposta}")
    return resposta


@app.route("/bot", methods=["POST"])
def bot():
    msg = request.form.get("Body")
    telefone = request.form.get("From")
    resposta = chatbot_resposta(msg, telefone)
    resp = MessagingResponse()
    resp.message(resposta)
    return str(resp)


if __name__ == "__main__":
    criar_banco()
    app.run(port=5000)
