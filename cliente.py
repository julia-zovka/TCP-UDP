import socket
import random
import threading #cria threads, importante para programação paralela
import math
import struct #interpretar e montar a estrututra dos pacotes 
from zlib import crc32

# Configuracoes do servidor
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFF_SIZE = 1024

# Cria o socket  e atribi uma porta aleatória a ele
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#afnet--- ipv4
#sockdgram----socket udp

client.bind((SERVER_IP, random.randint(1000, 9998)))

# Funcao de apresentacao simples
def apresentacao():
    nome = input("Digite seu nome: ")
    print(f"Oi {nome}, tudo bem?")
    print("\nPara entrar na sala, digite:")
    print(f"-hi, meu nome eh {nome}")
    print("\nPara sair da sala, digite:")
    print("-bye \n")
    return nome, f"hi, meu nome eh {nome}"

# Funcao para receber mensagens
def receive():
    while True:
        try:
            message, _ = client.recvfrom(BUFF_SIZE)
            print(message.decode(encoding="ISO-8859-1"))
        except:
            pass

# Funcao para criar arquivo .txt (se estiver usando)
def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename

# Funcao para criar fragmento com header (se estiver usando fragmentacao)
def create_fragment(contents, frag_size, frag_index, frag_count):
    data = bytearray()
    data.extend(contents[:frag_size])
    crc = crc32(data)
    header = struct.pack('!IIII', frag_size, frag_index, frag_count, crc)
    return header + data

# Inicia thread de recebimento
receive_thread = threading.Thread(target=receive)
receive_thread.start()

# Loop principal
is_conected = False

# Executa apresentacao
nickname, hello = apresentacao()

while True:
    message = input()

    if message.strip() == "":
        continue  # Ignora mensagens vazias

    client_ip = client.getsockname()[0]

#### CONECTAR O CLIENTE NO SERVIDOR

    if message.startswith("hi, meu nome eh "):
        if is_conected:
            print("Você já está conectado à sala!")
        else:
            nickname = message[16:]
            is_conected = True
            client.sendto(f"SIGNUP_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))

### DESCONECTAR O CLIENTE DO SERVIDOR, SAIR DA SALA

    elif message == "bye":
        if not is_conected:
            print("Você nao está conectado à sala!")
        else:
            client.sendto(f"QUIT_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))
            print("Você nao está  mais conectado à sala!")
            is_conected = False


### MANDANDO MENSAGENS

    elif is_conected:
        path_file = convert_string_to_txt(nickname, message) # cria o txt contendo a mensagem  mais recente do usuario 
        with open(path_file, "rb") as file:
            contents = file.read()

        frag_size = BUFF_SIZE - 16
        frag_index = 0
        frag_count = math.ceil(len(contents) / frag_size)

        while contents:
            fragment = create_fragment(contents, frag_size, frag_index, frag_count)
            client.sendto(fragment, (SERVER_IP, SERVER_PORT))
            contents = contents[frag_size:]
            frag_index += 1

    else:
        print("Comando inválido!")
