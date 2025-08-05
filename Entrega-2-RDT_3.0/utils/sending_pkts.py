###from src.server import create_fragment
from server import convert_string_to_txt 
import utils.constants as c
import math
import time
from utils.create_frag import  create_fragment


def send_packet(message, sender, destination_address, origin_adress=None, nickname=None, seq_num=None, ack_num=None):
    fragment_sent = True # Controle do status de envio do fragmento
    
    # Converte a mensagem em um arquivo txt
    if origin_adress==c.SERVER_ADRR:
        path_file = convert_string_to_txt(message, nickname, True) # SERVER sending
    else:
        path_file = convert_string_to_txt(message, nickname) # CLIENT sending
    # Lendo o conteudo do arquivo
    with open(path_file,"rb") as file:
        contents = file.read()

    #fragmentando o arquivo em diversas partes
    fragSize = c.FRAG_SIZE # Tamanho do fragmento 
##    fragIndex = 0 # Indice do fragmento
    fragCount = math.ceil(len(contents) / fragSize) # Quantidade total de fragmentos


    ### criacao dos fragmentos
    for frag_index in range(fragCount):
        fragment_data = contents[frag_index * fragSize: (frag_index + 1) * fragSize]

        fragment = create_fragment(fragment_data, fragSize, frag_index, frag_count, seq_num, ack_num)



        while True: 

            if origin_adress:
                sender.sendto(fragment, (origin_adress, destination_address)) # Envia o fragmento (header + data) para servidor
            else:
                sender.sendto(fragment, (destination_address)) # Envia o fragmento (header + data) para cliente

            time_sent = time.time()

            # Aguarda até que ACK_RECEIVED ou time out seja True
            while not c.ACK_RECEIVED:
                if time.time() - time_sent > c.TIMEOUT:
                    print("O envio da mensagem excedeu o tempo limite!")
                    break
                time.sleep(0.1)

            if c.ACK_RECEIVED: # Se ACK foi recebido
                c.ACK_RECEIVED = False # Reseta status do ack
                break## vai pro proximo fragmento            
