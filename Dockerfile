FROM python:alpine

ARG VERSION
ARG BUILD_DATE

ENV LOG_LEVEL="DEBUG"



ENV INFLUX_HOST=""
ENV INFLUX_USER=""
ENV INFLUX_PASS=""
ENV INFLUX_DATABASE=""

ENV KEYID=""
ENV KEYSECRET=""            


# MQTT configuration
ENV ENABLE_MQTT="false"
ENV MQTT_HOST="mqtt"
ENV MQTT_PORT=1883
ENV MQTT_TOPIC="solis/data"
ENV MQTT_USER=""
ENV MQTT_PASS=""


COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY Solis-Api.py ./

CMD [ "python", "./Solis-Api.py" ]
