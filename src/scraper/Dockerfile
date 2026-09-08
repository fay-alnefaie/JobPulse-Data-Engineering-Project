FROM python:3.12-slim

WORKDIR /App

ENV OUTPUT_DIR=/App/data/raw_data

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "tanqeeb_scraper.py"]