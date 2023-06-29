FROM python:3

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8081

CMD ["gunicorn", "-b", "0.0.0.0:8080", "application.py"]