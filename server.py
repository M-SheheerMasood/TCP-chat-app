'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import socket
# i gotta import thread my self here tsk tsk
from threading import Thread
from dataclasses import dataclass
import argparse
import util #L dont need


MAX_NUM_CLIENTS = 10

@dataclass
class Server:
    '''
    This is the main Server Class. You will to write Server code inside this class.
    '''
    server_addr: str
    server_port: int

    def __post_init__(self):
        #adding this inside postinit to solve error 104
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        #dict for client sockets, addresses
        self.users = {}

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
         #open for conneting
        self.sock.listen()
        while True:
            soc, address = self.sock.accept()
            # create new thread and call function client in that thread
            thread = Thread(target=self.clients, args=(soc, address))
            #thread settings
            thread.daemon = True
            thread.start()

    def clients(self, soc, addresss):
        try:
            #big buffer mmmm yes
            msg = soc.recv(65536).decode()
        except ConnectionResetError:
            return
        if msg == "":
            return
        words = msg.split()
        #checking for min length for format
        if len(words) < 2:
            soc.close()
            return
        msg_type = words[0]
        username = words[1]
        if msg_type == "join":
            if len(self.users) >= MAX_NUM_CLIENTS:
                soc.send("err_server_full".encode())
                print("disconnected: server full")
                soc.close()
                return
            if username in self.users:
                soc.send("err_username_unavailable".encode())
                print("disconnected: username not available")
                soc.close()
                return
            #save user in the dict
            self.users[username] = [soc, addresss] #dk why u guys asked to store address didnt use it
            print(f"join: {username}")
            while True:
                try:
                    #big buffer is a good buffer :)
                    msg = soc.recv(65536).decode()
                except ConnectionResetError:
                    break
                words1 = msg.split()
                if not words1:
                    #check for empty msg
                    continue
                types = words1[0]
                # get type and do the task for that type
                # did input check on client side so less needed here
                if types == "list":
                    print(f"request_users_list: {username}")
                    user_list = "list " + " ".join(sorted(self.users.keys()))
                    soc.send(user_list.encode())
                elif types == "msg":
                    count = int(words1[1]) #num of recivers
                    recipients = words1[2 : 2 + count]
                    text = "msg " + username + " " + " ".join(words1[2 + count:])
                    print(f"msg: {username}")
                    for i in recipients:
                        if i in self.users:
                            self.users[i][0].send(text.encode())
                        else:
                            print(f"msg: {username} to non-existent user {i}")
                elif types == "file":
                    count = int(words1[1])
                    recipients = words1[2 : 2 + count]
                    # forward data
                    file_data = "file " + username + " " + " ".join(words1[2 + count:])
                    print(f"file: {username}")
                    for i in recipients:
                        if i in self.users:
                            self.users[i][0].sendall(file_data.encode()) #send all to make sure it works it failed sometimes without it
                        else:
                            print(f"file: {username} to non-existent user {i}")
                elif types == "disconnect":
                    print(f"disconnected: {username}")
                    #break to go to clean up
                    break
                else:
                    print(f"disconnected: {username} sent an unknown command")
                    soc.send("err_unknown_message".encode())
                    #break to go to clean up
                    break
            # dont exit prematurely yk have to do clean up so break is good
            #clean up
            if username in self.users:
                del self.users[username]
        soc.close()


# Do not change this part of code
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Application Server")
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=15000,
        help="The server port, defaults to 15000"
    )
    parser.add_argument(
        "-a", "--address",
        type=str,
        default="localhost",
        help="The server IP or hostname, defaults to localhost"
    )

    args = parser.parse_args()
    PORT = args.port
    DEST = args.address

    SERVER = Server(DEST, PORT)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        print("Exception occurred. Exiting...")
        sys.exit()
