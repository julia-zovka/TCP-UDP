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
ack_expected = 0 # Número de reconhecimento do pacote esperado no  servidor 
client_ip = None 
nickname = None
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



# Funcao para receber mensagens

def receive():
    buffer = {}
    global ack_to_send
    
    while True:
        try:
            data, _ = client.recvfrom(BUFF_SIZE)

            # ve se mensagens entrada/saída
            try:
                text = data.decode("utf-8")
                if "se juntou" in text or "saiu da sala" in text:
                    print(text.strip())
                    continue
            except:
                pass 

            # Processa fragmento
            header, fragment = data[:16], data[16:]
            size, index, total, crc = struct.unpack("!IIII", header)

            if crc32(fragment) != crc:
                print("[ERRO] Fragmento corrompido (CRC inválido)")
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
                msg = b''.join(buffer["frags"]).decode("utf-8")
                print(msg)
                buffer.clear()  # Limpa para próxima mensagem

        except Exception as e:
            print(f"[ERRO NO CLIENTE] Falha ao receber mensagem: {e}")
    

# Funcao para criar arquivo .txt, so guarda a mensagem mais recente

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename


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
            print("Você não está conectado à sala! para sair precisa entrar chefe!")
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



















import socket
import struct
import threading
from utils.sending_pkts import send_packet
from utils.checksum import find_checksum
from utils.constants import SERVER_IP, SERVER_PORT, BUFF_SIZE, HEADER_SIZE

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.bind((SERVER_IP, 0))  # Usa uma porta aleatória

seq_num_client = 0  # número de sequência para envio
ack_expected = 0    # número de sequência esperado do servidor

client_ip = client.getsockname()[0]
nickname = input("Digite seu nickname: ").strip()

print("\nPara entrar na sala, digite:\n  hi, meu nome eh <nickname>")
print("Para sair, digite:\n  bye\n")

# Função para receber mensagens
def receive():
    global ack_expected
    buffer = {}
    
    while True:
        try:
            data, _ = client.recvfrom(BUFF_SIZE)
            header = data[:HEADER_SIZE]
            fragment = data[HEADER_SIZE:]

            frag_size, frag_index, frag_count, seq_num, ack_num, checksum = struct.unpack('!IIIIII', header)

            header_no_checksum = struct.pack('!IIIII', frag_size, frag_index, frag_count, seq_num, ack_num)
            data_for_checksum = header_no_checksum + fragment
            checksum_check = find_checksum(data_for_checksum)

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
            print(f"[ERRO] {e}")

# Thread para receber mensagens
threading.Thread(target=receive, daemon=True).start()

# Loop principal de envio
while True:
    try:
        msg = input()
        if msg.strip() == "":
            continue
        send_packet(msg, client, (SERVER_IP, SERVER_PORT), client_ip, nickname, seq_num_client, ack_expected)
        seq_num_client = 1 - seq_num_client
    except KeyboardInterrupt:
        print("Encerrando cliente.")
        break
