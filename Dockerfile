#please define the corresponding dockerfile

FROM --platform=arm64 ubuntu:18.04

WORKDIR /app

COPY . /app

FROM python:3.9.9-slim-buster

WORKDIR /app

COPY ./requirements.txt /app

RUN pip install -r requirements.txt

COPY . .

EXPOSE 6060

ENV einsam=gpt-stream.py

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "6060"]