'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import socket
from threading import Thread
from dataclasses import dataclass
import argparse
import util #L dont need

@dataclass
class Client:
    '''
    This is the main Client Class. 
    Write your code inside this class. 
    In the start() function, you will read user-input and act accordingly.
    receive_handler() function is running another thread and you have to listen 
    for incoming messages in this function.
    '''
    name: str
    server_addr: str
    server_port: int

    def __post_init__(self):
        #adding this inside postinit to solve error 104
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(None)
        # state of connetion
        self.conn = False

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''
        try:
            self.sock.connect((self.server_addr, self.server_port))
            self.conn = True 
            # connection established
        except:
            print("Could not connect to server")
            sys.exit()
        self.sock.send(f"join {self.name}".encode())
        while True:
            try:
                user_input = input()
            except EOFError:
                continue
            except KeyboardInterrupt:
                self.sock.send("disconnect".encode())
                self.sock.close()
                sys.exit()
            if not self.conn:
                #check for connetion wont process forward till connection established
                break
            words = user_input.split()
            if words:
                # modularity wow i am so cool
                self.handle_user_input(words)

    def handle_user_input(self, words):
        types = words[0]
        if types == "list":
            self.sock.send("list".encode())
        elif types == "msg":
            self.handle_msg(words)
        elif types == "help":
            print("supported commands: list, msg, file, help, quit")
        elif types == "quit":
            self.sock.send("disconnect".encode())
            #gracefull yes yes
            print("quitting")
            self.sock.close()
            sys.exit()
        elif types == "file":
            self.handle_file(words)
        else:
            print("incorrect user input format")

    def handle_msg(self, words):
        # min len, digit check for just in case, check for format
        if len(words) >= 4 and words[1].isdigit() and len(words) - 2 > int(words[1]):
            msg_str = " ".join(words[1:])
            self.sock.send(f"msg {msg_str}".encode())
        else:
            print("incorrect user input format")

    def handle_file(self, words):
        # min len, digit check for just in case, check for format
        if len(words) >= 4 and words[1].isdigit() and len(words) - 2 > int(words[1]):
            count = int(words[1])
            file_name = words[count + 2]
            try:
                with open(file_name, 'r') as file:
                    content = file.read()
                new_string = " ".join(words[1:]) + " " + content
                self.sock.sendall(f"file {new_string}".encode()) #send it allllllll
            except:
                print("incorrect user input format")
        else:
            print("incorrect user input format")

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        while not self.conn:
            # making sure connetion is there
            continue
        while True:
            try:
                #beeg buffer
                msg = self.sock.recv(65536).decode()
                if not msg:
                    #check for empty
                    break
                words = msg.split()
                #get type
                types = words[0]
                # seperate based on type
                if types == "list":
                    text = "list: " + " ".join(words[1:])
                    print(text)
                elif types == "msg":
                    text = " ".join(words[2:])
                    print(f"msg: {words[1]}: {text}")
                elif types == "file":
                    words1 = msg.split(" ", 3) # first 3 so its easier to combine later
                    user = words1[1]
                    file_name = words1[2]
                    file_contents = words1[3] if len(words1) > 3 else "" # safety check for empty file, hiden test case preemptive strike :>
                    # open file with format to write in, override old file of same name tho
                    with open(f"{self.name}_{file_name}", 'w') as file:
                        file.write(file_contents)
                    print(f"file: {user}: {file_name}")
                elif types == "err_server_full":
                    print("disconnected: server full")
                    #set connetion to false before breaking very imp
                    self.conn = False
                    break
                elif types == "err_username_unavailable":
                    print("disconnected: username not available")
                    #set connetion to false before breaking very imp x2
                    self.conn = False
                    break
                elif types == "err_unknown_message":
                    print("disconnected: server received an unknown command")
                    #set connetion to false before breaking very imp x3
                    self.conn = False
                    break
            except:
                break
        self.sock.close()


# Do not change this part of code
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Application Client")
    parser.add_argument(
        "-u", "--user",
        required=True,
        type=str,
        help="The username of the Client"
    )
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
    USER_NAME = args.user
    PORT = args.port
    DEST = args.address

    S = Client(USER_NAME, DEST, PORT)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        print("Exception occurred. Exiting...")
        sys.exit()
