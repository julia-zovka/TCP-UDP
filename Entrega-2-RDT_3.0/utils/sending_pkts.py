###from src.server import create_fragment
from server import convert_string_to_txt 
import utils.variables as g
import utils.constants as c
import math
import time
from utils.create_frag import  create_fragment


def send_packet(message, sender, destination_address, origin_adress=None, nickname=None, seq_num=None, ack_num=None):
    fragment_sent = True # Controle do status de envio do fragmento
    
    # Converte a mensagem em um arquivo txt
    if origin_adress==None:
        path_file = convert_string_to_txt(message, nickname, True) # SERVER sending
    else:
        path_file = convert_string_to_txt(message, nickname) # CLIENT sending
    # Lendo o conteudo do arquivo
    file = open(path_file,"rb")
    contents = file.read()

    #fragmentando o arquivo em diversas partes
    fragIndex = 0 # Indice do fragmento
    fragSize = c.FRAG_SIZE # Tamanho do fragmento 
    fragCount = math.ceil(len(contents) / fragSize) # Quantidade total de fragmentos

    # Envia os fragmentos
    if message == "FYN-ACK" or message == "ACK" or message == "" or message == "SYN" or message == "SYN-ACK": # Se pacote enviado for de reconhecimento
        fragment = create_fragment(contents, fragSize, fragIndex, fragCount, seq_num, ack_num)
        
        if origin_adress:
            sender.sendto(fragment, (origin_adress, destination_address)) # Envia o fragmento (header + data) para servidor
        else:
            sender.sendto(fragment, (c.SERVER_IP, destination_address)) # Envia o fragmento (header + data) para cliente

    else: # Se pacote enviado for com conteúdo
        if message == "FYN-ACK" or message == "ACK" or message == "SYN" or message == "SYN-ACK": # Se for pacote de reconhecimento de finalização
            fragment = create_fragment(contents, fragSize, fragIndex, fragCount, seq_num, ack_num)
            
            if origin_adress:
                sender.sendto(fragment, (origin_adress, destination_address)) # Envia o fragmento (header + data) para servidor
            else:
                sender.sendto(fragment, (destination_address)) # Envia o fragmento (header + data) para cliente
            
        else:
            while contents: 
                fragment = create_fragment(contents, fragSize, fragIndex, fragCount, seq_num, ack_num)

                time_of_last_pkt = time.time()

                if origin_adress:
                    sender.sendto(fragment, (origin_adress, destination_address)) # Envia o fragmento (header + data) para servidor
                else:
                    sender.sendto(fragment, (destination_address)) # Envia o fragmento (header + data) para cliente

                # Aguarda até que c.ACK_RECEIVED seja True
                while not g.ACK_RECEIVED:
                    if time_of_last_pkt + g.TIMEOUT < time.time():
                        print("O envio da mensagem excedeu o tempo limite!")
                        fragment_sent = False
                    pass

                if fragment_sent:
                    
                    g.ACK_RECEIVED = False # Reseta status do ack
                    contents = contents[fragSize:] # Remove o fragmento enviado do conteúdo
                    fragIndex += 1 # Incrementa o índice do fragmento
                
                fragment_sent = True # Reestabele status 'True' para fazer nova conferência
