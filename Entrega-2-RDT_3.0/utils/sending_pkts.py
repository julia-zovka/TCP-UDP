from utils.convert_string_to_text import convert_string_to_txt 
import utils.constants as c
import math
import socket
import time
import struct
from utils.create_frag import  create_fragment


def send_packet(message, sender, destination_address, origin_adress=None, nickname=None, seq_num=None, ack_num=None):
    #fragment_sent = True # Controle do status de envio do fragmento
    
    # Converte a mensagem em um arquivo txt
    if origin_adress==c.SERVER_ADDR:
        path_file = convert_string_to_txt(nickname, message) # SERVER sending
    else:
        path_file = convert_string_to_txt(nickname, message) # CLIENT sending
    # Lendo o conteudo do arquivo
    with open(path_file,"rb") as file:
        contents = file.read()

    #fragmentando o arquivo em diversas partes
    fragSize = c.FRAG_SIZE # Tamanho do fragmento 
    fragCount = math.ceil(len(contents) / fragSize) # Quantidade total de fragmentos


    ### criacao dos fragmentos
    for frag_index in range(fragCount):
        fragment_data = contents[frag_index * fragSize: (frag_index + 1) * fragSize]

        fragment = create_fragment(fragment_data, fragSize, frag_index, fragCount, seq_num, ack_num)



        while True:
            sender.sendto(fragment, destination_address)
            print(f" Enviado fragmento {frag_index}, aguardando ACK...")

            sender.settimeout(c.TIMEOUT)
            try:
                ack_data, _ = sender.recvfrom(c.BUFF_SIZE)
                ack_header = ack_data[:24]
                _, _, _, seq_r, ack_r, checksum_r = struct.unpack('!IIIIII', ack_header)
                
                # Verifica se ack certo
                if ack_r==seq_num:
                    print(f"ACK {ack_r} recebido corretamente para fragmento {frag_index}")
                    break  
                    # pode enviar próximo fragmento
                else:
                    print(f"ACK incorreto, {ack_r} foi recebido, aguardando correto...")
            
            except socket.timeout:
                print(f"[TIMEOUT] Reenviando fragmento {frag_index}...")
                continue  # Reenvia
        time.sleep(0.1) ## depois dos válidos

    sender.settimeout(None)




def send_ack(sender: socket.socket, destination_address: tuple, ack_num: int):
    """
    Envia um ACK puro (sem payload), com ack_num no cabeçalho.
    """
    # Cabeçalho: (frag_size, frag_index, frag_count, seq_num, ack_num, checksum)
    # Tudo zero, exceto ack_num
    header = struct.pack('!IIIIII',
                         0,    # frag_size
                         0,    # frag_index
                         0,    # frag_count
                         0,    # seq_num (não usado em ACK)
                         ack_num,
                         0     # checksum não usado em ACK
                         )
    sender.sendto(header, destination_address)
