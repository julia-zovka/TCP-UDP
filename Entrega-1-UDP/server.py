import socket
import queue
import threading
import struct
from datetime import datetime
from zlib import crc32
import math



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



# funcao pra o servidor não mandar mensagem maior que 1024

def fragment_and_send(message_bytes, client_ip):
    frag_size = BUFF_SIZE - 16  # 16 bytes de cabeçalho
    frag_count = math.ceil(len(message_bytes) / frag_size)

    for frag_index in range(frag_count):
        start = frag_index * frag_size
        end = start + frag_size
        fragment_data = message_bytes[start:end]
        actual_size = len(fragment_data)
        crc = crc32(fragment_data)
        header = struct.pack('!IIII', actual_size, frag_index, frag_count, crc)
        packet = header + fragment_data
        server.sendto(packet, client_ip)
# Thread para receber mensagens

def receive():
    fragments = {}
    chunks_count = {}
    expected_chunks = {}

    while True:
        try:
            message_received_bytes, address_ip_client = server.recvfrom(BUFF_SIZE)

            # Mensagens de controle (não fragmentadas)
            decoded_control = message_received_bytes.decode("utf-8", errors="ignore")
            if (decoded_control.startswith("SIGNUP_TAG:") or
                decoded_control.startswith("QUIT_TAG:")):
                messages.put((message_received_bytes, address_ip_client))
                continue

            # Fragmentos 
            header = message_received_bytes[:16]
            fragment = message_received_bytes[16:]
            frag_size, frag_index, frag_count, crc = struct.unpack('!IIII', header)
            
            # Verifica CRC, checar integridade do fragmento
            if crc32(fragment) != crc:
                print(f"[ERRO] Fragmento corrompido (CRC inválido) de {address_ip_client}")
                continue

            # Inicializa listas para o cliente se necessário
            if address_ip_client not in fragments:
                fragments[address_ip_client] = [None] * frag_count
                chunks_count[address_ip_client] = 0
                expected_chunks[address_ip_client] = frag_count

            # armazena os novos frags e verifica se o indice é valido
            if 0 <= frag_index < frag_count:
                if fragments[address_ip_client][frag_index] is None:
                    fragments[address_ip_client][frag_index] = fragment
                    chunks_count[address_ip_client] += 1
                    print(f"[INFO] Fragmento {frag_index+1}/{frag_count} recebido de {address_ip_client}")

            else:
                print(f"[ERRO] Índice de fragmento inválido: {frag_index}/{frag_count}")

            # Se recebeu todos os fragmentos
            if chunks_count[address_ip_client] == expected_chunks[address_ip_client]:
                print(f"[INFO] Todos os {frag_count} fragmentos recebidos de {address_ip_client}")
                content = b''.join(fragments[address_ip_client])
                name = ""
                for ip in clients_ip:
                    if ip == address_ip_client:
                        index = clients_ip.index(ip)
                        name = clients_nickname[index]
                        break


                content_decoded = content.decode("utf-8")
                path_file = convert_string_to_txt(name, content_decoded)

                ## le so a ultima do log
                with open(path_file, "r", encoding="utf-8") as arquivo:
                    lines = arquivo.readlines()
                    last_message=lines[-1].strip() if lines else ""
                    message = f"{name}:{last_message}".encode("utf-8")
                    messages.put((message, address_ip_client))## joga na fila de mensagens


                # Limpa para próxima mensagem
                del fragments[address_ip_client]
                del chunks_count[address_ip_client]
                del expected_chunks[address_ip_client]

        except Exception as e:
            print("Erro ao receber fragmento:", e)
            
# Thread para enviar mensagens

def broadcast():
    while True:
        while not messages.empty():
            message_bytes, address_ip_client = messages.get()
            decoded_message = message_bytes.decode("utf-8")

            ###  tratamento de novo usuario
            if decoded_message.startswith("SIGNUP_TAG:"):
                nickname = decoded_message.split(":", 1)[1]
                if address_ip_client not in clients_ip:
                    clients_ip.append(address_ip_client)
                    clients_nickname.append(nickname)

            ### envia para todos os usuários
            for client_ip in clients_ip:
                try:
                    ### usuário entra na sala
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        nickname = decoded_message.split(":", 1)[1]
                        server.sendto(f"{nickname} se juntou, comece a conversar".encode("utf-8"), client_ip)
                    

                    ### usuário saiu da sala, tira da lista de clientes
                    elif decoded_message.startswith("QUIT_TAG:"):
                        nickname = decoded_message.split(":", 1)[1]
                        if client_ip == address_ip_client:
                            remove_client(client_ip)
                        server.sendto(f"{nickname} saiu da sala!".encode("utf-8"), client_ip)
                    
                    ### se comunicando na sala, mensagens
                    elif ":" in decoded_message:
                            name, msg = decoded_message.split(":", 1)
                            ip, port = address_ip_client
                            message_output = f'{ip}:{port}/~{name}:{msg.strip()} {get_current_time_and_date()}'
                            fragment_and_send(message_output.encode("utf-8"), client_ip)
                    else:
                        print(f"[ERRO] Mensagem inesperada: {decoded_message}")      
                except Exception as e:
                    print(f"Erro ao enviar mensagem para {client_ip}: {e}")

# Inicia as threads

receive_tread = threading.Thread(target=receive)
broadcast_tread = threading.Thread(target=broadcast)

receive_tread.start()
broadcast_tread.start()