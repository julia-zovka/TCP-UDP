# Configuracoes do servidor
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000

SERVER_ADDR = ("127.0.0.1", 12000)

BUFF_SIZE        = 1024
HEADER_SIZE      = 24
# max do payload em cada fragmento
FRAG_SIZE        = BUFF_SIZE - HEADER_SIZE


TIMEOUT = 0.5
ACK_RECEIVED = False
