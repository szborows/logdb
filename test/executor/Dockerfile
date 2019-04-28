FROM python:3.7.1-alpine3.8
RUN apk --no-cache update && apk --no-cache add jq bash curl
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt && rm /tmp/requirements.txt
