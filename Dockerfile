FROM python:3

WORKDIR /app

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD [ "python", "application.py" ]