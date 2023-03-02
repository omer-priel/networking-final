# entry point to DHCP

import logging
import socket

from src.dhcp.config import init_config, init_logging
from src.dhcp.database import get_database
from src.dhcp.controller import main_loop


def main() -> None:
    init_config()
    init_logging()

    database = get_database()

    main_loop(database)


if __name__ == "__main__":
    main()
