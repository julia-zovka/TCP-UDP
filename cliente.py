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
            print(message.decode("utf-8").strip())
        except:
            pass


# Funcao para criar arquivo .txt, so guarda a mensagem mais recente

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename


# Funcao para criar fragmento com header (se estiver usando fragmentacao)

def create_fragment(contents, frag_size, frag_index, frag_count):
    # Calcula a posição inicial e final do fragmento
    start = frag_index * frag_size
    end = start + frag_size
    fragment_data = contents[start:end]
    actual_size = len(fragment_data)
    # Calcula CRC apenas dos dados do fragmento
    crc = crc32(fragment_data)
    # Monta o cabeçalho (tamanho real, índice, total, crc)
    header = struct.pack('!IIII', actual_size, frag_index, frag_count, crc)
    return header + fragment_data


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

#### conecta cliente na sala

    if message.startswith("hi, meu nome eh "):
        if is_conected:
            print("Calma jovem, você já está conectado à sala!")
        else:
            nickname = message[16:]
            is_conected = True
            client.sendto(f"SIGNUP_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))

### desconecta cliente do servidor, sai da sala

    elif message == "bye":
        if not is_conected:
            print("Você não está conectado à sala!, pra sair precisa entrar né, assim não dá")
        else:
            client.sendto(f"QUIT_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))
            print("Você não está  mais conectado à sala!, até a próxima")
            is_conected = False


### mandando mensagens

    elif is_conected:
        temp_file = convert_string_to_txt(nickname, message) # cria o txt contendo a mensagem  mais recente do usuario 
        with open(temp_file, "rb") as file:
            contents = file.read()

        ## calcula qunatos fragmento por mensagem
        frag_size = BUFF_SIZE - 16 ##  16 são os bytes do cabeçalho
        frag_count = math.ceil(len(contents) / frag_size)

        # Envia cada fragmento
        for frag_index in range(frag_count):
            fragment = create_fragment(contents, frag_size, frag_index, frag_count)
            client.sendto(fragment, (SERVER_IP, SERVER_PORT))
            
            # Pequeno delay para evitar congestionamento
            ##time.sleep(0.001)

    else:
        print("Comando inválido!")
