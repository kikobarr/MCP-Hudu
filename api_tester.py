import os
import json
import requests

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("HUDU_API_KEY")

# url = "https://calpolyhumboldt.huducloud.com/api/v1/companies"
# # url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=ACAC-S33381"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=ANEX_007A" # location
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=S33381" # device
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?page=1&page_size=10"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=Emily R Oparowski"
url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?page=1&page_size=15&search=Emily"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?page=1&page_size=100&search=S33381"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/companies"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/companies/3/assets/28840"


headers = {"x-api-key": api_key}
response = requests.get(url, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=4))

