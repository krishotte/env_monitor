import urequests


TOKEN = "BBFF-iDvT8Vrl6JThnHZqgzNyO2Q7DAHdWs"  # Put your TOKEN here
DEVICE_LABEL = "demo"  # Put your device label here
VARIABLE_LABEL_1 = "variable1"  # Put your first variable label here
VARIABLE_LABEL_2 = "demo"  # Put your second variable label here


url = "http://things.ubidots.com/api/v1.6/devices/{}".format(DEVICE_LABEL)
headers = {"X-Auth-Token": TOKEN, "Content-Type": "application/json"}
payload = {VARIABLE_LABEL_1: 1}

req = urequests.post(url=url, headers=headers, json=payload)
