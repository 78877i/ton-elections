FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install -y python3 python3-pip

ADD infrastructure/requirements/webserver.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt

COPY . /usr/src/validation_service
WORKDIR /usr/src/validation_service

ENTRYPOINT [ "gunicorn", "webserver.main:app", "-k", "uvicorn.workers.UvicornWorker" ]