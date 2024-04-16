import requests
from urllib.parse import urlencode
import json
import pprint

# Create test requests to our predict API
# IMPORTANT: Run the .sh file using command 'bash run_api.sh' to start the docker container before running this test

api_url = 'http://localhost:1313/predict'

data_single = {
    "x0": "-1.018506",
    "x1": "4.180869",
    "x2": "5.70305872366547",
    "x3": "-1.018506",
    "x4": "4.180869",
    "x5": "5.70305872366547",
    "x6": "-1.018506",
    "x7": "4.180869",
    "x8": "5.70305872366547",
    "x9": "-1.018506",
    "x10": "4.180869",
    "x11": "5.70305872366547",
    "x12": "-1.018506",
    "x13": "4.180869",
    "x14": "5.70305872366547",
    "x15": "-1.018506",
    "x16": "4.180869",
    "x17": "5.70305872366547",
    "x18": "-1.018506",
    "x19": "4.180869",
    "x20": "5.70305872366547",
    "x21": "-1.018506",
    "x22": "4.180869",
    "x23": "5.70305872366547",
    "x24": "-1.018506"
}


data_batch = [{
    "x0": "-1.018506",
    "x1": "4.180869",
    "x2": "5.70305872366547",
    "x3": "-1.018506",
    "x4": "4.180869",
    "x5": "5.70305872366547",
    "x6": "-1.018506",
    "x7": "4.180869",
    "x8": "5.70305872366547",
    "x9": "-1.018506",
    "x10": "4.180869",
    "x11": "5.70305872366547",
    "x12": "-1.018506",
    "x13": "4.180869",
    "x14": "5.70305872366547",
    "x15": "-1.018506",
    "x16": "4.180869",
    "x17": "5.70305872366547",
    "x18": "-1.018506",
    "x19": "4.180869",
    "x20": "5.70305872366547",
    "x21": "-1.018506",
    "x22": "4.180869",
    "x23": "5.70305872366547",
    "x24": "-1.018506"
},
{
    "x0": "-1.018506",
    "x1": "4.180869",
    "x2": "5.70305872366547",
    "x3": "-1.018506",
    "x4": "4.180869",
    "x5": "5.70305872366547",
    "x6": "-1.018506",
    "x7": "4.180869",
    "x8": "5.70305872366547",
    "x9": "-1.018506",
    "x10": "4.180869",
    "x11": "5.70305872366547",
    "x12": "-1.018506",
    "x13": "4.180869",
    "x14": "5.70305872366547",
    "x15": "-1.018506",
    "x16": "4.180869",
    "x17": "5.70305872366547",
    "x18": "-1.018506",
    "x19": "4.180869",
    "x20": "5.70305872366547",
    "x21": "-1.018506",
    "x22": "4.180869",
    "x23": "5.70305872366547",
    "x24": "-1.018506"
}]

single_url_param = urlencode({'data': json.dumps(data_single)}) # Encode the data to use in the url query
single_url_with_query = f"{api_url}?{single_url_param}"
single_response = requests.post(single_url_with_query)

batch_url_param = urlencode({'data': json.dumps(data_batch)})
batch_url_with_query = f"{api_url}?{batch_url_param}"
batch_response = requests.post(batch_url_with_query)

print('*** Single Request Test ***')
print(f'Status Code Response: {single_response}')
pprint.pprint(f'Response Data: {single_response.json()}')
print()
print('*** Batch Request Test ***')
print(f'Status Code Response: {batch_response}')
pprint.pprint(f'Response Data: {batch_response.json()}')
