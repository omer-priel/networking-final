# entry point to Application

import logging
import sys

from src.app.config import init_config, init_logging
from src.app.controller import main_loop
from src.app.rudp import create_socket
from src.app.storage import init_strorage
from src.lib.profiler import profiler_scope, use_profiler


@profiler_scope("init")
def init_app() -> None:
    init_config()
    init_logging()
    init_strorage()

    logging.info("The app is initialized")


# entry point
def main() -> None:
    init_app()
    create_socket()

    main_loop()


if __name__ == "__main__":
    if "--with-profiler" in sys.argv:
        use_profiler(main)
    else:
        main()
