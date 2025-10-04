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
import paho.mqtt.client as mqtt

# InfluxDB configuration
host = os.environ['INFLUX_HOST']
port = 8086
database = os.environ['INFLUX_DATABASE']
measurement = 'solis'
username = os.environ['INFLUX_USER']
password = os.environ['INFLUX_PASS']

# MQTT configuration
ENABLE_MQTT = os.environ.get("ENABLE_MQTT", "false").lower() == "true"
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "solis/data")
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")

mqtt_client = None  # global client


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


def on_disconnect(client, userdata, rc):
    """Try to reconnect on disconnect"""
    if rc != 0:
        print("MQTT disconnected, trying to reconnect...")
        reconnect_mqtt(client)


def reconnect_mqtt(client):
    while True:
        try:
            client.reconnect()
            print("Reconnected to MQTT broker")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}, retrying in 5s...")
            time.sleep(5)


def init_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client()
    if MQTT_USER and MQTT_PASS:
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

    mqtt_client.on_disconnect = on_disconnect

    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()  # background thread handles reconnect
        print(f"Connected to MQTT broker {MQTT_HOST}:{MQTT_PORT}")
    except Exception as e:
        print(f"Initial MQTT connection failed: {e}")


def publish_mqtt(data):
    if mqtt_client:
        try:
            record = data["data"]["page"]["records"][0]
            for field in numeric_fields:
                if field in record:
                    topic = f"{MQTT_TOPIC}/{field}"
                    mqtt_client.publish(topic, record[field])
            print(f"Published {len(record)} fields to MQTT under {MQTT_TOPIC}/<field>")
        except Exception as e:
            print(f"MQTT publish error: {e}")



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

        # Convert response to JSON
        json_data = json.loads(response.text)

        # Write data to InfluxDB
        write_to_influxdb(json_data)

        # Publish to MQTT if enabled
        if ENABLE_MQTT:
            publish_mqtt(json_data)

    except Exception as e:
        print(e)


def job():
    print("Running job...")
    main()


# Initialize MQTT if enabled
if ENABLE_MQTT:
    init_mqtt()

# Schedule the job to run every 4 minutes
schedule.every(4).minutes.do(job)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)

