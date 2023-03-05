# options class


class Options:
    def __init__(self) -> None:
        self.clientAddress: tuple[str, int] = ("localhost", 8001)
        self.appAddress: tuple[str, int] = ("localhost", 8000)
        self.anonymous = True
        self.userName = ""
        self.password = ""
