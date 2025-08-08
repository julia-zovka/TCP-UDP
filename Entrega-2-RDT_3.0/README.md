# Socket-UDP-Entrega 2

## Sobre 

Esse projeto  é  um produto da disciplina "Redes de computadores", ministrada por Paulo Freitas de Araújo, no Centro de Informática da UFPE, e se resume na construção de uma sala de bate papo, em que os usúarios conectados  trocam mensagens entre si  e conseguem ver quem entra e quem sai do chat.Os arquivos a seguir implementam essa função por meio de um protocolo UDP com a implementação do RDT 3.0.

## Estrutura de Arquivos

- server.py: Código do servidor que gerencia a comunicação entre os clientes.
- client.py: Código do cliente que permite aos usuários enviar e receber mensagens.
- utils: Pasta que contém função que será usada como uma 'biblioteca'
    - checksum.py
  

## Especificidade
- Implementação de transferência de pacotes utilizando protocolo UDP e protocolo RDT 3.0
    - ACK e número de sequência sendo utilizados para fazer o controle dos pacotes que chegaram e dos próximos
    - implementação de um timer caso o pacote se perca no meio do caminho oque acarreta no reenvio do pacote
    - caso o ACK chegue corrompido ou o timer tenha estourado, o pacote é reeenviado

- Troca de arquivos em pacotes de até 1024 bytes
- Exibição da mensagem"hi, meu nome eh {input}" para entrar na sala
- "IP: PORTA /~nome_usuario: mensagem hora-data"  ao mandar mensagens
- "{nome} saiu da sala!" ao comunicar aos outros usuários quando alguém sai do chat
- "Você nao está  mais conectado à sala!" mensagem que aparece no terminal do usuário que se desconectou 

## Como funciona?
1. Rodar em um terminal o arquivo server.py (use `python server.py`)
2. Em outro terminal rodar cliente.py (use `python cliente.py`)

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
    - [Letícia de Albuquerque Souza Leitão](https://www.linkedin.com/in/leticialevleitao/)
     
