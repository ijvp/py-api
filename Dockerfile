FROM python:3

WORKDIR /user/app

COPY application.py ./

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD [ "python", "application.py" ]