FROM python:3.7-slim-buster as base

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc wget

RUN pip install --upgrade pip
RUN pip install numpy

# TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install

RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz

# Install plutous
RUN mkdir plutous
COPY . plutous
RUN pip install -e plutous