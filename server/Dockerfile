FROM python:3.7.1-alpine3.8

RUN apk --no-cache update && apk --no-cache add build-base git sqlite-dev pcre-dev
WORKDIR /tmp/
RUN git clone https://github.com/ralight/sqlite3-pcre.git
RUN cd sqlite3-pcre && make && make install
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt && rm /tmp/requirements.txt
WORKDIR /
