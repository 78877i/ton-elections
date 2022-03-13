FROM ubuntu:20.04

RUN apt-get update
# RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
RUN apt-get install -y python3 python3-pip

ADD infrastructure/requirements/indexer.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt

COPY . /usr/src/validation_service
WORKDIR /usr/src/validation_service

ARG TON_CONFIG_FILE
COPY ${TON_CONFIG_FILE} liteserver_config.json

ENTRYPOINT ["celery", "-A", "indexer", "worker", "-B", "--loglevel=INFO"]