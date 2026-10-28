from app.llm import generate


def main():
    response = generate("Reply with exactly five words.")
    print(response)


if __name__ == "__main__":
    main()
