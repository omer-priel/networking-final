# create a big file

def main() -> None:
    LINES = 1000

    fileName = str(LINES) + ".txt"
    if LINES >= 1000:
        fileName = str(int(LINES / 1000)) + "K.txt"
    f = open(fileName, "a")
    for i in range(1, LINES + 1):
        f.write("*" * i + "\n")
    f.close()

if __name__ == "__main__":
    main()
