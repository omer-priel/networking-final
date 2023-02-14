# entry point to Application

from src.utils import config, init_config


def main() -> None:
    init_config()

    print("Hello World Application")
    print(config.APP_HOST + ":" + str(config.APP_PORT))


if __name__ == "__main__":
    main()