FROM ubuntu:22.04 AS boost174

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    sed -i 's|http://ports.ubuntu.com/ubuntu-ports/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/|g' /etc/apt/sources.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      icu-devtools \
      libboost-date-time-dev \
      libboost-filesystem-dev \
      libboost-regex-dev \
      libicu-dev \
      libboost-system-dev; \
    mkdir -p /opt/oo-boost-1.74/include /opt/oo-boost-1.74/lib; \
    cp -a /usr/include/boost /opt/oo-boost-1.74/include/; \
    cp -a /usr/include/unicode /opt/oo-boost-1.74/include/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_date_time.a /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_date_time.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_date_time.so.1.74.0 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_filesystem.a /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_filesystem.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_filesystem.so.1.74.0 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_regex.a /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_regex.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_regex.so.1.74.0 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_system.a /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_system.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libboost_system.so.1.74.0 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicudata.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicudata.so.70 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicudata.so.70.1 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicui18n.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicui18n.so.70 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicui18n.so.70.1 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicuuc.so /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicuuc.so.70 /opt/oo-boost-1.74/lib/; \
    cp -a /usr/lib/aarch64-linux-gnu/libicuuc.so.70.1 /opt/oo-boost-1.74/lib/; \
    rm -rf /var/lib/apt/lists/*

FROM onlyoffice/documentserver:latest

ENV DEBIAN_FRONTEND=noninteractive

COPY --from=boost174 /opt/oo-boost-1.74 /opt/oo-boost-1.74

RUN set -eux; \
    sed -i 's|http://ports.ubuntu.com/ubuntu-ports/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/|g' /etc/apt/sources.list.d/ubuntu.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      binutils \
      build-essential \
      file \
      git \
      libboost-dev \
      libboost-date-time-dev \
      libboost-filesystem-dev \
      libboost-regex-dev \
      libboost-system-dev \
      libicu-dev \
      libssl-dev \
      make \
      pkg-config \
      python3 \
      qtbase5-dev; \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT []
CMD ["/bin/bash"]
