FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --quiet
COPY . .
CMD ["python3", "poller.py"]
