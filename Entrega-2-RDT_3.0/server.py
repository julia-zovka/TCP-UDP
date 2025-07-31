import socket
import queue
import threading
import struct
from datetime import datetime
from zlib import crc32
import math

from utils.checksum import find_checksum
from utils.sending_pkts import send_packet
import utils.variables as g 


# Configuracoes do servidor
SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000
BUFF_SIZE = 1024


# Inicializacao

messages = queue.Queue()## fila de mensagens a serem processadas

clients_ip = []
clients_nickname = []
seq_ack_control= []

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))

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

    global final_ack
    g.ACK_received ## setado inicialmente em false

    while True:
    
        message_received_bytes, address_ip_client = server.recvfrom(BUFF_SIZE)

        # Fragmentos e desempacotando o header
        header = message_received_bytes[:24]
        fragment = message_received_bytes[24:]
        frag_size, frag_index, frag_count, seq_num, ack_num, checksum = struct.unpack('!IIII', header)

        header_no_checksum = struct.pack('!IIIII', frag_size, frag_index, frag_count, seq_num, ack_num) # Criando um header sem o checksum, para fazer a verificação de checksum depois
        fragment_no_checksum = header_no_checksum + fragment # Criando um fragmento que o header não tem checksum, para comparar com o checksum que foi feito no remetente, pois lá não havia checksum no header quando o checksum foi calculado

        # fazendo o calculo e ajeitando o checksum do que chegou
        checksum_check=find_checksum(fragment_no_checksum)
        checksum=bin(checksum)[2:]
        checksum='0'*(len(checksum_check)- len(checksum)) + checksum # adiciona zeros a esquerda

        decoded_message = fragment.decode("utf-8", errors="ignore")

        if (decoded_message=="SYN"):
            print(f'enviando o SYN-ACK')
            messages.put((message_received_bytes, address_ip_client))
            send_packet("SYN-ACK", server, address_ip_client, None, f"3-way-handshake-{address_ip_client}", seq_num, ack_num)
            ###### decidir qual ainda
    
        else:
            # Inicializa listas para o cliente se necessário
            if address_ip_client not in clients_ip:
                clients_ip.append(address_ip_client)
                nickname=decoded_message.split("eh ")[1]
                clients_nickname.append(nickname)
                seq_ack_control.append([0,0])
                index=clients_ip.index(address_ip_client)

            else:
                index= clients_ip.index(address_ip_client)
                nickname=decoded_message.split("eh ")[1]


            if seq_ack_control:# se tiver algo na lista
                curr_seq=seq_ack_control[index][0]## o seq number o pacote que o servidor mando com o akc do ultimo recebido
                curr_ack=seq_ack_control[index][1]

                if decoded_message=="ACK":## recebeu a confirmacao do fyn ack que tinha enviado
                    final_ack=True
                    print("Vou fechar a conexão agora")
                elif decoded_message: ##  tem algo pra mandar de algum cliente pro chat agora vai checar o checksum e seq_number
                    expected_seq = 1-curr_ack
                    if checksum != checksum_check or seq_num != expected_seq:## teve algum erro
                        if checksum!=checksum_check:
                            print("Houve corrupção no pacote, ele terá que ser reenviado")

                        ## reenvio do ultimo ack
                        send_packet('',server, address_ip_client,SERVER_IP, nickname, seq_num, curr_ack )
                        #zerando a lista de fragmentos
                        rec_chunks=[]
                        chunks_count=0
                    
                    else:## tem mensagem e nao teve erro, irá mandar o ack para o cliente e a respectiva mensagem prara o chat
                        
                        # Atualiza próximo ack a ser enviado
                        if curr_ack == 0:
                            seq_ack_control[index][1] = 1
                        else:
                            seq_ack_control[index][1] = 0


                        if decoded_message=="bye":
                            print("vou enviar o FYN-ACK")
                            seq_ack_control[index][0] = 1-curr_seq ## atualizar curr_seq (seq do servidor para enviar): uma nova mensagem (não só um ACK vazio).
                            send_packet("FYN-ACK", server, address_ip_client, SERVER_IP, nickname, seq_num, curr_ack)## ja vai com o ack certo,m novo 
                        else:
                            print("enviando ACK da mensagem ")
                            send_packet('', server, address_ip_client, SERVER_IP, nickname, seq_num, curr_ack)


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

                            ## le so a ultima do log
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
                else:# caso pacote de reconhecimento,o cliente reconhecendo o broadcast por exemplo
                    if checksum !=checksum or ack_num!=curr_seq:#reenvio do ultimo pacote, teve algum erro
                        if checksum != checksum_check:
                            print(f"Houve corrupção no pacote!")
                    else: # Recebe ack do pacote recebido e atualiza próximo número de sequência a ser enviado
                    
                        g.ACK_received= True # Afirma que recebeu ack
                        print(f'Recebeu ACK do pacote!')

                        if curr_seq == 0:
                            seq_ack_control[index][0] = 1
                        elif curr_seq == 1:
                            seq_ack_control[index][0] = 0

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
                curr_seq = seq_ack_control[index][0]
                curr_ack = seq_ack_control[index][1]

                try:
                    ### usuário entra na sala
                    if decoded_message.startswith("SIGNUP_TAG:"):
                        send_packet(f"{nickname} se juntou, comece a conversar", server, client_ip, SERVER_IP, name, curr_seq, curr_ack)

                    ### usuário quer sair da sala
                    elif decoded_message=="bye":
                        send_packet(f"{nickname} saiu da sala!", server, client_ip, SERVER_IP, name, curr_seq, curr_ack)
                    
                    ### se comunicando na sala, mensagens
                    else:
                        ip, port = address_ip_client
                        message_output = f'{ip}:{port}/~{nickname}:{decoded_message} {get_current_time_and_date()}'
                        print(f'Enviando mensagem do usuário {nickname} para cliente {name}!')
                        send_packet(message_output, server, client_ip, SERVER_IP, name, curr_seq, curr_ack)
                
                except Exception as e:
                    print(f"Erro ao enviar mensagem {e} para {name}")
            if decoded_message=="bye":
                while not final_ack:### so tira quando receber o ack do cliente que marca final ack como true
                    pass
                remove_client(address_ip_client)
                print(f'Removeu {nickname} da lista de usuários!')
                final_ack=False
                
# Inicia as threads

receive_tread = threading.Thread(target=receive)
broadcast_tread = threading.Thread(target=broadcast)

receive_tread.start()
broadcast_tread.start()
pr

## address_ip_client isso é uma tupla

### ajeitar o adres do server nas funcoes de send


##ajeitar os curr ack e curr seq quanod manda os pacots
