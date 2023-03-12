# entry point to Application

import logging
import os
import os.path
import sys

from src.client.commands import delete_command, download_command, list_command, upload_command
from src.client.options import Options
from src.lib.config import config, init_logging
from src.lib.network import create_network_connection


def init_app() -> None:
    config.LOGGING_LEVEL = logging.CRITICAL

    init_logging()

    logging.info("The app is initialized")


def print_help() -> None:
    print('client is CLI client for custom app like "FTP" based on UDP.')
    print("  client --help                                                      - print the help content")
    print("  client [options] upload [--dest <destination>] <file / directory>  - upload file or directory")
    print("  client [options] download <remote file / directory> [destination]  - download file or directory")
    print("  client [options] list [remote directory] [--recursive]             - print directory content")
    print("  client [options] delete <remote file / directory>                  - delete file or directory")
    print("Options:")
    print("--user <user name>    - set user name")
    print("--password <password> - set user password, require --user")
    print("--host <host> - set the server host address, defualt: localhost")
    print("--port <port> - set the server port, defualt: 8000")
    print("--client-host <host> - set the client host address, defualt: localhost")
    print("--client-port <port> - set the client port, defualt: 8001")


def main() -> None:
    init_app()

    if len(sys.argv) < 2 or "--help" in sys.argv:
        print_help()
        return None

    options = Options()

    i = 1

    while i < len(sys.argv) and sys.argv[i].startswith("--"):
        if sys.argv[i] == "--user":
            if i + 1 == len(sys.argv):
                print("User Name is missing")
                return None
            else:
                options.userName = sys.argv[i + 1]
                options.anonymous = False
            i += 2
        elif sys.argv[i] == "--password":
            if i + 1 == len(sys.argv):
                print("Password is missing")
                return None
            else:
                options.password = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--host":
            if i + 1 == len(sys.argv):
                print("Host address is missing")
                return None
            else:
                options.appAddress = (sys.argv[i + 1], options.appAddress[1])
            i += 2
        elif sys.argv[i] == "--port":
            if i + 1 == len(sys.argv):
                print("Port address is missing")
                return None
            else:
                options.appAddress = (options.appAddress[0], int(sys.argv[i + 1]))
            i += 2
        elif sys.argv[i] == "--client-host":
            if i + 1 == len(sys.argv):
                print("Host address is missing")
                return None
            else:
                options.clientAddress = (sys.argv[i + 1], options.clientAddress[1])
            i += 2
        elif sys.argv[i] == "--client-port":
            if i + 1 == len(sys.argv):
                print("Port address is missing")
                return None
            else:
                options.clientAddress = (options.clientAddress[0], int(sys.argv[i + 1]))
            i += 2
        else:
            print("The option {} dose not exists!".format(sys.argv[i]))
            return None

    if options.password != "" and options.userName == "":
        print("The --password need User Name!")
        return None

    if i == len(sys.argv):
        print("Not found any command")
        return None

    if sys.argv[i] == "upload":
        targetPath = None
        destination = None

        i += 1
        while i < len(sys.argv):
            if sys.argv[i] == "--dest":
                if i == len(sys.argv) - 1:
                    print("The option --dest need destaion as paramter")
                    return None
                destination = sys.argv[i + 1]
                i += 1
            else:
                targetPath = sys.argv[i]
            i += 1

        if not targetPath:
            print("Missing file / directory path to upload")
            return None

        if not destination:
            destination = os.path.basename(targetPath)

        networkConnection = create_network_connection(options.clientAddress)
        print("The client socket initialized on " + options.clientAddress[0] + ":" + str(options.clientAddress[1]))

        upload_command(networkConnection, options, targetPath, destination)
        networkConnection.close()
    elif sys.argv[i] == "download":
        if len(sys.argv) == i + 1:
            print("File / directory path and destination path are Missing!")
            return None
        if len(sys.argv) == i + 2:
            print("Destination path are Missing!")
            return None

        targetPath = sys.argv[i + 1]
        destination = sys.argv[i + 2]

        networkConnection = create_network_connection(options.clientAddress)
        print("The client socket initialized on " + options.clientAddress[0] + ":" + str(options.clientAddress[1]))

        download_command(networkConnection, options, targetPath, destination)
        networkConnection.close()

    elif sys.argv[i] == "list":
        recursive = False
        directoryPath = "."

        i += 1
        while i < len(sys.argv):
            if sys.argv[i] == "--recursive":
                recursive = True
            else:
                directoryPath = sys.argv[i]
            i += 1

        networkConnection = create_network_connection(options.clientAddress)
        print("The client socket initialized on " + options.clientAddress[0] + ":" + str(options.clientAddress[1]))

        list_command(networkConnection, options, directoryPath, recursive)
        networkConnection.close()
    elif sys.argv[i] == "delete":
        if len(sys.argv) == i + 1:
            print("File / directory path is Missing!")
            return None

        targetPath = sys.argv[i + 1]

        networkConnection = create_network_connection(options.clientAddress)
        print("The client socket initialized on " + options.clientAddress[0] + ":" + str(options.clientAddress[1]))

        delete_command(networkConnection, options, targetPath)
        networkConnection.close()
    else:
        print('The command "{}" not exists'.format(sys.argv[i]))


if __name__ == "__main__":
    main()
