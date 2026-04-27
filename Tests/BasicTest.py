import hashlib
import os
import time
import util


class BasicTest(object):
    def __init__(self, forwarder, test_name="Basic", verbose=False):
        self.forwarder = forwarder
        self.forwarder.register_test(self, test_name)
        self.num_of_clients = 0
        self.client_stdin = {}
        self.input = []
        self.input_to_check = []
        self.last_time = time.time()
        self.time_interval = 0.5
        self.verbose = verbose

    def set_state(self):
        pass

    def handle_message(self):
        for m, user in self.forwarder.in_queue:
            self.forwarder.out_queue.append((m, user))
        self.forwarder.in_queue = []

    def handle_tick(self, tick_interval):
        if self.last_time is None:
            return
        elif len(self.input) > 0:
            if time.time() - self.last_time > self.time_interval:
                client, inpt = self.input[0]
                self.input_to_check.append((client, inpt))
                self.input = self.input[1:]
                self.forwarder.senders[client].stdin.write(inpt.encode())
                self.forwarder.senders[client].stdin.flush()
                self.last_time = time.time()
        elif time.time() - self.last_time > 0.5:
            for client in self.forwarder.senders.keys():
                self.forwarder.senders[client].stdin.write("quit\n".encode())
                self.forwarder.senders[client].stdin.flush()
            self.last_time = None
        return

    def result(self):
        num_of_packets = 0

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
            server_out.append(f"join: {client}")
            clients_out[client] = ["quitting"]
            server_out.append(f"disconnected: {client}")
            num_of_packets += 1

        # Checking Output of Client Messages
        for inp in self.input_to_check:
            client, message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append(f"request_users_list: {client}")
                clients_out[client].append(
                    "list: %s" % " ".join(sorted(self.client_stdin.keys()))
                )
                num_of_packets += 2
            elif msg[0] == "msg":
                server_out.append(f"msg: {client}")
                num_of_packets += 1
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append(
                        f"msg: {client}: {' '.join(msg[2 + int(msg[1]):])}"
                    )
                    num_of_packets += 1

        # Validate Clients Output
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

        # Validate Server Output
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

    def files_are_the_same(self, file1, file2):
        return BasicTest.md5sum(file1) == BasicTest.md5sum(file2)

    @staticmethod
    def md5sum(filename, block_size=2**20):
        with open(filename, "rb") as f:
            md5 = hashlib.md5()
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5.update(data)
        return md5.digest()
