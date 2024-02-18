FROM python:3.11.5-slim
ENV PYTHONBUFFERED=1

RUN apt-get update && \
    apt-get -y install libpq-dev gcc && \
    apt-get autoremove && rm -r /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

COPY . /app/
RUN pip install --no-cache-dir -r requirements.txt

CMD python bot.py
