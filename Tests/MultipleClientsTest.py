from .BasicTest import *


class MultipleClientsTest(BasicTest):
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
            ("client1", "list\n"),
            ("client2", "msg 1 client3 Hello Client3!\n"),
            ("client3", "list\n"),
            ("client4", "msg 3 client1 client5 client2 Hi everyone!\n"),
            ("client5", "msg 1 client4 Thank you!\n"),
            ("client1", "msg 4 client2 client3 client4 client5 Welcome all!\n"),
            ("client3", "msg 2 client1 client2 Greetings!\n"),
            ("client2", "list\n"),
            ("client4", "msg 1 client5 Bye for now!\n"),
            ("client5", "msg 4 client1 client2 client3 client4 Final message\n"),
        ]
        self.last_time = time.time()
