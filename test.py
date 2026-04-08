import requests


url = f"https://api.telegram.org/bot8645106850:AAEO_vZmF9MBAo7OcIpJZHHtGPOcle11igY/getUpdates?offset=-1"
response = requests.get(url)

print(response.json())