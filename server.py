import socket
import queue
import threading
import struct
from datetime import datetime
from zlib import crc32



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


# Funcao para salvar mensagem em .txt é para guardar o histórico das mensagens recebidas pelo servidor e fazer um log de toda conversa da sala

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}_server_log.txt"
    with open(filename, "a", encoding="utf-8") as file:
        file.write(message + "\n")
    return filename


# Funcao para pegar data e hora atual

def get_current_time_and_date():
    now = datetime.now()
    return now.strftime("%H:%M:%S %d/%m/%Y")


# Funcao para remover cliente ao sair da sala

def remove_client(client):
    index_client = clients_ip.index(client)
    clients_ip.remove(client)
    clients_nickname.pop(index_client)


# Thread para receber mensagens

def receive():
    fragments = {}
    chunks_count = {}
    expected_chunks = {}

    while True:
        try:
            message_received_bytes, address_ip_client = server.recvfrom(BUFF_SIZE)

            # Mensagens de controle (não fragmentadas)
            if (message_received_bytes.decode(errors="ignore").startswith("SIGNUP_TAG:") or
                message_received_bytes.decode(errors="ignore").startswith("QUIT_TAG:")):
                messages.put((message_received_bytes, address_ip_client))
                continue

            # Fragmentos
            header = message_received_bytes[:16]
            fragment = message_received_bytes[16:]
            frag_size, frag_index, frag_count, crc = struct.unpack('!IIII', header)

            # Inicializa listas para o cliente se necessário
            if address_ip_client not in fragments:
                fragments[address_ip_client] = [b''] * frag_count
                chunks_count[address_ip_client] = 0

            fragments[address_ip_client][frag_index] = fragment
            chunks_count[address_ip_client] += 1

            # Se recebeu todos os fragmentos
            if chunks_count[address_ip_client] == frag_count:
                content = b''.join(fragments[address_ip_client])
                name = ""
                for ip in clients_ip:
                    if ip == address_ip_client:
                        index = clients_ip.index(ip)
                        name = clients_nickname[index]
                        break

                content_decoded = content.decode(encoding="ISO-8859-1")
                path_file = convert_string_to_txt(name, content_decoded)

                with open(path_file, "r", encoding="utf-8") as arquivo:
                    lines = arquivo.readlines()
                    last_message=lines[-1].strip() if lines else ""
                    message = f"{name}: {last_message}".encode(encoding="ISO-8859-1")
                    messages.put((message, address_ip_client))


                # Limpa para próxima mensagem
                del fragments[address_ip_client]
                del chunks_count[address_ip_client]

        except Exception as e:
            print("Erro ao receber fragmento:", e)
            
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
                    ### usuário entra na sala
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        nickname = decoded_message[decoded_message.index(":")+1:]
                        server.sendto(f"{nickname} se juntou, comece a conversar".encode(), client_ip)

                    ### usuário saiu da sala, tira da lista de clientes
                    elif decoded_message.startswith("QUIT_TAG:"):
                        nickname = decoded_message[decoded_message.index(":")+1:]
                        remove_client(client_ip)
                        server.sendto(f"{nickname} saiu da sala!".encode(), client_ip)
                    
                    ### se comunicando na sala
                    else:
                        ip = address_ip_client[0]
                        port = address_ip_client[1]
                        message_output = f'{ip}:{port}/~{decoded_message} {get_current_time_and_date()}'
                        resposta = message_output.encode(encoding='ISO-8859-1')
                        for i in range(0, len(resposta), BUFF_SIZE):
                            server.sendto(resposta[i:i+BUFF_SIZE], client_ip)
                except:
                    remove_client(client_ip)


# Inicia as threads

receive_tread = threading.Thread(target=receive)
broadcast_tread = threading.Thread(target=broadcast)

receive_tread.start()
broadcast_tread.start()
