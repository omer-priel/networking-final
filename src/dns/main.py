# entry point to DNS

from src.dns.config import init_config, init_logging
from src.dns.controller import main_loop
from src.dns.database import get_database


def main() -> None:
    init_config()
    init_logging()

    database = get_database()

    main_loop(database)


if __name__ == "__main__":
    main()
