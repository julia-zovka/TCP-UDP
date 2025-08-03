import socket
import random
import threading #cria threads, importante para programação paralela
import math
import struct #interpretar e montar a estrututra dos pacotes 
from zlib import crc32
from server import convert_string_to_txt


import utils.constants as c
from utils.folder_management import delete_folder
from utils.sending_pkts import send_packet
import utils.variables as g


# atribui uma porta aleatória ao cliente

CLIENT_PORT = random.randint(1000, 9998)

# cria socket UDP e dá bind usando o IP do servidor e a porta local
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.bind((c.SERVER_IP, CLIENT_PORT))


##### variabeis globais
seq_num_client = 0 # Número de sequência do pacote enviado pelo cliente
ack_to_send = 0 # Número de reconhecimento do pacote enviado pelo servidor 
client_ip = None 
nickname = None
message_buffer = ''


# Funcao de apresentacao simples

def apresentacao():
    nome = input("Qual é o seu nome? \n")
    print(f"\nOi {nome}, tudo bem?")
    print("\nPara entrar na sala, digite:")
    print(f"' hi, meu nome eh {nome} '")
    print("\nPara sair da sala, digite:")
    print("' bye ' \n")
    return nome, f"hi, meu nome eh {nome}"



# Funcao para receber mensagens

def receive():
    global client, seq_num_client, ack_to_send, client_ip, nickname, is_conected, message_buffer

    buffer = {}
    
    while True:
        try:
            if nickname:
                    delete_folder(c.DATA_FOLDER_PATH, nickname)
        
            data, _ = client.recvfrom(c.BUFF_SIZE)

                # ve se mensagens entrada/saída
            try:
                text   = data.decode("utf-8")
                if "se juntou" in text or "saiu da sala" in text:
                    print(text.strip())
                    continue
            except:
                    pass 
            header   = data[:c.HEADER_SIZE]
            fragment = data[c.HEADER_SIZE:]

                # Processa fragmento
            size, index, total, seq_num, ack_num, crc = struct.unpack("!IIIIII", header)


            if crc32(fragment) != crc:
                print("[ERRO] Fragmento corrompido (CRC inválido)")
                continue
            decoded = fragment.decode("utf-8", errors="ignore")

            # pacotes de controle -> handshake e ACK
            if decoded in ("SYN-ACK", "FYN-ACK", "ACK"):
                if ack_num != seq_num_client or crc32(fragment) != crc:
                    # descarta pacote corrompido ou fora de ordem
                    continue
                g.ACK_RECEIVED = True
                if decoded == "SYN-ACK":
                    is_conected = True
                elif decoded == "FYN-ACK":
                    is_conected = False
                if decoded == "ACK":
                    seq_num_client = 1 - seq_num_client
                    continue


            if decoded == "SYN-ACK":
                g.ACK_RECEIVED = True
                is_conected    = True

                # 2) envia o SIGNUP_TAG guardado
                send_packet(
                    message_buffer,
                    client,
                    c.SERVER_PORT,
                    client_ip,
                    nickname,
                    seq_num_client,
                    ack_to_send
                )
                # 3) envia o ACK final
                send_packet(
                    "ACK",
                    client,
                    c.SERVER_PORT,
                    client_ip,
                    nickname,
                    seq_num_client,
                    ack_to_send
                )
                seq_num_client = 1 - seq_num_client
                continue

            elif decoded == "FYN-ACK":
                g.ACK_RECEIVED = True
                is_conected    = False

                # 2) envia o QUIT_TAG guardado
                send_packet(
                    message_buffer,
                    client,
                    c.SERVER_PORT,
                    client_ip,
                    nickname,
                    seq_num_client,
                    ack_to_send
                )
                # 3) envia o ACK final
                send_packet(
                    "ACK",
                    client,
                    c.SERVER_PORT,
                    client_ip,
                    nickname,
                    seq_num_client,
                    ack_to_send
                )
                seq_num_client = 1 - seq_num_client
                continue

                # Inicializa buffer da mensagem se necessário para reconstruir e guardar nas posiscoes certas
            if "frags" not in buffer:
                    buffer["frags"] = [None] * total
                    buffer["recebidos"] = 0

                # Armazena fragmento
            if buffer["frags"][index] is None:
                    buffer["frags"][index] = fragment
                    buffer["recebidos"] += 1

                # Se recebeu todos, junta e imprime
            if buffer["recebidos"] == total:
                    msg = b''.join(buffer["frags"]).decode("utf-8", errors="ignore")
                    print(msg)
                    
                    # envia ACK de confirmacao
                    send_packet(
                    '',
                    client,
                    c.SERVER_PORT,
                    client_ip,
                    nickname,
                    seq_num_client,
                    ack_to_send
                )
                # alterna bit de ACK
                    ack_to_send = 1 - ack_to_send
                    buffer.clear()  # Limpa para próxima mensagem

        except Exception as e:
            print(f"[ERRO NO CLIENTE] Falha ao receber mensagem: {e}")
        


# Inicia thread de recebimento

receive_thread = threading.Thread(target=receive, daemon=True)
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

    # inicia handshake de entrada SYN -> SYN-ACK -> SIGNUP_TAG -> ACK
    if message.startswith("hi, meu nome eh ") and not is_conected:
            nickname       = message[16:]
            message_buffer = f"SIGNUP_TAG:{nickname}"
            send_packet(
                "SYN",
                client,
                c.SERVER_PORT,
                client_ip,
                nickname,
                seq_num_client,
                ack_to_send
            )
            # alterna bit de seq de controle
            seq_num_client = 1 - seq_num_client

        #  inicia handshake de saida FYN > FYN-ACK > ACK
    elif message == "bye" and is_conected:
            message_buffer = f"QUIT_TAG:{nickname}"
            send_packet(
                "FYN",
                client,
                c.SERVER_PORT,
                client_ip,
                nickname,
                seq_num_client,
                ack_to_send
            )
            seq_num_client = 1 - seq_num_client
            print("Você não está mais conectado à sala!, até a próxima")

    
    elif not is_conected:
            print("Comando inválido!")

        # envia mensagem de usuario
    else:
            temp_file = convert_string_to_txt(nickname, message)
            send_packet(
                message,
                client,
                c.SERVER_PORT,
                client_ip,
                nickname,
                seq_num_client,
                ack_to_send
            )

        