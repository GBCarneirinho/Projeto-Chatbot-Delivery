# ZappyDelivery Chatbot

Este é um chatbot de delivery feito com Python, Flask, Twilio e SQLite. Ele permite que usuários façam pedidos via WhatsApp, cadastrem nome e endereço, recebam o cardápio, acompanhem o status da entrega e possam cancelar pedidos.

## Funcionalidades

- Integração com o WhatsApp usando a API do Twilio.
- Cadastro automático de clientes com nome e endereço.
- Cardápio interativo com múltiplas opções.
- Acompanhamento do pedido com atualização de status a cada 15 segundos:
  - Em produção → A caminho → Entregue.
- Cancelamento de pedidos.
- Armazenamento de dados em banco SQLite (`delivery.db`).
- Registro de vendas.

## Tecnologias Usadas

- Python 3
- Flask
- Twilio
- SQLite
- Threading (`threading.Thread`)
- HTML TwiML (via `twilio.twiml.messaging_response`)

## Requisitos

- Python 3 instalado
- Conta e número verificado no [Twilio](https://www.twilio.com/)
- Biblioteca `twilio`: instale com `pip install twilio`
- Flask: instale com `pip install flask`
