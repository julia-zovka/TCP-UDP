import socket
import queue
import threading
import struct
from datetime import datetime
import math
import time
import sys
import os

# Adiciona o diretório utils ao path para importar o checksum
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from utils.checksum import find_checksum, verify_checksum


# Configuracoes do servidor
SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000
BUFF_SIZE = 1024
TIMEOUT = 1.0  
MAX_RETRIES = 20  # limite de tentativas (evitar loop infinito)
CLEANUP_INTERVAL = 30  # segundos para limpeza de clientes inativos

# Inicializacao
messages = queue.Queue()
clients_ip = []
clients_nickname = []

# para o servidor esperar ACKs enviados pelos clientes
ack_lock = threading.Lock()
ack_events = {}  # chave: (client_addr, seq) 

# Controle de sequência esperado por cliente (lado receptor no servidor)
expected_seq_recv = {}  # chave: client_addr -> 0/1

# Controle de sequência de envio por cliente (lado remetente no servidor)
next_seq_send = {}  # chave: client_addr -> 0/1

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))

# utils

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}_server_log.txt"
    with open(filename, "a", encoding="utf-8") as file:
        file.write(message + "\n")
    return filename

def get_current_time_and_date():
    now = datetime.now()
    return now.strftime("%H:%M:%S %d/%m/%Y")

def remove_client(client):
    index_client = clients_ip.index(client)
    clients_ip.remove(client)
    clients_nickname.pop(index_client)
    # Limpa estados RDT desse cliente
    expected_seq_recv.pop(client, None)
    next_seq_send.pop(client, None)
    # Limpa eventos pendentes
    with ack_lock:
        for k in [k for k in ack_events.keys() if k[0] == client]:
            ack_events.pop(k, None)


### funçoes que tratam do desempacotamento e empacotamento do pacote

def _make_data_header(fragment_data, frag_index, frag_count, seq):
    # Agora o cabeçalho tem 20 bytes para carregar o seq:
    # '!IIIII' -> [size, index, count, crc, seq]
    actual_size = len(fragment_data)
    checksum = find_checksum(fragment_data)
    header = struct.pack('!IIIII', actual_size, frag_index, frag_count, checksum, seq)
    return header

def _parse_header(data):
    # Tenta o cabeçalho novo de 20 bytes; se falhar, tenta o antigo de 16 (compat)
    if len(data) >= 20:
        try:
            size, index, total, cks, seq = struct.unpack('!IIIII', data[:20])
            payload = data[20:]
            return size, index, total, cks, seq, payload, 20
        except Exception:
            pass
    # fallback para compatibilidade (sem seq) — tratamos como seq esperado (não alterna)
    size, index, total, cks = struct.unpack('!IIII', data[:16])
    payload = data[16:]
    seq = None
    return size, index, total, cks, seq, payload, 16

def _send_ack(addr, seq_to_ack):
    # ACK como texto simples para simplificar coordenação entre threads
    ack_msg = f"ACK:{seq_to_ack}".encode("utf-8")
    server.sendto(ack_msg, addr)
    print(f"[RDT] -> Enviado ACK {seq_to_ack} para {addr}")

def _wait_for_ack(addr, seq):
    key = (addr, seq)
    with ack_lock:
        if key not in ack_events:
            ack_events[key] = threading.Event()
        ev = ack_events[key]
        # Limpa o evento antes de esperar para evitar restos de ACKs antigos
        ev.clear()
    got = ev.wait(TIMEOUT)
    # Limpa o evento após uso para evitar conflitos futuros
    with ack_lock:
        if key in ack_events:
            ack_events.pop(key, None)
    return got

def _register_ack_received(addr, seq):
    key = (addr, seq)
    with ack_lock:
        if key in ack_events:
            ack_events[key].set()
        # Se não existe o evento, significa que já foi processado ou timeout


##criacao dos fragmentacao das mensagens para serem enviadas

def fragment_and_send(message_bytes, client_ip):

    # Verifica se o cliente ainda está na lista antes de enviar
    if client_ip not in clients_ip:
        print(f"[SKIP] Cliente {client_ip} não está mais conectado. Pulando envio.")
        return
        
    if client_ip not in next_seq_send:
        next_seq_send[client_ip] = 0

    frag_size = BUFF_SIZE - 20  # 20 bytes de cabeçalho (com seq)
    frag_count = math.ceil(len(message_bytes) / frag_size)

    for frag_index in range(frag_count):
        # Verifica novamente se o cliente ainda está conectado
        if client_ip not in clients_ip:
            print(f"[ABORT] Cliente {client_ip} desconectou durante envio. Abortando.")
            return
            
        start = frag_index * frag_size
        end = start + frag_size
        fragment_data = message_bytes[start:end]

        seq = next_seq_send[client_ip]
        header = _make_data_header(fragment_data, frag_index, frag_count, seq)
        packet = header + fragment_data

        # Envia com retransmissão até receber ACK correto
        tries = 0
        while True:
            # Verifica se cliente ainda está conectado antes de cada tentativa
            if client_ip not in clients_ip:
                print(f"[ABORT] Cliente {client_ip} desconectou durante retransmissão. Abortando.")
                return
                
            tries += 1
            print(f"[RDT] -> Enviando frag {frag_index+1}/{frag_count} para {client_ip} (seq={seq}, tentativa={tries})")
            
            try:
                server.sendto(packet, client_ip)
            except socket.error as e:
                error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                if error_code == 10054:  # Cliente desconectou
                    print(f"[DISCONNECT] Cliente {client_ip} desconectou durante envio. Removendo da lista.")
                    if client_ip in clients_ip:
                        remove_client(client_ip)
                    return
                else:
                    print(f"[ERRO] Erro ao enviar para {client_ip}: {e}")
                    
            if _wait_for_ack(client_ip, seq):
                print(f"[RDT] <- ACK {seq} recebido de {client_ip} para frag {frag_index+1}/{frag_count}")
                # Alterna sequência após ACK correto
                next_seq_send[client_ip] = 1 - next_seq_send[client_ip]
                break
            else:
                print(f"[TIMEOUT] Sem ACK para seq={seq} (frag {frag_index+1}), retransmitindo...")

            if tries >= MAX_RETRIES:
                print(f"[ERRO] Limite de retransmissões atingido para {client_ip}. Removendo cliente.")
                if client_ip in clients_ip:
                    remove_client(client_ip)
                return

def cleanup_disconnected_clients():
    """Função para limpar clientes desconectados periodicamente"""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        
        disconnected_clients = []
        for client_addr in list(clients_ip):
            try:
                # Tenta enviar um "ping" pequeno para verificar conectividade
                ping_msg = b"PING"
                server.sendto(ping_msg, client_addr)
            except socket.error as e:
                error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                if error_code == 10054:  # Cliente desconectado
                    disconnected_clients.append(client_addr)
                    
        # Remove clientes desconectados
        for client_addr in disconnected_clients:
            if client_addr in clients_ip:
                idx = clients_ip.index(client_addr)
                nickname = clients_nickname[idx]
                print(f"[CLEANUP] Removendo cliente inativo: {nickname} ({client_addr})")
                remove_client(client_addr)



### thread de recebimento de mensagens

def receive():
    # buffers por cliente
    fragments = {}       
    chunks_count = {}    
    expected_chunks = {} 
    last_good_seq = {}   

    while True:
        try:
            data, address_ip_client = server.recvfrom(BUFF_SIZE)

            # Tenta decodificar como controle textual
            decoded_control = None
            try:
                decoded_control = data.decode("utf-8", errors="strict")
            except Exception:
                decoded_control = None

            if decoded_control:
                # registro de ACK vindo do cliente (para servidor liberar retransmissão)
                if decoded_control.startswith("ACK:"):
                    try:
                        seq_ack = int(decoded_control.split(":", 1)[1])
                        print(f"[RDT] <- ACK {seq_ack} recebido de {address_ip_client}")
                        _register_ack_received(address_ip_client, seq_ack)
                        continue
                    except Exception:
                        pass

                if decoded_control.startswith("SIGNUP_TAG:") or decoded_control.startswith("QUIT_TAG:"):
                    messages.put((data, address_ip_client))
                    continue

            # Se chegou aqui, é pacote de dados (fragmento)
            size, index, total, cks, seq, payload, hdr_len = _parse_header(data)

            # Se ainda não havia seq esperado para esse cliente, inicia
            if address_ip_client not in expected_seq_recv:
                expected_seq_recv[address_ip_client] = 0
                last_good_seq[address_ip_client] = 1  # assim, se duplicar 0, reenviamos ACK do último bom (1)

            # Verifica checksum
            if not verify_checksum(payload, cks) or size != len(payload):
                print(f"[RDT] Pacote corrompido de {address_ip_client} (frag {index+1}/{total}). Reenviando ACK do último bom.")
                _send_ack(address_ip_client, last_good_seq[address_ip_client])
                continue

            # Verifica seq esperado
            exp = expected_seq_recv[address_ip_client]
            if seq is None:
                # Pacote sem seq no header — aceitamos como se estivesse correto, mas SEM alternância
                # Ainda assim montamos e replicamos para manter compatibilidade mínima
                print(f"[RDT][LEGADO] Recebido frag {index+1}/{total} sem seq explícito de {address_ip_client}.")
                # Envia ACK "fixo" (0) para destravar quem estiver esperando
                _send_ack(address_ip_client, 0)
            else:
                if seq != exp:
                    print(f"[RDT] Seq inesperado de {address_ip_client}. Esperado={exp}, recebido={seq}. ACK duplicado do último bom.")
                    _send_ack(address_ip_client, last_good_seq[address_ip_client])
                    continue
                # Seq ok -> ACK e alterna esperado
                _send_ack(address_ip_client, seq)
                last_good_seq[address_ip_client] = seq
                expected_seq_recv[address_ip_client] = 1 - expected_seq_recv[address_ip_client]

            # Inicializa buffers para esse cliente (para remontagem)
            if address_ip_client not in fragments:
                fragments[address_ip_client] = [None] * total
                chunks_count[address_ip_client] = 0
                expected_chunks[address_ip_client] = total

            # Armazena fragmento se ainda não recebido
            if 0 <= index < total:
                if fragments[address_ip_client][index] is None:
                    fragments[address_ip_client][index] = payload
                    chunks_count[address_ip_client] += 1
                    print(f"[INFO] Fragmento {index+1}/{total} recebido de {address_ip_client}")
            else:
                print(f"[ERRO] Índice de fragmento inválido: {index}/{total}")

            # Se recebeu todos os fragmentos, produz mensagem para broadcast
            if chunks_count[address_ip_client] == expected_chunks[address_ip_client]:
                print(f"[INFO] Todos os {total} fragmentos recebidos de {address_ip_client}")
                content = b''.join(fragments[address_ip_client])
                name = ""
                for ip in clients_ip:
                    if ip == address_ip_client:
                        index_cli = clients_ip.index(ip)
                        name = clients_nickname[index_cli]
                        break

                content_decoded = content.decode("utf-8")
                path_file = convert_string_to_txt(name, content_decoded)

                # lê só a última linha do log
                with open(path_file, "r", encoding="utf-8") as arquivo:
                    lines = arquivo.readlines()
                    last_message = lines[-1].strip() if lines else ""
                    message = f"{name}:{last_message}".encode("utf-8")
                    messages.put((message, address_ip_client))

                # limpa buffers
                del fragments[address_ip_client]
                del chunks_count[address_ip_client]
                del expected_chunks[address_ip_client]

        except socket.error as e:
            # Trata erros específicos de socket (cliente desconectado, etc)
            error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
            if error_code == 10054:  # WSAECONNRESET - Conexão resetada pelo peer
                print(f"[REDE] Cliente desconectou abruptamente: {e}")
                # Remove clientes desconectados da lista
                disconnected_clients = []
                for client_addr in list(clients_ip):
                    try:
                        # Tenta um envio de teste para verificar se o cliente ainda está ativo
                        test_msg = b"test"
                        server.sendto(test_msg, client_addr)
                    except socket.error:
                        disconnected_clients.append(client_addr)
                        
                for client_addr in disconnected_clients:
                    if client_addr in clients_ip:
                        print(f"[CLEANUP] Removendo cliente desconectado: {client_addr}")
                        remove_client(client_addr)
            else:
                print(f"[REDE] Erro de socket: {e}")
        except Exception as e:
            print(f"[ERRO] Erro geral ao receber fragmento: {e}")
            import traceback
            traceback.print_exc()



### funcao de broadcast para repassar a mensagem pra todos os cliente conectados

def broadcast():
    while True:
        while not messages.empty():
            message_bytes, address_ip_client = messages.get()
            decoded_message = message_bytes.decode("utf-8")

            # tratamento de novo usuario
            if decoded_message.startswith("SIGNUP_TAG:"):
                nickname = decoded_message.split(":", 1)[1]
                if address_ip_client not in clients_ip:
                    clients_ip.append(address_ip_client)
                    clients_nickname.append(nickname)
                    # zera estados RDT desse cliente
                    next_seq_send[address_ip_client] = 0
                    expected_seq_recv[address_ip_client] = 0

            for client_ip in list(clients_ip):
                try:
                    # Verifica se o cliente ainda está conectado antes de enviar
                    if client_ip not in clients_ip:
                        continue
                        
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        nickname = decoded_message.split(":", 1)[1]
                        try:
                            server.sendto(f"{nickname} se juntou, comece a conversar\n".encode("utf-8"), client_ip)
                        except socket.error as e:
                            error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                            if error_code == 10054:
                                print(f"[BROADCAST] Cliente {client_ip} desconectado durante signup. Removendo.")
                                remove_client(client_ip)
                                continue

                    elif decoded_message.startswith("QUIT_TAG:"):
                        nickname = decoded_message.split(":", 1)[1]
                        if client_ip == address_ip_client:
                            remove_client(client_ip)
                        try:
                            server.sendto(f"{nickname} saiu da sala!".encode("utf-8"), client_ip)
                        except socket.error as e:
                            error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                            if error_code == 10054:
                                print(f"[BROADCAST] Cliente {client_ip} já desconectado durante quit.")
                                if client_ip in clients_ip:
                                    remove_client(client_ip)

                    elif ":" in decoded_message:
                        # Mensagem de chat - apenas envia para OUTROS clientes (não para quem enviou)
                        if client_ip != address_ip_client:  
                            name, msg = decoded_message.split(":", 1)
                            ip, port = address_ip_client
                            message_output = f'\n{ip}:{port}/~{name}:{msg.strip()} {get_current_time_and_date()}\n'
                            fragment_and_send(message_output.encode("utf-8"), client_ip)
                    else:
                        print(f"[ERRO] Mensagem inesperada: {decoded_message}")
                        
                except socket.error as e:
                    error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                    if error_code == 10054:
                        print(f"[BROADCAST] Erro de conexão com {client_ip}. Removendo cliente.")
                        if client_ip in clients_ip:
                            remove_client(client_ip)
                    else:
                        print(f"[BROADCAST] Erro de socket para {client_ip}: {e}")
                except Exception as e:
                    print(f"[BROADCAST] Erro geral ao enviar mensagem para {client_ip}: {e}")

# Inicia as threads
receive_tread = threading.Thread(target=receive, daemon=True)
broadcast_tread = threading.Thread(target=broadcast, daemon=True)
##cleanup_thread = threading.Thread(target=cleanup_disconnected_clients, daemon=True)

print(f"[SERVIDOR OK] Servidor conectado e aguardando na porta {SERVER_PORT}, {get_current_time_and_date()}")

receive_tread.start()
broadcast_tread.start()

# Mantém o processo vivo
receive_tread.join()
broadcast_tread.join()
