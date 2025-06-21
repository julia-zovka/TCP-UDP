import socket
import random
import threading
import math
import struct
from zlib import crc32

# Configuracoes do servidor

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFF_SIZE = 1024

# Cria o socket UDP
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.bind((SERVER_IP, random.randint(1000, 9998)))


# Funcao para receber mensagens

def receive():
    while True:
        try:
            message, _ = client.recvfrom(BUFF_SIZE)
            print(message.decode(encoding="ISO-8859-1"))
        except:
            pass


# Funcao para criar um arquivo .txt com a mensagem

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename


# Funcao para criar um fragmento com header

def create_fragment(contents, frag_size, frag_index, frag_count):
    data = bytearray()
    data.extend(contents[:frag_size])
    crc = crc32(data)
    header = struct.pack('!IIII', frag_size, frag_index, frag_count, crc)
    return header + data


# Inicia a thread de recebimento

receive_thread = threading.Thread(target=receive)
receive_thread.start()


# Loop principal

is_conected = False

while True:
    message = input()
    client_ip = client.getsockname()[0]

    if message.startswith("hi, meu nome eh "):
        if is_conected:
            print("Você já está conectado à sala!")
        else:
            nickname = message[16:]
            is_conected = True
            client.sendto(f"SIGNUP_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))

    elif message == "bye":
        if not is_conected:
            print("Você nao está conectado à sala!")
        else:
            client.sendto(f"QUIT_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))
            is_conected = False

    elif is_conected:
        path_file = convert_string_to_txt(nickname, message)
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
