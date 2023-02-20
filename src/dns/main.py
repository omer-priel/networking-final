# entry point to DNS

from src.lib.config import config, init_config


def main() -> None:
    init_config()

    print("Hello World DNS")


if __name__ == "__main__":
    main()
