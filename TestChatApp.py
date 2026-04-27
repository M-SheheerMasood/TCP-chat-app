import os
import socket
import subprocess
import time
import random
import signal
import argparse
from Tests import SingleClientTest, BasicTest, MultipleClientsTest, ErrorHandlingTest, FileSharingTest

total_passed = 0


def delete_with_rm_rf():
    """Delete outputs from previous runs using rm -rf."""
    patterns = ["./client_*", "./test_*", "./*_test_*", "./server_out"]

    try:
        for pattern in patterns:
            subprocess.run(f"rm -rf {pattern}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to delete files matching pattern: {e}")


def tests_to_run(forwarder, selected_tests, verbose):
    """Runs the selected tests or all tests if none specified."""
    test_map = {
        "SingleClient": SingleClientTest.SingleClientTest,
        "MultipleClients": MultipleClientsTest.MultipleClientsTest,
        "FileSharing": FileSharingTest.FileSharingTest,
        "ErrorHandling": ErrorHandlingTest.ErrorHandlingTest
    }

    if selected_tests:
        for test_name in selected_tests:
            if test_name in test_map:
                test_map[test_name](forwarder, test_name, verbose=verbose)
            else:
                print(f"Unknown test: {test_name}")
    else:
        for test_name, test_class in test_map.items():
            test_class(forwarder, test_name, verbose=verbose)


class Forwarder(object):
    def __init__(self, sender_path, receiver_path, port):
        if not os.path.exists(sender_path):
            raise ValueError("Could not find sender path: %s" % sender_path)
        self.sender_path = sender_path

        if not os.path.exists(receiver_path):
            raise ValueError("Could not find receiver path: %s" %
                             receiver_path)
        self.receiver_path = receiver_path

        self.tests = {}  # test object => testName
        self.current_test = None
        self.out_queue = []
        self.in_queue = []
        self.tick_interval = 0.001  # 1ms
        self.last_tick = time.time()
        self.timeout = 12.  # seconds

        # network stuff
        self.port = port
        self.middle_clientside = {}  # Man in the middle sockets that connects with clients
        self.middle_serverside = {}  # Man in the middle sockets that connects with server
        self.senders = {}
        self.receiver_port = self.port + 1
        self.receiver_addr = None

    def _tick(self):
        self.current_test.handle_tick(self.tick_interval)
        for p, user in self.out_queue:
            self._send(p, user)
        self.out_queue = []

    def _send(self, message, user):
        if message.receiver == "clientside":
            self.middle_clientside[user].send(message.message)
        elif message.receiver == "serverside":
            self.middle_serverside[user].send(message.message)

    def register_test(self, testcase, testName):
        assert isinstance(testcase, BasicTest.BasicTest)
        self.tests[testcase] = testName

    def execute_tests(self):
        for t in self.tests:
            try:
                self.port = random.randint(2000, 65500)
                self.current_test = t
                self.current_test.set_state()

                self.sock = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind(('', self.port))
                self.sock.listen()
                self.sock.settimeout(self.timeout)
                self.middle_clientside = {}  # Man in the middle sockets that connects with clients
                self.middle_serverside = {}  # Man in the middle sockets that connects with server
                for client in sorted(self.current_test.client_stdin.keys()):
                    self.middle_serverside[client] = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM)
                    self.middle_serverside[client].settimeout(0.01)

                print(("Testing %s" % self.tests[t]))
                self.start()
            except Exception as e:
                print(f"\033[91mTest Failed due to an exception!\033[0m {e}")

    def handle_receive(self, message, sender, user):
        if sender == "clientside":
            m = MessageWrapper(message, "serverside")
        elif sender == "serverside":
            m = MessageWrapper(message, "clientside")

        self.in_queue.append((m, user))
        self.current_test.handle_message()

    def start(self):
        self.receiver_addr = ('127.0.0.1', self.receiver_port)
        self.recv_outfile = "server_out"

        recv_out = open(self.recv_outfile, "w")
        receiver = subprocess.Popen(
            ["python3", self.receiver_path, "-p", str(self.receiver_port)],
            stdout=recv_out)
        time.sleep(0.01)  # make sure the receiver is started first. reduced this from 0.2 to 0.01
        self.senders = {}
        sender_out = {}
        for i in sorted(list(self.current_test.client_stdin.keys())):
            u = i
            sender_out[i] = open("client_" + i, "w")
            if "duplicate" in i:
                u = i[:7]
            self.senders[i] = subprocess.Popen([
                "python3", self.sender_path, "-p", str(self.port), "-u", u
            ],
                stdin=subprocess.PIPE,
                stdout=sender_out[i])

            conn, addr = self.sock.accept()
            conn.settimeout(0.01)
            self.middle_clientside[i] = conn
            self.middle_serverside[i].connect(self.receiver_addr)

        try:
            client_stdin = dict(self.current_test.client_stdin)
            start_time = time.time()
            self.last_tick = time.time()
            while None in [self.senders[s].poll() for s in self.senders]:
                for i in sorted(list(self.current_test.client_stdin.keys())):
                    try:
                        message = self.middle_clientside[i].recv(4096)
                        if len(message) != 0:
                            self.handle_receive(message, "clientside", i)
                    except socket.timeout:
                        pass
                    try:
                        message = self.middle_serverside[i].recv(4096)
                        if len(message) != 0:
                            self.handle_receive(message, "serverside", i)
                    except socket.timeout:
                        pass
                    if time.time() - self.last_tick > self.tick_interval:
                        self.last_tick = time.time()
                        self._tick()
                    if time.time() - start_time > self.timeout:
                        raise Exception("Test timed out!")
            while bool(client_stdin):
                for i in list(client_stdin.keys()):
                    try:
                        message = self.middle_clientside[i].recv(4096)
                        if len(message) != 0:
                            self.handle_receive(message, "clientside", i)
                        else:
                            del client_stdin[i]
                    except socket.timeout:
                        pass
            self._tick()
        except (KeyboardInterrupt, SystemExit):
            exit()
        finally:
            for sender in self.senders:
                if self.senders[sender].poll() is None:
                    self.senders[sender].send_signal(signal.SIGINT)
                sender_out[sender].close()
            receiver.send_signal(signal.SIGINT)
            recv_out.flush()
            recv_out.close()

        if not os.path.exists(self.recv_outfile):
            raise RuntimeError("No data received by receiver!")
        time.sleep(1)
        try:
            result = self.current_test.result()
            if result:
                global total_passed
                total_passed += 1
        except Exception as e:
            print(f"\033[91mTest Failed due to an exception!\033[0m {e}")


class MessageWrapper(object):
    def __init__(self, message, receiver):
        self.message = message
        self.receiver = receiver


if __name__ == "__main__":
    delete_with_rm_rf()

    def usage():
        print("Usage: python3 TestChatApp.py [options]")
        print("Options:")
        print(
            "  --client CLIENT   The path to the Client implementation (default: client.py)"
        )
        print(
            "  --server SERVER   The path to the Server implementation (default: server.py)"
        )
        print(
            "  --port PORT       The port number for the server (default: random in range 2000-65500)"
        )
        print(
            "  --test TESTS      Run specific tests (e.g., SingleClient MultipleClients). Default: Run all tests."
        )
        print(
            "  --verbose         Enable verbose output for tests."
        )
        print("  -h, --help        Show this help message and exit.")
        print("\nExample:")
        print("  python3 TestChatApp.py --client client.py --server server.py --verbose")
        print(
            "  python3 TestChatApp.py --client client.py --server server.py --test SingleClient MultipleClients --verbose"
        )

    parser = argparse.ArgumentParser(
        description="Tests for Chat Application", add_help=False)
    parser.add_argument(
        "--client",
        default="client.py",
        help="The path to Client implementation (default: client.py)"
    )
    parser.add_argument(
        "--server",
        default="server.py",
        help="The path to the Server implementation (default: server.py)"
    )
    parser.add_argument(
        "--port", default=random.randint(2000, 65500), type=int,
        help="The port number for the server (default: random in range 2000-65500)"
    )
    parser.add_argument("--test", nargs="*", default=None,
                        help="Run specific tests (e.g., SingleClient MultipleClients)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output for tests.")
    parser.add_argument("-h", "--help", action="store_true",
                        help="Show this help message and exit.")

    args = parser.parse_args()

    if args.help:
        usage()
        exit(0)
    try:
        f = Forwarder(args.client, args.server, args.port)
        tests_to_run(f, args.test, verbose=args.verbose)
        f.execute_tests()
    except Exception as e:
        print(f"\033[91mTest Failed due to an exception!\033[0m {e}")
        exit(1)

    if not args.test:
        print(f"Final Score: {total_passed * 5}/20")

        if total_passed == 4:
            print("\n🎉 Congratulations! You aced it! 🎉")
        elif total_passed == 0:
            print("\n😢 Oh no! You didn't pass any tests! There there 😢")
        else:
            print("\n✨ Good job! Keep aiming for perfection! ✨")
