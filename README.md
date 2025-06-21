# Socket-UDP-Entrega 1

## Sobre 

O projeto se resume na construção de uma sala de bate papo, em que os usúarios conectados  podem trocar mensagens e conseguem ver quem entra e quem sai do chat.

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

**obs**: Para conectar múltiplos clientes é necessário rodar o cliente.py em multiplos terminais
**obs**:Se desconectar um usuário da sala e quiser reconectar, é necessário rodar cliente.py em outro terminal.

