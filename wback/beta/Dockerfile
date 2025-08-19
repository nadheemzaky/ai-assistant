FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /BETA

COPY requirements.txt .
RUN apt-get update && apt-get install -y build-essential libpq-dev
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]

#docker-compose up --build -d