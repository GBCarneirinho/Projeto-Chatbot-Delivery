from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import time
from threading import Thread

app = Flask(__name__)

CARDAPIO = {
    "1": ("Pizza", 25.00),
    "2": ("Hamburguer", 15.00),
    "3": ("Lasanha", 30.00),
    "4": ("Salada", 12.00),
    "5": ("Sushi", 40.00),
    "6": ("Esfirra", 8.00),
    "7": ("Coxinha", 6.00),
    "8": ("Refrigerante", 5.00),
    "9": ("Suco Natural", 7.00),
    "10": ("Brownie", 10.00)
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
            cursor.execute(
                "UPDATE pedidos SET status = ? WHERE telefone = ?", (status, telefone))
            banco.commit()
        banco.close()
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar status do pedido: {e}")


def adicionar_pedido(cliente, telefone, pedido, endereco):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute("INSERT INTO pedidos (cliente, telefone, pedido, endereco, status) VALUES (?, ?, ?, ?, ?)",
                       (cliente, telefone, pedido, endereco, "Em producao"))
        cursor.execute("INSERT INTO vendas (pedido) VALUES (?)", (pedido,))
        banco.commit()
        banco.close()
        Thread(target=atualizar_status_pedido, args=(telefone,)).start()
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar pedido: {e}")


def verificar_status_pedido(telefone):
    try:
        banco = sqlite3.connect('delivery.db')
        cursor = banco.cursor()
        cursor.execute(
            "SELECT status FROM pedidos WHERE telefone = ?", (telefone,))
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


def usuario_ja_cadastrado(telefone):
    banco = sqlite3.connect('delivery.db')
    cursor = banco.cursor()
    cursor.execute(
        "SELECT cliente, endereco FROM pedidos WHERE telefone = ? ORDER BY id DESC LIMIT 1", (telefone,))
    resultado = cursor.fetchone()
    banco.close()
    if resultado:
        return {"nome": resultado[0], "endereco": resultado[1]}
    return None


def chatbot_resposta(mensagem, telefone):
    telefone = telefone.replace("whatsapp:", "")
    mensagem = mensagem.strip().lower()

    if telefone not in usuarios_temp:
        usuarios_temp[telefone] = {"etapa": "verificar_cadastro"}

    etapa = usuarios_temp[telefone]["etapa"]

    if etapa == "verificar_cadastro":
        cadastro = usuario_ja_cadastrado(telefone)
        if cadastro:
            usuarios_temp[telefone].update({
                "nome": cadastro["nome"],
                "endereco": cadastro["endereco"],
                "etapa": "aguardando_pedido"
            })
            menu = "\n".join(
                [f"{num} - {desc[0]} - R${desc[1]:.2f}" for num, desc in CARDAPIO.items()])
            return f"Olá {cadastro['nome']}, seja bem-vindo de volta ao ZappyDelivery!\nAqui está o nosso cardápio:\n{menu}"
        else:
            usuarios_temp[telefone]["etapa"] = "aguardando_nome"
            return "Olá! Antes de fazer seu pedido, precisamos do seu cadastro.\nPor favor, envie seu nome completo:"

    elif etapa == "aguardando_nome":
        nome = mensagem.title()
        if len(nome) < 2:
            return "Nome inválido. Por favor, digite seu nome completo."
        usuarios_temp[telefone]["nome"] = nome
        usuarios_temp[telefone]["etapa"] = "aguardando_endereco"
        return "Perfeito! Agora, por favor, envie seu endereço completo."

    elif etapa == "aguardando_endereco":
        endereco = mensagem.strip()
        if len(endereco) < 5:
            return "Endereço inválido. Por favor, envie um endereço completo."
        usuarios_temp[telefone]["endereco"] = endereco
        usuarios_temp[telefone]["etapa"] = "aguardando_pedido"
        menu = "\n".join(
            [f"{num} - {desc[0]} - R${desc[1]:.2f}" for num, desc in CARDAPIO.items()])
        return f"Cadastro realizado com sucesso!\nAgora você pode fazer seu pedido. Aqui está o cardápio:\n{menu}"

    elif etapa == "aguardando_pedido":
        itens = [item.strip() for item in mensagem.replace(",", " ").split()]
        pedidos_selecionados = [(CARDAPIO[item][0], CARDAPIO[item][1])
                                for item in itens if item in CARDAPIO]
        if pedidos_selecionados:
            pedido_final = ", ".join(
                [f"{nome} - R${preco:.2f}" for nome, preco in pedidos_selecionados])
            total = sum([preco for _, preco in pedidos_selecionados])
            usuarios_temp[telefone]["pedido"] = pedido_final
            usuarios_temp[telefone]["total"] = total
            usuarios_temp[telefone]["etapa"] = "confirmar_pedido"
            return f"Você escolheu:\n{pedido_final}\nTotal: R${total:.2f}\nDeseja confirmar o pedido? Responda com *sim* ou *não*."
        else:
            return "Não entendi sua escolha. Por favor, envie os números dos itens desejados (ex: 1, 2, 5)."

    elif etapa == "confirmar_pedido":
        if mensagem == "sim":
            dados = usuarios_temp[telefone]
            adicionar_pedido(dados["nome"], telefone,
                             dados["pedido"], dados["endereco"])
            usuarios_temp[telefone]["etapa"] = "pedido_realizado"
            return f"Pedido confirmado!\n{dados['pedido']}\nTotal: R${dados['total']:.2f}\nSerá entregue em: {dados['endereco']}\nPara acompanhar, digite: *status do meu pedido*."
        else:
            usuarios_temp[telefone]["etapa"] = "aguardando_pedido"
            return "Tudo bem. Você pode escolher outro item do cardápio."

    elif "status do meu pedido" in mensagem:
        return f"Status do seu pedido: {verificar_status_pedido(telefone)}"

    elif "cancelar pedido" in mensagem:
        usuarios_temp.pop(telefone, None)
        return cancelar_pedido(telefone)

    elif mensagem == "menu":
        menu = "\n".join(
            [f"{num} - {desc[0]} - R${desc[1]:.2f}" for num, desc in CARDAPIO.items()])
        usuarios_temp[telefone]["etapa"] = "aguardando_pedido"
        return f"Aqui está o nosso cardápio:\n{menu}"

    else:
        return "Desculpe, não entendi. Digite 'menu' para ver as opções ou 'status do meu pedido'."


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
    app.run(port=5000, debug=True)
