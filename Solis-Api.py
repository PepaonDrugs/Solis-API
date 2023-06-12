import json
import hashlib
import hmac
import base64
import requests
import datetime
import schedule
import os
import time
from requests.auth import AuthBase
from influxdb import InfluxDBClient
# InfluxDB configuration
host = os.environ['INFLUX_HOST']
port = 8086
database = os.environ['INFLUX_DATABASE']
measurement = 'solis'
username = os.environ['INFLUX_USER']
password = os.environ['INFLUX_PASS']


url = 'soliscloud.com:13333'




class HMACAuth(AuthBase):
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def __call__(self, r):
        content_md5 = hashlib.md5(r.body.encode()).hexdigest()
        date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        path = "/v1/api/userStationList"
        param = f"POST\n{content_md5}\napplication/json\n{date}\n{path}"
        signature = hmac.new(self.secret.encode(), param.encode(), hashlib.sha1).digest()
        signature = base64.b64encode(signature).decode()
        r.headers["Content-MD5"] = content_md5
        r.headers["Date"] = date
        r.headers["Authorization"] = f"API {self.key}:{signature}"
        return r

def write_to_influxdb(data):
    client = InfluxDBClient(host=host, port=port, username=username, password=password)
    client.switch_database(database)

    numeric_fields = [
        "all", "normal", "fault", "offline", "building", "mppt", "fullHour",
        "dayPowerGeneration", "monthCarbonDioxide", "dip", "azimuth", "power",
        "timeZone", "daylight", "price", "capacity", "capacityPercent",
        "dayEnergy", "dayIncome", "monthEnergy", "yearEnergy", "allEnergy",
        "allEnergy1", "allIncome", "updateDate", "type", "epmType", "gridSwitch",
        "gridSwitch1", "dcInputType", "stationTypeNew", "batteryTotalDischargeEnergy",
        "batteryTotalChargeEnergy", "gridPurchasedTotalEnergy", "gridSellTotalEnergy",
        "homeLoadTotalEnergy", "oneSelf", "batteryTodayDischargeEnergy",
        "batteryTodayChargeEnergy", "gridPurchasedTodayEnergy", "gridSellTodayEnergy",
        "homeLoadTodayEnergy", "oneSelfTotal", "monthEnergy1", "dayEnergy1",
        "yearEnergy1", "power1"
    ]

    json_body = [
        {
            "measurement": measurement,
            "fields": {
                field: float(data["data"]["page"]["records"][0][field])
                for field in numeric_fields if field in data["data"]["page"]["records"][0]
            }
        }
    ]

    client.write_points(json_body)

def main():
    try:
        key = os.environ['KEYID']
        key_secret = os.environ['KEYSECRET']
        url = "https://soliscloud.com:13333" + "/v1/api/userStationList"
        data = {"pageNo": 1, "pageSize": 10}
        body = json.dumps(data)
        headers = {
            "Content-type": "application/json;charset=UTF-8",
        }
        auth = HMACAuth(key, key_secret)
        response = requests.post(url, data=body, headers=headers, auth=auth)
        print(response.text)

        # Write data to InfluxDB
        json_data = json.loads(response.text)
        write_to_influxdb(json_data)
    except Exception as e:
        print(e)

def job():
    print("Running job...")
    main()

# Schedule the job to run every 5 minutes
schedule.every(5).minutes.do(job)

# Run the scheduler
while True:
    schedule.run_pending()