import socket
import random
import threading
import math
import struct
import time
import sys
import os

# Adiciona o diretório utils ao path para importar o checksum
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from utils.checksum import find_checksum, verify_checksum

# Configuracoes do servidor
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFF_SIZE = 1024
TIMEOUT = 1.0
MAX_RETRIES = 20

# Cria o socket  e atribi uma porta aleatória a ele
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.bind((SERVER_IP, random.randint(1000, 9998)))

# Eventos/estado de ACK (para o remetente cliente aguardar ACK do servidor)
ack_lock = threading.Lock()
ack_event = {0: threading.Event(), 1: threading.Event()}  # duas seq (0/1)

# Sequências
next_seq_send = 0       # lado remetente (cliente p servidor)
expected_seq_recv = 0   # lado receptor (servidor p cliente)
last_good_seq = 1       # para ACK duplicado


# funcao de apresentação

def apresentacao():
    nome = input("Digite seu nome: ")
    print(f"Oi {nome}, tudo bem?")
    print("\nPara entrar na sala, digite:")
    print(f"' hi, meu nome eh {nome} '")
    print("\nPara sair da sala, digite:")
    print("' bye ' \n")
    return nome, f"hi, meu nome eh {nome}"


### funçoes que tratam do desempacotamento e empacotamento do pacote

def _make_header(fragment_data, frag_index, frag_count, seq):
    actual_size = len(fragment_data)
    checksum = find_checksum(fragment_data)
    header = struct.pack('!IIIII', actual_size, frag_index, frag_count, checksum, seq)
    return header

def _parse_header(data):
    if len(data) >= 20:
        try:
            size, index, total, cks, seq = struct.unpack('!IIIII', data[:20])
            payload = data[20:]
            return size, index, total, cks, seq, payload, 20
        except Exception:
            pass
    size, index, total, cks = struct.unpack('!IIII', data[:16])
    payload = data[16:]
    seq = None
    return size, index, total, cks, seq, payload, 16

def _send_ack(seq_to_ack):
    ack_msg = f"ACK:{seq_to_ack}".encode("utf-8")
    client.sendto(ack_msg, (SERVER_IP, SERVER_PORT))
    

def _wait_ack(seq):
    ev = ack_event[seq]
    got = ev.wait(TIMEOUT)
    return got

def _register_ack(seq):
    ev = ack_event.get(seq)
    if ev:
        ev.set()

def _clear_ack(seq):
    ev = ack_event.get(seq)
    if ev:
        ev.clear()


### funcao de recebimento de mensagens dos outros cliente e de acks
def receive():
    global expected_seq_recv, last_good_seq

    buffer = {}  # armazena frag para remontar msg do servidor

    while True:
        try:
            data, _ = client.recvfrom(BUFF_SIZE)

            # decodificar como texto simples (mensagens de controle)
            try:
                text = data.decode("utf-8", errors="strict")
                
                # ACKs do servidor
                if text.startswith("ACK:"):
                    try:
                        seq_ack = int(text.split(":", 1)[1])
                        _register_ack(seq_ack)
                        continue
                    except Exception:
                        pass

                # Mensagens simples (signup/quit/ping)
                if ("se juntou" in text or "saiu da sala" in text or 
                    text.strip() == "PING" or len(text.strip()) < 50):
                    if text.strip() and text.strip() != "PING":
                        print(text.strip())
                    continue
                    
            except UnicodeDecodeError:
                # Se não conseguir decodificar como texto, é um pacote binário
                pass
            except Exception as e:
                # Outros erros de decodificação, tenta como pacote
                pass

            # Se chegou aqui, deve ser um pacote fragmentado binário
            try:
                # Verifica se tem tamanho mínimo para ser um cabeçalho
                if len(data) < 16:
                    print(f"[ERRO NO CLIENTE] Pacote muito pequeno: {len(data)} bytes")
                    continue
                    
                size, index, total, cks, seq, fragment, hdr_len = _parse_header(data)
                
                #  calculo checksum 
                if not verify_checksum(fragment, cks) or size != len(fragment):
                    # pacote corrompido -> ACK do último bom
                    _send_ack(last_good_seq)
                    continue

                # Verifica sequence number  é o esperado
                if seq is not None:
                    if seq == expected_seq_recv:
                        # Sequência correta -> envia ACK e alterna esperado
                        _send_ack(seq)
                        last_good_seq = seq
                        expected_seq_recv = 1 - expected_seq_recv
                    else:
                        # Seq incorreto (duplicata ou fora de ordem) -> ACK duplicado
                        _send_ack(last_good_seq)
                        continue
                else:
                    # Pacote legado sem seq -> aceita e envia ACK fixo
                    _send_ack(0)

            except struct.error as e:
                print(f"[ERRO NO CLIENTE] Erro ao fazer parse do cabeçalho: {e}")
                print(f"[DEBUG] Dados recebidos: {data[:50]}...")
                continue
            except Exception as e:
                print(f"[ERRO NO CLIENTE] Erro geral ao processar pacote: {e}")
                continue

            # Inicializa buffer se necessário (só para pacotes fragmentados válidos)
            if "frags" not in buffer:
                buffer["frags"] = [None] * total
                buffer["recebidos"] = 0
                buffer["total"] = total

            # Armazena fragmento
            if 0 <= index < total:
                if buffer["frags"][index] is None:
                    buffer["frags"][index] = fragment
                    buffer["recebidos"] += 1

            # Se recebeu todos, imprime
            if buffer.get("recebidos", 0) == buffer.get("total", 1):
                msg = b''.join(buffer["frags"]).decode("utf-8")
                print(msg)
                buffer.clear()

        except Exception as e:
            print(f"[ERRO NO CLIENTE] Falha ao receber mensagem: {e}")



### conversao pra txt, salva a ultima mensgem do cliente

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(message)
    return filename

## função para criação dos fragmentos, importante para mensagens longas
def create_fragment(contents, frag_size, frag_index, frag_count, seq):
    start = frag_index * frag_size
    end = start + frag_size
    fragment_data = contents[start:end]
    header = _make_header(fragment_data, frag_index, frag_count, seq)
    return header + fragment_data



receive_thread = threading.Thread(target=receive, daemon=True)
receive_thread.start()

# Loop principal
is_conected = False

# Executa apresentacao
nickname, hello = apresentacao()

while True:
    message = input()

    if message.strip() == "":
        continue

    client_ip = client.getsockname()[0]

    if message.startswith("hi, meu nome eh "):
        if is_conected:
            print("Calma jovem, você já está conectado à sala!")
        else:
            nickname = message[16:]
            is_conected = True
            client.sendto(f"SIGNUP_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))

    elif message == "bye":
        if not is_conected:
            print("Você não está conectado à sala! para sair precisa entrar chefe!")
        else:
            client.sendto(f"QUIT_TAG:{nickname}".encode(), (SERVER_IP, SERVER_PORT))
            print("Você não está  mais conectado à sala! até a próxima!!")
            is_conected = False

    elif is_conected:
        # Envio confiável (stop-and-wait por fragmento)
        temp_file = convert_string_to_txt(nickname, message)
        with open(temp_file, "rb") as file:
            contents = file.read()

        frag_size = BUFF_SIZE - 20  # 20 bytes de cabeçalho (com seq)// os pacotes de ack foram tratados de forma separada
        frag_count = math.ceil(len(contents) / frag_size)

        for frag_index in range(frag_count):
            tries = 0
            while True:
                tries += 1
                seq = next_seq_send
                fragment = create_fragment(contents, frag_size, frag_index, frag_count, seq)
                # limpa evento do ACK esperado
                _clear_ack(seq)
                # envia
                client.sendto(fragment, (SERVER_IP, SERVER_PORT))
                # espera ACK
                if _wait_ack(seq):
                    next_seq_send = 1 - next_seq_send
                    break
                else:
                    print(f"[TIMEOUT] Sem ACK para seq={seq} (frag {frag_index+1}), reenviando...")

                if tries >= MAX_RETRIES:
                    print("[ERRO] Limite de retransmissões atingido. Abortando envio da mensagem.")
                    break
    else:
        print("Comando inválido! Para entrar na sala, digite 'hi, meu nome eh {nome}' ou 'bye' para sair.")
