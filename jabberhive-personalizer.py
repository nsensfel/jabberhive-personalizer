#!/bin/env python3
import argparse
import re

import socket
import _thread

class ClientState:
    CLIENT_IS_SENDING_DOWNSTREAM = 1
    CLIENT_IS_SENDING_UPSTREAM = 2
    CLIENT_IS_CONNECTING = 3
    CLIENT_IS_TERMINATING = 4

def client_main (source, params):
    pattern = re.compile(params.regex)
    state = ClientState.CLIENT_IS_CONNECTING
    t_connect = None
    current_target = None
    current_username = "Mysterious Guest"

    try:
        while True:
            if (state == ClientState.CLIENT_IS_SENDING_DOWNSTREAM):
                valid_query = False
                up_data = "Nothing"

                while not valid_query:
                    print("AWAITING NEXT MESSAGE FROM SOURCE...")
                    try:
                        in_data = b""

                        while True:
                            in_char = source.recv(1)
                            in_data = (in_data + in_char)

                            if (in_char == b"\n"):
                                break
                            elif (in_char == b''):
                                raise Exception("Disconnected client")

                        up_data = in_data.decode("UTF-8")
                    except UnicodeDecodeError:
                        print("IN unicode error.")

                    valid_query = up_data.startswith("?R")

                    print("IN: \"" + up_data + "\"")

                    if (up_data.startswith("!AI username: ")):
                        username = re.sub(
                            "!AI username: (.*)\n",
                            r"\1",
                            up_data
                        )
                        print("NEW USERNAME: " + username)
                    else:
                        print("IN (true): \"" + str(in_data) + "\"")
                        t_connect.sendall(in_data)

                state = ClientState.CLIENT_IS_SENDING_UPSTREAM

            elif (state == ClientState.CLIENT_IS_SENDING_UPSTREAM):
                valid_reply = False
                down_data = "Nothing"

                print("AWAITING NEXT MESSAGE FROM SERVER...")
                while not valid_reply:
                    try:
                        out_data = b""

                        while True:
                            out_char = t_connect.recv(1)
                            out_data = (out_data + out_char)

                            if (out_char == b"\n"):
                                break
                            elif (out_char == b''):
                                raise Exception("Disconnected client")
                        down_data = out_data.decode("UTF-8")
                    except UnicodeDecodeError:
                        print("Unicode error.")
                        down_data = "!N"

                    print("Transformed \"" + down_data + "\"")
                    down_data = re.sub(pattern, username, down_data)
                    source.send(down_data.encode("UTF-8"))
                    print("into \"" + down_data + "\"")

                    valid_reply = (
                        down_data.startswith("!P")
                        or down_data.startswith("!N")
                    )

                print("Sending downstream...")
                state = ClientState.CLIENT_IS_SENDING_DOWNSTREAM

            elif (state == ClientState.CLIENT_IS_CONNECTING):
                print("Connecting to downstream...")
                t_connect = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                t_connect.connect(params.destination)

                print("Sending downstream...")
                state = ClientState.CLIENT_IS_SENDING_DOWNSTREAM
            else:
                break
    except:
        print("Closing")
        source.close()
        t_connect.close()

################################################################################
## ARGUMENTS HANDLING ##########################################################
################################################################################

parser = argparse.ArgumentParser(
    description = (
        "Generates a list of instructions to construct the Structural Level."
    )
)

parser.add_argument(
    '-s',
    '--socket-name',
    type = str,
    required = True,
    help = 'Name of the UNIX socket for this filter.'
)

parser.add_argument(
    '-d',
    '--destination',
    type = str,
    required = True,
    help = 'UNIX socket this filter sends to.',
)

parser.add_argument(
    '-r',
    '--regex',
    type = str,
    required = True,
    help = 'The regex to replace with the current user\'s name',
)

args = parser.parse_args()

################################################################################
## MAIN ########################################################################
################################################################################
server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

server_socket.bind(args.socket_name)
server_socket.listen(5)

while True:
    (client, client_address) = server_socket.accept()
    _thread.start_new_thread(client_main, (client, args))

