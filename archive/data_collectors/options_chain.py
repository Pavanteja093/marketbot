import requests

session = requests.Session()

headers = {
    "User-Agent":
    "Mozilla/5.0"
}

session.get(
    "https://www.nseindia.com",
    headers=headers
)

url = (
    "https://www.nseindia.com/api/"
    "option-chain-indices?symbol=NIFTY"
)

response = session.get(
    url,
    headers=headers
)

print("Status:", response.status_code)

print("\nFirst 500 characters:\n")

print(response.text[:500])