import struct
from utils.checksum import find_checksum


def create_fragment(contents, frag_size, frag_index, frag_count):
     # Calcula a posição inicial e final do fragmento
    start = frag_index * frag_size
    end = start + frag_size
    fragment_data = contents[start:end]
    actual_size = len(fragment_data)

    header_no_checksum = struct.pack('!IIIII', actual_size, frag_index, frag_count, seq_num, ack_num)

    # calcula o checksum 
    data_for_checksum = header_no_checksum + fragment_data
    checksum_check = find_checksum(data_for_checksum)
    checksum_int = int(checksum_check, 2)

    # Monta o cabeçalho (tamanho real, índice, total, crc)
    header = struct.pack('!IIII', actual_size, frag_index, frag_count, seq_num, ack_num, checksum_int)
    return header + fragment_data