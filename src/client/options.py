# options class


class Options:
    def __init__(self) -> None:
        self.clientAddress: tuple[str, int] = ("localhost", 20859)
        self.appAddress: tuple[str, int] = ("localhost", 30034)
        self.anonymous = True
        self.userName = ""
        self.password = ""
