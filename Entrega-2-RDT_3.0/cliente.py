import socket
import random
import threading #cria threads, importante para programação paralela
import math
import struct #interpretar e montar a estrututra dos pacotes 
from zlib import crc32


from utils.checksum import find_checksum
from utils.sending_pkts import send_packet
import utils.constants as g 


# Configuracoes do servidor

SERVER_IP =g.SERVER_IP
SERVER_PORT =g.SERVER_PORT
BUFF_SIZE=g.BUFF_SIZE

# Cria o socket  e atribi uma porta aleatória a ele

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#afnet--- ipv4
#sockdgram----socket udp
client.bind((SERVER_IP, random.randint(1000, 9998)))

##### variabeis globais
seq_num_client = 0 # Número de sequência para enviar pacote  pelo cliente
ack_expected = 0 # Número de sequencia do pacote esperado que o  servidor  manda
client_ip = None 
nickname = None
is_conected=False
message_buffer = ''


# Funcao de apresentacao simples

def apresentacao():
    nome = input("Digite seu nome: ")
    print(f"Oi, tudo bem?")
    print("\nPara entrar na sala, digite:")
    print(f"' hi, meu nome eh {nome} '")
    print("\nPara sair da sala, digite:")
    print("' bye ' \n")
    return nome, f"hi, meu nome eh {nome}"


# Funcao para criar arquivo .txt, so guarda a mensagem mais recente

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename


# Funcao para receber mensagens

def receive():
    buffer = {}
    global ack_expected
    
    while True:
        try:
            data, _ = client.recvfrom(BUFF_SIZE)
            header = data[:g.HEADER_SIZE]
            fragment = data[g.HEADER_SIZE:]

            ## desempacotando para fazer o checksum
            frag_size, frag_index, frag_count, seq_num, ack_num, checksum = struct.unpack('!IIIIII', header)

            header_no_checksum = struct.pack('!IIIII', frag_size, frag_index, frag_count, seq_num, ack_num)
            data_for_checksum = header_no_checksum + fragment
            checksum_check = find_checksum(data_for_checksum)

            print(f"[DEBUG CLIENTE] Recebido ACK: seq_r={seq_num}, ack_r={ack_num}, esperado={seq_num}")


            if checksum != checksum_check or seq_num != ack_expected:
                print("[ERRO] Pacote corrompido ou fora de ordem, reenviando ACK anterior")
                send_packet('', client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, 1 - ack_expected)
                continue

            # Monta o buffer por fragmento
            if "frags" not in buffer:
                buffer["frags"] = [None] * frag_count
                buffer["recebidos"] = 0

            if buffer["frags"][frag_index] is None:
                buffer["frags"][frag_index] = fragment
                buffer["recebidos"] += 1

            # Se completou todos os fragmentos
            if buffer["recebidos"] == frag_count:
                msg = b''.join(buffer["frags"]).decode("utf-8", errors="ignore")
                print(msg)
                send_packet('', client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, ack_expected)
                ack_expected = 1 - ack_expected
                buffer.clear()

        except Exception as e:
            print(f"[ERRO NO CLIENTE] Falha ao receber mensagem: {e}")
    


# Inicia thread de recebimento

receive_thread = threading.Thread(target=receive)
receive_thread.start()


# Executa apresentacao
nickname, hello = apresentacao()

# Loop de envio
while True:
    message = input()

    if message.strip() == "":
        continue  # ignora mensagens vazias

    if message.startswith("hi, meu nome eh ") and not is_conected:
        # Extrai nickname da mensagem e entra na sala
        nickname = message.split("hi, meu nome eh ")[1].strip()
        is_conected = True
        convert_string_to_txt(nickname, message)
        send_packet(message, client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, ack_expected)
        seq_num_client = 1 - seq_num_client

    elif message.strip().lower() == "bye" and is_conected:
        # Sai da sala
        print("Você saiu da sala, até uma próxima.")
        convert_string_to_txt(nickname, message)
        send_packet(message, client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, ack_expected)
        break

    elif not is_conected:
        # Tentou mandar outra mensagem sem ter se conectado
        print(" Você precisa entrar na sala primeiro")

    else:
        # Envia mensagem normal após conexão
        convert_string_to_txt(nickname, message)
        send_packet(message, client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, ack_expected)
        seq_num_client = 1 - seq_num_client



#### erross não tá dando comnado invalido antes de se conectar a salaaa
