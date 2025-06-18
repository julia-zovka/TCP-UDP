from socket import *
serverPort=15000
hostname=socket.gethostname()

serverSocket=socket(AF_INET,SOCK_DGRAM)
serverSocket.bind((hostname, serverPort))
print ("the server is readyyyy")
while 1:
    message=clientAdress=serverSocket.recvfrom(1024)###espera uma mensagem chegarr

    modifiedMessage=message.upper()##aqui é comp trata a e oque manda pro cliente de volta
    serverSocket.sendto(modifiedMessage,clientAdress)