import urllib.parse

API_KEY = "025ddbf0-aaee-4b5f-8281-5097b97c11ae"

REDIRECT_URI = "http://localhost:8080"

redirect = urllib.parse.quote(
    REDIRECT_URI,
    safe=""
)

url = (
    "https://api-v2.upstox.com/login/authorization/dialog"
    f"?response_type=code"
    f"&client_id={"025ddbf0-aaee-4b5f-8281-5097b97c11ae"}"
    f"&redirect_uri={redirect}"
)

print("\n")
print(url)
print("\n")