# entry point to DHCP

from src.dhcp.config import config, init_config, init_logging


def main() -> None:
    init_config()
    init_logging()


if __name__ == "__main__":
    main()
