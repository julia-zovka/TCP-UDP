# Socket-UDP-Entrega 1

## Sobre 

Esse projeto  é  um produto da disciplina "Redes de computadores", ministrada por Paulo Freitas de Araújo, no Centro de Informática da UFPE, e se resume na construção de uma sala de bate papo local, em que os usúarios conectados  trocam mensagens entre si  e conseguem ver quem entra e quem sai do chat.Os arquivos a seguir implemntam essa função por meio da um protocolo UDP.

## Especificidade
- implementação de transferencia de pacotes utilizando protocolo UDP
- troca de arquivos em pacotes de até 1024
- exibição da mensagem"hi, meu nome eh {input}" para entrar na sala
- "<IP>: <PORTA> /~<nome_usuario>: <mensagem> <hora-data>"  ao mandar mensagens
- "{nome} saiu da sala!" ao comunicar aos outros usuários quando alguém sai do chat
- "Você nao está  mais conectado à sala!" mensagem que aparece no terminal do usuário que se desconectou 

## Como funciona?
1. rodar em um terminal o arquivo server.py 
2. em outro terminal rodar cliente.py

**obs:** 
- Para conectar múltiplos clientes é necessário rodar o cliente.py em multiplos terminais.
- Se desconectar um usuário da sala e quiser reconectar, é necessário rodar cliente.py em outro terminal.

