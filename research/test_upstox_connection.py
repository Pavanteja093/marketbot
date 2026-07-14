import sys
from pathlib import Path
import upstox_client

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN

print("TOKEN LENGTH:", len(ACCESS_TOKEN))
print("TOKEN START :", ACCESS_TOKEN[:20])
print("TOKEN END   :", ACCESS_TOKEN[-20:])

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

user_api = upstox_client.UserApi(client)

profile = user_api.get_profile("2.0")

print(profile)