FROM python:alpine

ARG VERSION
ARG BUILD_DATE

ENV LOG_LEVEL="DEBUG"



ENV INFLUX_HOST=""
ENV INFLUX_PORT=""
ENV INFLUX_USER=""
ENV INFLUX_PASS=""
ENV INFLUX_DATABASE=""

ENV KEYID=""
ENV KEYSECRET=""            





COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY Solis-Api.py ./

CMD [ "python", "./Solis-Api" ]
