FROM python:3.6-alpine
WORKDIR /usr/src/app
RUN apk add --no-cache postgresql-dev build-base musl-dev libffi libffi-dev

COPY requirements.txt .
COPY optional-requirements.txt .
RUN cat optional-requirements.txt >> requirements.txt && pip install -r requirements.txt
COPY . .
ARG SETUP_MODE
RUN python setup.py ${SETUP_MODE} && touch /tmp/nginx.socket
CMD [ "/bin/sh", "/usr/src/app/init.sh" ]