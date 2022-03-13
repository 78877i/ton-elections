FROM ubuntu:20.04

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata

RUN apt install -y build-essential cmake clang-6.0 openssl libssl-dev zlib1g-dev gperf wget git curl libreadline-dev ccache libmicrohttpd-dev

WORKDIR /
RUN git clone --recurse-submodules https://github.com/newton-blockchain/ton.git

RUN mkdir /ton/build
WORKDIR /ton/build
ENV CC clang-6.0
ENV CXX clang++-6.0
RUN cmake -DCMAKE_BUILD_TYPE=Release ..
RUN cmake --build . -j$(nproc) --target lite-client