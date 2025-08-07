
# Funcao para salvar mensagem em .txt é para guardar o histórico das mensagens recebidas pelo servidor e fazer um log de toda conversa da sala

def convert_string_to_txt(nickname, message):
    filename = f"{nickname}_log.txt"
    with open(filename, "a", encoding="utf-8") as file:
        file.write(message + "\n")
    return filename