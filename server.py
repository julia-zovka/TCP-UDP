import socket
import queue
import threading
import struct
from datetime import datetime


# Configuracoes do servidor
SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000

BUFF_SIZE = 1024


# Inicializacao

messages = queue.Queue()
clients_ip = []
clients_nickname = []

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))


# Funcao para salvar mensagem em .txt

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}_server.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename


# Funcao para pegar data e hora atual

def get_current_time_and_date():
    now = datetime.now()
    return now.strftime("%H:%M:%S %d/%m/%Y")


# Funcao para remover cliente

def remove_client(client):
    index_client = clients_ip.index(client)
    clients_ip.remove(client)
    clients_nickname.pop(index_client)


# Thread para receber mensagens

def receive():
    received_chunks = 0
    rec_list = []

    while True:
        try:
            message_received_bytes, address_ip_client = server.recvfrom(BUFF_SIZE)

            if (message_received_bytes.decode().startswith("SIGNUP_TAG:") or
                message_received_bytes.decode().startswith("QUIT_TAG:")):
                messages.put((message_received_bytes, address_ip_client))
            else:
                raise NameError('MESSAGE_TAG')

        except:
            header = message_received_bytes[:16]
            message_received_bytes = message_received_bytes[16:]
            (frag_size, frag_index, frag_count, crc) = struct.unpack('!IIII', header)

            if len(rec_list) < frag_count:
                need_to_add = frag_count - len(rec_list)
                rec_list.extend([''] * need_to_add)

            rec_list[frag_index] = message_received_bytes
            received_chunks += 1

            if received_chunks == frag_count:
                for ip in clients_ip:
                    if ip == address_ip_client:
                        index = clients_ip.index(ip)
                        name = clients_nickname[index]
                        break

                content = b''.join(rec_list)
                content = content.decode(encoding="ISO-8859-1")
                path_file = convert_string_to_txt(name, content)

                with open(path_file, "r") as arquivo:
                    message = f"{name}: {arquivo.read()}".encode()

                messages.put((message, address_ip_client))

                received_chunks = 0
                rec_list = []

            elif (received_chunks < frag_count) and (frag_index == frag_count - 1):
                print("Houve perda de pacote!")
                received_chunks = 0
                rec_list = []


# Thread para enviar mensagens

def broadcast():
    while True:
        while not messages.empty():
            message_bytes, address_ip_client = messages.get()
            decoded_message = message_bytes.decode(encoding="ISO-8859-1")

            if address_ip_client not in clients_ip:
                name = decoded_message[decoded_message.index(":")+1:]
                clients_ip.append(address_ip_client)
                clients_nickname.append(name)

            for client_ip in clients_ip:
                try:
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        nickname = decoded_message[decoded_message.index(":")+1:]
                        server.sendto(f"{nickname} se juntou, comece a conversar".encode(), client_ip)

                    elif decoded_message.startswith("QUIT_TAG:"):
                        nickname = decoded_message[decoded_message.index(":")+1:]
                        remove_client(client_ip)
                        server.sendto(f"{nickname} saiu da sala!".encode(), client_ip)

                    else:
                        ip = address_ip_client[0]
                        port = address_ip_client[1]
                        message_output = f'{ip}:{port}/~{decoded_message} {get_current_time_and_date()}'
                        server.sendto(message_output.encode(encoding='ISO-8859-1'), client_ip)

                except:
                    remove_client(client_ip)


# Inicia as threads

receive_tread = threading.Thread(target=receive)
broadcast_tread = threading.Thread(target=broadcast)

receive_tread.start()
broadcast_tread.start()
