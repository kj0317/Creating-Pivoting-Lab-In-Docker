FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    iputils-ping \
    iproute2 \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/webapp/app.py

EXPOSE 80

CMD ["python3", "/opt/webapp/app.py"]
