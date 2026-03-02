from socket import *
import threading

serverName = '127.0.0.1' # local machine for now

tcpPort = 12000
udpPort = 5000

users = {"justin", "siya", "mongezi"}
onlineUsers = {}
groups = {}
lock = threading.Lock()

"""
Server is constantly listening at udpPort for a message with the cmd "DISCOVER", it'll send back 
a response with the client address to establish a tcp connection
"""
def udp_discovery():
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.bind((serverName, udpPort)) #this is for my local machine for now
    print("UDP discovery running...")

    while True:
        message, clientAddress = udpSocket.recvfrom(1024)

        if message.decode() == "DISCOVER":
            response = f"CHAT_SERVER|{tcpPort}"
            udpSocket.sendto(response.encode(), clientAddress)

"""
This is where the persistant tcp connection is established. We keep it listening and we handle multiple 
connections concurrently
"""
def tcp_server():
    serverSocket= socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', tcpPort))
    serverSocket.listen()
    print("TCP server running...")

    while True:
        connectionSocket, addr = serverSocket.accept()
        thread = threading.Thread(target=handle_client, args=(connectionSocket, addr))
        thread.start()

def handle_client(connectionSocket, addr):
    username = None

    while True:
        data = connectionSocket.recv(1024)
        if not data:
            break
        
        message = data.decode()
        parts = message.split("|")
        if len(parts) == 0:
            continue
        command = parts[0]

        # LOGIN
        if command == "LOGIN":
            reqUsername = parts[1]
            p2pPort = int(parts[2])
            clientIP = addr[0]
            with lock:
                # Reject if the user is already online or the requested username is not in the users
                if reqUsername in onlineUsers or reqUsername not in users:
                    connectionSocket.send("ERROR".encode())
                else:
                    username = reqUsername
                    onlineUsers[reqUsername] = {
                        "ip": clientIP,
                        "p2p_port": p2pPort,
                        "socket": connectionSocket
                    }
                    
                    connectionSocket.send("ACK".encode())
        # LOGOUT
        elif command == "LOGOUT":
            with lock:
                if username in onlineUsers:
                    del onlineUsers[username] 
                connectionSocket.send("ACK".encode())
                break
        
        # JOIN GROUP
        elif command == "JOIN GROUP":
            groupName = parts[1]

            with lock:
                
                if groupName in groups:
                    groups[groupName].add(username) 
                    connectionSocket.send("ACK".encode())
                else:
                    connectionSocket.send("ERROR".encode())

        # LEAVE GROUP
        elif command == "LEAVE GROUP":
            groupName = parts[1]
            with lock:
                # Allow user to leave group only if group exists and the user is in that group
                if groupName in groups and username in groups[groupName]:
                    groups[groupName].remove(username)
                    connectionSocket.send("ACK".encode())
                else:
                    connectionSocket.send("ERROR".encode())
        
        # CREATE GROUP
        elif command == "CREATE GROUP":
            groupName = parts[1]
            with lock:
                if groupName not in groups:
                    groups[groupName] = set()
                    groups[groupName].add(username) # assuming user becomes user in the group they created
                    connectionSocket.send("ACK".encode())
                else:
                    connectionSocket.send("ERROR".encode())
                
        # SEND PRIVATE
        elif command == "SEND PRIVATE":
            recipient = parts[1]
            with lock:
                if recipient in onlineUsers:
                    ip = onlineUsers[recipient]["ip"]
                    port = onlineUsers[recipient]["p2p_port"]

                    response = f"USER_INFO|{ip}|{port}"
                    connectionSocket.send(response.encode())
                else:
                    connectionSocket.send("User offline".encode())
        # SEND GROUP
        elif command == "SEND GROUP":
            groupName = parts[1]
            message = parts[2]

            if groupName not in groups:
                connectionSocket.send("ERROR".encode())
                continue
            # Loop through all the members and send the message to server
            for member in groups[groupName]:
                if member in onlineUsers:
                    memberSocket = onlineUsers[member]["socket"]
                    memberSocket.send(f"GROUP_MESSAGE|{groupName}|{username}|{message}".encode())



     # Cleanup if the client crashes or abruptly disconnects      
    with lock:
        if username and username in onlineUsers:
            del onlineUsers[username]
    connectionSocket.close()
    
if __name__ == "__main__":
    threading.Thread(target=udp_discovery, daemon=True).start()
    tcp_server()