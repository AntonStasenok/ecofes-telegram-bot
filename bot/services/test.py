import requests
import base64
import uuid

client_id = "5cb714b4-50fa-4408-a508-c3338c910bf9"
secret = "afad7144-c646-46ef-97c2-962f503e60b5"
encoded = base64.b64encode(f"{client_id}:{secret}".encode()).decode()

url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
headers = {
    "Authorization": f"Basic {encoded}",
    "RqUID": str(uuid.uuid4()),
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
}
data = {"scope": "GIGACHAT_API_PERS"}

response = requests.post(url, headers=headers, data=data, verify=False)
print("Status:", response.status_code)
print("Response:", response.text)
