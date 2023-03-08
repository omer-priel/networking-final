# entry point to DNS

from src.dns.config import init_config, init_logging, config
from src.dns.controller import main_loop
from src.dns.database import get_database


def main() -> None:
    init_config()
    init_logging()

    databse = get_database()

    main_loop(databse)


if __name__ == "__main__":
    main()
