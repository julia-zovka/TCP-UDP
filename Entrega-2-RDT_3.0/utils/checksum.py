from zlib import crc32

def find_checksum(data):
    
    return crc32(data) & 0xffffffff

def verify_checksum(data, expected_checksum):
    calculated = find_checksum(data)
    return calculated == expected_checksum

# Implementação alternativa usando soma simples (conforme material didático)
def simple_checksum(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Converte bytes para sequência de 16-bit words
    checksum = 0
    
    # Processa pares de bytes
    for i in range(0, len(data), 2):
        if i + 1 < len(data):
            word = (data[i] << 8) + data[i + 1]
        else:
            word = data[i] << 8  # Último byte se ímpar
        
        checksum += word
        
        # Trata overflow (wrap around)
        if checksum > 0xFFFF:
            checksum = (checksum & 0xFFFF) + 1
    
    # Complemento de 1
    return (~checksum) & 0xFFFF