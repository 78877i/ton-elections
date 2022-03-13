#!/bin/bash
set -e

PROJECT_ROOT=`dirname "$0"`/../..

echo "Building image"
docker build -t lite-client-builder -f ${PROJECT_ROOT}/infrastructure/lite-client.Dockerfile . $@

echo "Running container"
CONTAINER_ID=$(docker run -d -t lite-client-builder)

echo "Copying lite-client"
docker cp ${CONTAINER_ID}:/ton/build/lite-client/lite-client ${PROJECT_ROOT}/distlib/lite-client

echo "Removing container"
docker container rm ${CONTAINER_ID}
