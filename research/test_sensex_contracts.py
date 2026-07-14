import sys
from pathlib import Path
from pprint import pprint

import upstox_client

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

options_api = upstox_client.OptionsApi(client)

print("TOKEN LENGTH:", len(ACCESS_TOKEN))
print("TOKEN START :", ACCESS_TOKEN[:20])
print("TOKEN END   :", ACCESS_TOKEN[-20:])

try:

    result = options_api.get_option_contracts(
        "BSE_INDEX|SENSEX"
    )

    print(type(result))

    pprint(result.to_dict())

except Exception as e:

    print("ERROR")
    print(type(e))
    print(e)