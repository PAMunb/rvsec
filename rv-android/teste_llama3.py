from ollama import Client

def teste01():
    client = Client(host='http://localhost:11434')
    response = client.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": "Tell me an interesting fact about elephants",
            },
        ],
    )
    print(response["message"]["content"])


if __name__ == '__main__':
    teste01()
