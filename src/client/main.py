# entry point to Application

import logging

from src.utils import config, init_config, init_logging

def init_app() -> None:
    init_config()
    init_logging()

    logging.info('The app is initialized')


def main() -> None:
    print("Start Client")


if __name__ == "__main__":
    main()
