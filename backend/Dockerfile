FROM python:3.8.19-alpine3.20

WORKDIR /app

COPY ./requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD python3 app.py

#CMD ["python3", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
