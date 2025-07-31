
import struct
from zlib import crc32
from utils.checksum import find_checksum


def create_fragment(contents, frag_size, frag_index, frag_count):
    # Calcula a posição inicial e final do fragmento
    start = frag_index * frag_size
    end = start + frag_size
    fragment_data = contents[start:end]
    actual_size = len(fragment_data)
    # Calcula CRC apenas dos dados do fragmento
    crc = crc32(fragment_data)
    # Monta o cabeçalho (tamanho real, índice, total, crc)
    header = struct.pack('!IIII', actual_size, frag_index, frag_count, crc)
    return header + fragment_data