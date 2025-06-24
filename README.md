# Socket-UDP-Entrega 1

## Sobre 

Esse projeto  é  um produto da disciplina "Redes de computadores", ministrada por Paulo Freitas de Araújo, no Centro de Informática da UFPE, e se resume na construção de uma sala de bate papo, em que os usúarios conectados  trocam mensagens entre si  e conseguem ver quem entra e quem sai do chat.Os arquivos a seguir implementam essa função por meio de um protocolo UDP.

## Estrutura de Arquivos

- server.py: Código do servidor que gerencia a comunicação entre os clientes.
- client.py: Código do cliente que permite aos usuários enviar e receber mensagens.

## Especificidade
- Implementação de transferência de pacotes utilizando protocolo UDP
- Troca de arquivos em pacotes de até 1024 bytes
- Exibição da mensagem"hi, meu nome eh {input}" para entrar na sala
- "IP: PORTA /~nome_usuario: mensagem hora-data"  ao mandar mensagens
- "{nome} saiu da sala!" ao comunicar aos outros usuários quando alguém sai do chat
- "Você nao está  mais conectado à sala!" mensagem que aparece no terminal do usuário que se desconectou 

## Como funciona?
1. Rodar em um terminal o arquivo server.py 
2. Em outro terminal rodar cliente.py

**obs:** 
- Para conectar múltiplos clientes é necessário rodar o cliente.py em multiplos terminais.
- Se desconectar um usuário da sala e quiser reconectar, é necessário rodar cliente.py em outro terminal.
- Os arquivos server_log.txt guardam todas as mensagens de um usuário, funcionando como um log de mensagens

## Contribuintes
- Júlia Zovka de Souza
- Letícia de Albuquerque Souza Leitão 
- João Paulo Oliveira Nolasco

    ### Contato
    - [Júlia Zovka de Souza - Linkedin](https://www.linkedin.com/in/j%C3%BAlia-zovka-de-souza-a4731235a/)
    - [João Paulo Oliveira Nolasco - Linkedin](https://www.linkedin.com/in/joaonolasco10/)
     
