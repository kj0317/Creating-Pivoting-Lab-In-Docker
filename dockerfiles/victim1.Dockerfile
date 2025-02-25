FROM phusion/baseimage:jammy-1.0.4

RUN apt update -y \
    && apt install -y \
	python3-pip \
	wget	\
	&& apt clean

WORKDIR /opt

RUN wget "https://github.com/cemtan/sar2html/archive/refs/tags/4.0.0.tar.gz" \
    && tar -xvf *

WORKDIR /opt/sar2html-4.0.0/

RUN pip3 install -r requirements.txt
RUN chmod +x startWeb
CMD ["./startWeb"]
