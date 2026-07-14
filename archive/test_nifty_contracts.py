import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import upstox_client
import traceback

from config.upstox_config import ACCESS_TOKEN

print("Starting...")

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

options_api = upstox_client.OptionsApi(client)

try:

    print("Calling API...")

    result = options_api.get_option_contracts(
        instrument_key="NSE_INDEX|Nifty 50"
    )

    print("SUCCESS")
    print(type(result))
    print(result)

except Exception as e:

    print("ERROR")
    print(type(e))
    print(str(e))

    traceback.print_exc()

input("\nPress Enter to exit...")