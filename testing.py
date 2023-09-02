import requests

payload = {"content": "when was hitler born?"}

response = requests.post("http://127.0.0.1:8000/chat", json=payload, stream=True)

for res in response.iter_content(chunk_size=1024, decode_unicode=True):
    print(res)
