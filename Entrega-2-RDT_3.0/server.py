import socket
import queue
import threading
import struct
from datetime import datetime
import math

from utils.checksum import find_checksum
from utils.sending_pkts import send_packet
import utils.constants as g 


# Inicializacao

messages = queue.Queue()## fila de mensagens a serem processadas

clients_ip = []
clients_nickname = []
seq_ack_control= []

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((g.SERVER_IP, g.SERVER_PORT))
print(f"[{datetime.now().strftime('%H:%M:%S')}] Servidor conectado em {g.SERVER_IP}:{g.SERVER_PORT}")


final_ack=False # checar se fim ack foi recebido pelo cliente


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
    seq_ack_control.pop(index_client)


# Thread para receber mensagens

def receive():
    chunks_count=0 # quantidade de chunks recebidos
    rec_chunks=[] # lista dos chunks recebidos

    while True:
    
        message_received_bytes, address_ip_client = server.recvfrom(g.BUFF_SIZE)

        # Fragmentos e desempacotando o header
        header = message_received_bytes[:24]
        fragment = message_received_bytes[24:]
        frag_size, frag_index, frag_count, seq_num, ack_num, checksum = struct.unpack('!IIIIII', header)

        header_no_checksum = struct.pack('!IIIII', frag_size, frag_index, frag_count, seq_num, ack_num) # Criando um header sem o checksum, para fazer a verificação de checksum depois
        fragment_no_checksum = header_no_checksum + fragment # Criando um fragmento que o header não tem checksum, para comparar com o checksum que foi feito no remetente, pois lá não havia checksum no header quando o checksum foi calculado

        # fazendo o calculo e ajeitando o checksum do que chegou
        checksum_check=find_checksum(fragment_no_checksum)

        decoded_message = fragment.decode("utf-8", errors="ignore")

        # Inicializa listas para o cliente se necessário
        if address_ip_client not in clients_ip:
            clients_ip.append(address_ip_client)
            nickname=decoded_message.split("eh ")[1]
            clients_nickname.append(nickname)
            seq_ack_control.append([0,0])
            index=clients_ip.index(address_ip_client)

        else:
            index= clients_ip.index(address_ip_client)
            nickname=clients_nickname[index]

        ## o seq number o pacote que o servidor mando com o akc do ultimo recebido
        curr_seq=seq_ack_control[index][0]
        curr_ack=seq_ack_control[index][1]
        expected_seq=1-curr_ack


        ### checando a integridade do pacote
        if(checksum!=checksum_check or seq_num!=expected_seq):## se tiver erro no checksum ou seq num, reenvia o ultimo ack
            if checksum!=checksum_check:
                print(f"Houve corrupção no pacote de {nickname}, ele terá que ser reenviado")
            else:
                print(f"Pacote de {nickname} fora de ordem ou duplicado, reenvio do último ACK")
            send_packet('', server, address_ip_client,g.SERVER_ADDR, nickname, curr_seq, curr_ack)
            continue
        
        ## pacote válido: envia ACK e alterna ack esperado
        new_ack = expected_seq
        send_packet('', server, address_ip_client,g.SERVER_ADDR, nickname, seq_num, new_ack)
        seq_ack_control[index][1] = new_ack


        ## adiciona fragcount posiçoes vazias na lista de fragmentos recebidos
        if(len(rec_chunks)<frag_count):
            to_add=frag_count-len(rec_chunks)
            rec_chunks.extend(['']* to_add)#aumenta a lista para caber os outros frags

        #adiciona o fragmento atual na lista de recebidos
        rec_chunks[frag_index]=fragment
        chunks_count+=1

        # Se recebeu todos os fragmentos
        if chunks_count == frag_count:
            print(f"[INFO] Todos os {frag_count} fragmentos recebidos de {address_ip_client}")
            content = b''.join(rec_chunks)
            content_decoded = content.decode("utf-8")

            path_file = convert_string_to_txt(nickname, content_decoded)

            ## le so a ultima mensagem do log
            with open(path_file, "r", encoding="utf-8") as arquivo:
                lines = arquivo.readlines()
                last_message=lines[-1].strip() if lines else ""
            if last_message.startswith("hi, meu nome eh ") or last_message.startswith("bye"):
                messages.put((decoded_message, address_ip_client, nickname))
            else:
                message = f"{nickname}:{last_message}".encode("utf-8")
                messages.put((message, address_ip_client, nickname))## joga na fila de mensagens


            # Limpa para óxima mensagem
            rec_chunks=[]
            chunks_count=0


        # Atualiza proximo seq_num a ser enviado
        g.ACK_RECEIVED = True
        seq_ack_control[index][0] = 1 - curr_seq



# Thread para enviar mensagens

def broadcast():
    global final_ack
    while True:
        while not messages.empty():
            decoded_message, address_ip_client, nickname = messages.get()

            ### envia para todos os usuários
            for client_ip in clients_ip:
                
                index = clients_ip.index(client_ip)
                name = clients_nickname[index]
                curr_seq = seq_ack_control[index][0] # seq que vamos usar para enviar
                curr_ack = seq_ack_control[index][1] # ack que queremos receber de volta

                try:
                    ### usuário entra na sala
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        send_packet(f"{nickname} se juntou, comece a conversar", server, client_ip, g.SERVER_ADDR, name, curr_seq, curr_ack)

                    ### usuário quer sair da sala
                    elif decoded_message=="bye":
                        send_packet(f"{nickname} saiu da sala!", server, client_ip, g.SERVER_ADDR, name, curr_seq, curr_ack)
                    
                    ### se comunicando na sala, mensagens
                    else:
                        ip, port = address_ip_client
                        message_output = f'{ip}:{port}/~{nickname}:{decoded_message} {get_current_time_and_date()}'
                        print(f'Enviando mensagem do usuário {nickname} para cliente {name}!')
                        send_packet(message_output, server, client_ip, g.SERVER_ADDR, name, curr_seq, curr_ack)
                     
                    ### altera o seq que vai ser usado no proximo pacote enviado 
                    seq_ack_control[index][0] = 1 - curr_seq
                except Exception as e:
                    print(f"Erro ao enviar mensagem {e} para {name}")
            
            
            if decoded_message=="bye":
                remove_client(address_ip_client)
                print(f'Removeu {nickname} da lista de usuários!')
                
# Inicia as threads

receive_tread = threading.Thread(target=receive)
broadcast_tread = threading.Thread(target=broadcast)

receive_tread.start()
broadcast_tread.start()

### o timer do servidor quanod ele manda os braodcasts

### reeenvio do pacote caso timer estoure ou ack errado

## logs precisos
