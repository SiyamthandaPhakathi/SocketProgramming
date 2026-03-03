from socket import *
import threading 

udpPort = 5000
serverResponse = None
responseLock = threading.Lock()

"""
Server discovery that returns IP and TCP port and establishes the session
"""
def discover_server(inputMessage):
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    clientSocket.settimeout(5)

    message = inputMessage.encode()
    clientSocket.sendto(message, ('255.255.255.255', udpPort))

    try:
        data, serverAddress = clientSocket.recvfrom(1024)
        response = data.decode()
        print("Discovered:", response)

        parts = response.split("|")
        tcpPort = int(parts[1])

        return serverAddress[0], tcpPort
    except timeout:
        print("No server found")
        return None, None
    
"""
Receives the messages from the server
"""
def receive_message(clientSocket):
    global serverResponse
    while True:
        data = clientSocket.recv(1024).decode()
        if not data:
            break
        parts = data.split("|")

        # User info for private messages
        if parts[0] == "USER_INFO":
            with responseLock:
                serverResponse = data
        # Prints out group messages
        elif parts[0] == "GROUP_MESSAGE":
                group = parts[1]
                sender = parts[2]
                message = parts[3]
                print(f"\n[{group}] {sender}: {message}")
        else:
            print("\nServer:", data)

"""
Starts the client's peer-to-peer server
"""
def start_p2p_server(port):
    p2pServer = socket(AF_INET, SOCK_STREAM)
    p2pServer.bind(('', port))
    p2pServer.listen(5)

    while True:
        conn, addr = p2pServer.accept()
        data = conn.recv(1024).decode()

        parts = data.split("|")

        if parts[0] == "DATA":
            sender = parts[1]
            message = parts[2]
            print(f"\nPrivate from {sender}: {message}")
            conn.send("ACK".encode())
        
        conn.close()

"""
Sends private messages to the recipient
"""
def send_private(ip, port, sender, message):
    p2pSocket = socket(AF_INET, SOCK_STREAM)
    p2pSocket.connect((ip, port))

    p2pSocket.send(f"DATA|{sender}|{message}".encode())
    ack = p2pSocket.recv(1024).decode()
    print("Received", ack)

    p2pSocket.close()


def main():
    global serverResponse
    
    # Discover the server
    discoverInput = input("Enter discover to connect to server:")
    if discoverInput == "DISCOVER":
        serverIP, tcpPort = discover_server(discoverInput)
    else:
        print("INVALID INPUT...")
        return

    if not serverIP:
        return 
    
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverIP, tcpPort))

    print("Connected")

    # LOGIN
    username = input("Username: ")
    p2pPort = int(input("Choose P2P port (e.g. 6001): "))
    
    loginMessage = f"LOGIN|{username}|{p2pPort}"
    clientSocket.send(loginMessage.encode())

    response = clientSocket.recv(1024).decode()

    if response != "ACK":
        print("ERROR")
        return
    
    print("Login successful")

    # Starts the threads for the p2p server and the receiving ports socket
    threading.Thread(target=start_p2p_server, args=(p2pPort,), daemon=True).start()
    threading.Thread(target=receive_message, args=(clientSocket,), daemon=True).start()

    while True: 
        message = input()
        parts = message.split("|")

        if parts[0] == "SEND PRIVATE":
            recipient = parts[1]

            clientSocket.send(message.encode())
            
            response = None
            while response is None:
                with responseLock:
                    if serverResponse is not None:
                        response = serverResponse
                        serverResponse = None
                    

            responseParts = response.split("|")

            if responseParts[0] == "USER_INFO":
                ip = responseParts[1]
                port = int(responseParts[2])

                privateMessage = input("Enter private message: ")
                send_private(ip, port, username, privateMessage)
            
            else:
                print("User offline.")
        elif parts[0] == "SEND GROUP":
            clientSocket.send(message.encode())
        else:
            clientSocket.send(message.encode())

if __name__ == "__main__":
    main()