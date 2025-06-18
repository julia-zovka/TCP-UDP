from socket import *
hostname=socket.gethostname()
serverName=hostname
serverPort=15000
clienteSocket=socket(socket.AF_INET, socket.SOCK_DGRAM)##cria o socket do cliente
#afnet--- ipv4
#sockdgram----socket udp
#porta do cliente e definida pelo so
message=input('input sentence:')
nome = input("Digite seu nome: ")
hello = f"hi, meu nome eh {nome}"

clienteSocket.sendto(message,(serverName, serverPort))

modifiedMessage,serverAddress=clienteSocket.recvfrom(1024)
print (modifiedMessage)# imprime pro usuario
clienteSocket.close()

