# Função para converter dados de bytes em bits
def bytes_to_bits_binary(byte_data):
    bits_data = bin(int.from_bytes(byte_data, byteorder='big'))[2:]
    return bits_data

# Função para calcular a soma 
def find_sum_checksum(message):
    # Converte a mensagem enviada para uma sequência binária de bits
    message_bits = bytes_to_bits_binary(message)
    slice_lenght = 8
    
    # Dividindo a mensagem enviada em pacotes de 8 bits.
    checksum_array = []
    while message_bits:
        checksum_array.append(message_bits[0:slice_lenght])
        message_bits = message_bits[slice_lenght:]
    
    # Calculando a soma binária dos pacotes
    return bin(sum(int(binary, 2) for binary in checksum_array))[2:]

# Função para encontrar o Checksum da Mensagem Enviada
def find_checksum(message):
    # Calcula a soma 
    sum_checksum = find_sum_checksum(message)
    slice_lenght = 8
    
    # Adiciona os bits de overflow
    if len(sum_checksum) > slice_lenght:
        x = len(sum_checksum) - slice_lenght
        sum_checksum = bin(int(sum_checksum[0:x], 2) + int(sum_checksum[x:], 2))[2:]
    
    # Preenche com zeros à esquerda se necessário
    if len(sum_checksum) < slice_lenght:
        sum_checksum = '0' * (slice_lenght - len(sum_checksum)) + sum_checksum

    # Complemento de 1
    checksum = ''.join('0' if bit == '1' else '1' for bit in sum_checksum)

    # Retorna o checksum como inteiro-- util pro  calculo comparando com o header e em sendpackets
    return int(checksum, 2)
