import random
import os
import time
from string import ascii_letters
from .BasicTest import *


class ErrorHandlingTest(BasicTest):
    def __init__(self, forwarder, test_name, verbose=False):
        super().__init__(forwarder, test_name)
        self.verbose = verbose 

    def set_state(self):
        self.num_of_clients = 12
        self.client_stdin = {}
        for i in range(1, 11):
            self.client_stdin["client" + str(i)] = i
        self.client_stdin["client_extra1"] = 11
        self.client_stdin["client_extra2"] = 12
        self.client_stdin["client1_duplicate"] = 13
        self.client_stdin["client5_duplicate"] = 14
        self.input = [
            ("client1", "msg 1 client4 Hello\n"),
            ("client2", "msg 2 client1 client0 Welcome Back!\n"),
            ("client5", "file 1 client12 test_file1\n"),
            ("client2", "msg 2 client1 client11 Heyy!\n"),
            ("client3", "list_my_friends\n"),
            ("client2", "quitt\n"),
        ]
        self.last_time = time.time()

        with open("test_file1", "w") as f:
            f.write("".join(random.choice(ascii_letters) for _ in range(2000)))

    def result(self):
        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")

        for client in self.client_stdin.keys():
            if not os.path.exists("client_" + client):
                raise ValueError(f"No such file client_{client}")

        server_out = []
        clients_out = {}

        # Checking Join
        for client in self.client_stdin.keys():
            if self.client_stdin[client] <= 10:
                server_out.append(f"join: {client}")
                clients_out[client] = ["quitting"]
                server_out.append(f"disconnected: {client}")
            elif "extra" in client:
                server_out.append("disconnected: server full")
                clients_out[client] = ["disconnected: server full"]
            elif "duplicate" in client:
                server_out.append("disconnected: username not available")
                clients_out[client] = ["disconnected: username not available"]

        # Checking Output of Client Messages
        for inp in self.input_to_check:
            client, message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append(f"request_users_list: {client}")
                clients_out[client].append(
                    "list: %s" % " ".join(sorted(self.client_stdin.keys()))
                )
            elif msg[0] == "msg":
                server_out.append(f"msg: {client}")
                for i in range(int(msg[1])):
                    if msg[i + 2] not in clients_out or int(self.client_stdin[msg[i + 2]]) > util.MAX_NUM_CLIENTS:
                        server_out.append(
                            f"msg: {client} to non-existent user {msg[i + 2]}")
                    else:
                        clients_out[msg[i + 2]].append(
                            f"msg: {client}: {' '.join(msg[2 + int(msg[1]):])}"
                        )
            elif msg[0] == "file":
                server_out.append(f"file: {client}")
                for i in range(int(msg[1])):
                    server_out.append(
                        f"file: {client} to non-existent user {msg[i + 2]}")
            elif msg[0] not in ["quit"]:
                clients_out[client].append("incorrect user input format")

        # Validate client outputs
        for client, expected_output in clients_out.items():
            with open(f"client_{client}") as f:
                user_output = f.read().split("\n")
                missing_lines = [
                    line for line in expected_output if line not in user_output
                ]

                if self.verbose:
                    self.show_verbose_output(
                        expected_output, user_output, f"Client {client}")
                if missing_lines:
                    print(f"\033[91mTest Failed\033[0m: Client {client} output is incorrect.")
                    print("\nMissing lines (expected but not found):")
                    for line in missing_lines:
                        print(f"  - {line}")
                    return False

        # Validate server output
        with open("server_out") as f:
            user_output = f.read().split("\n")
            missing_lines = [
                line for line in server_out if line not in user_output
            ]

            if self.verbose:
                self.show_verbose_output(server_out, user_output, "Server")
            if missing_lines:
                print(
                    f"\033[91mTest Failed\033[0m: Server output is incorrect.")
                print("\nMissing lines (expected but not found):")
                for line in missing_lines:
                    print(f"  - {line}")
                return False

        print("\033[92mTest Passed\033[0m")
        return True

    def show_verbose_output(self, expected, actual, context):
        """Display detailed side-by-side comparison of outputs."""
        print(f"\n\033[94mVerbose Output: {context} Comparison\033[0m")

        max_expected_len = max(len(line) for line in expected) if expected else 0
        max_actual_len = max(len(line) for line in actual) if actual else 0

        row_format = f"{{:<{max_expected_len + 2}}} | {{:<{max_actual_len + 2}}}"
        header = row_format.format("Expected Output", "Actual Output")
        separator = "-" * len(header)

        print(header)
        print(separator)

        max_lines = max(len(expected), len(actual))
        for i in range(max_lines):
            expected_line = expected[i] if i < len(expected) else ""
            actual_line = actual[i] if i < len(actual) else ""
            print(row_format.format(expected_line, actual_line))
