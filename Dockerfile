FROM python:3.8-slim

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

EXPOSE 5000

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]

#CMD ["gunicorn" , "--timeout", "180", "-b", "0.0.0.0:5000", "app:app"]
