FROM python:3.12-slim

WORKDIR /App

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY extract_skills.py .

CMD ["python", "extract_skills.py"]
