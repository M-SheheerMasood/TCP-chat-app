import random
import os
import time
from string import ascii_letters
from .BasicTest import *


class FileSharingTest(BasicTest):
    def __init__(self, forwarder, test_name, verbose=False):
        super().__init__(forwarder, test_name)
        self.verbose = verbose  

    def set_state(self):
        self.num_of_clients = 5
        self.client_stdin = {
            "client1": 1,
            "client2": 2,
            "client3": 3,
            "client4": 4,
            "client5": 5,
        }
        self.input = [
            ("client1", "list\n"),  # client1 requests the list of active users
            # client1 sends file1 to client2
            ("client1", "file 1 client2 test_file1\n"),
            # client3 shares file2 with client1 & client4
            ("client3", "file 2 client1 client4 test_file2\n"),
            # client5 shares file3 with multiple clients
            ("client5", "file 3 client2 client3 client4 test_file3\n"),
            ("client2", "list\n"),  # client2 requests the list of active users
            # client4 sends file4 to client5
            ("client4", "file 1 client5 test_file4\n"),
            # client5 shares file5 with all
            ("client5", "file 4 client1 client2 client3 client4 test_file5\n"),
        ]
        self.last_time = time.time()

        # Create test files
        for i in range(1, 6):  # test_file1 to test_file5
            with open(f"test_file{i}", "w") as f:
                f.write("".join(random.choice(ascii_letters)
                        for _ in range(2000 + i * 200)))

    def result(self):
        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")

        for client in self.client_stdin.keys():
            if not os.path.exists("client_" + client):
                raise ValueError(f"No such file client_{client}")

        server_out = []
        clients_out = {}
        files = {f"test_file{i}": [] for i in range(1, 6)}

        # Generate expected outputs
        for client in self.client_stdin.keys():
            server_out.append(f"join: {client}")
            clients_out[client] = ["quitting"]
            server_out.append(f"disconnected: {client}")

        for inp in self.input_to_check:
            client, message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append(f"request_users_list: {client}")
                clients_out[client].append(
                    "list: %s" % " ".join(sorted(self.client_stdin.keys()))
                )
            elif msg[0] == "msg":
                server_out.append("msg: %s" % client)
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append("msg: %s: %s" % (client, " ".join(msg[2 + int(msg[1]):])) )
            elif msg[0] == "file":
                server_out.append(f"file: {client}")
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append(
                        "file: %s: %s" % (client, msg[2 + int(msg[1])])
                    )
                    files[msg[2 + int(msg[1])]].append(
                        f"{msg[i+2]}_{msg[2+int(msg[1])]}"
                    )

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
                    f"\033[91mTest Failed\033[0m: Server output is incorrect."
                )
                print("\nMissing lines (expected but not found):")
                for line in missing_lines:
                    print(f"  - {line}")
                return False

        # Validate file integrity
        for filename, generated_files in files.items():
            for generated_file in generated_files:
                if not self.files_are_the_same(generated_file, filename):
                    print(f"\033[91mTest Failed\033[0m: File {generated_file} is corrupted or missing.")
                    return False

        print("\033[92mTest Passed\033[0m")
        return True

    def show_verbose_output(self, expected, actual, context):
        """Display detailed side-by-side comparison of outputs."""
        print(f"\n\033[94mVerbose Output: {context} Comparison\033[0m")

        max_expected_len = max(len(line)
                               for line in expected) if expected else 0
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
