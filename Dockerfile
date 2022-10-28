FROM python:3.11-bullseye
LABEL maintainer="Paul Grave <paul@stomer.com>"

WORKDIR /opt/resource

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /opt/src/
COPY src/octopus.py /opt/src/octopus.py
COPY assets/* /opt/resource/
