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


criar_banco()

STATUS_PEDIDO = ["Em produção", "A caminho", "Entregue"]


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
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute("INSERT INTO pedidos (cliente, pedido, endereco, status) VALUES (?, ?, ?, ?)",
                   (cliente, pedido, endereco, "Em produção"))
    banco.commit()
    banco.close()
    Thread(target=atualizar_status_pedido, args=(cliente,)).start()


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
    mensagem = mensagem.lower()
    if mensagem in ["oi", "olá"]:
        menu = "\n".join([f"{num} - {desc}" for num, desc in CARDAPIO.items()])
        return f"Olá! Gostaria de fazer seu pedido? Escolha uma opção:\n{menu}\nDigite o número do seu pedido."

    if mensagem in CARDAPIO:
        return "Ótima escolha! Agora, por favor, digite seu nome."

    if "meu nome é" in mensagem:
        nome = mensagem.replace("meu nome é", "").strip()
        return "Obrigado! Agora, informe seu endereço."

    if "meu endereço é" in mensagem:
        endereco = mensagem.replace("meu endereço é", "").strip()
        pedido = "Pizza"  # Aqui precisaremos salvar a escolha anterior no fluxo real
        adicionar_pedido(nome, pedido, endereco)
        return "Seu pedido foi feito! Acompanhe o status de entrega."

    if "status do meu pedido" in mensagem:
        return verificar_status_pedido(nome)

    if "cancelar pedido" in mensagem:
        return cancelar_pedido(nome)

    return "Desculpe, não entendi. Digite 'menu' para ver as opções."


@app.route("/bot", methods=["POST"])
def bot():
    msg = request.form.get("Body")
    telefone = request.form.get("From")
    resposta = chatbot_resposta(msg, telefone)
    resp = MessagingResponse()
    resp.message(resposta)
    return str(resp)


if __name__ == "__main__":
    app.run(port=5000)
