FROM python:3.6-alpine3.10
WORKDIR /usr/src/app
RUN apk add --no-cache postgresql-dev build-base musl-dev libffi libffi-dev bash
RUN addgroup -S gengine
RUN adduser -S -D -h /usr/src/app gengine gengine
RUN mkdir /run/uwsgi
RUN chown -R gengine:gengine /run/uwsgi
COPY requirements.txt ./
COPY optional-requirements.txt ./
COPY docker-files/* ./
RUN cat optional-requirements.txt >> requirements.txt && pip install -r requirements.txt
COPY . .
RUN pip install -e . && touch /tmp/nginx.socket
RUN chown -R gengine:gengine /usr/src/app
CMD [ "/bin/sh", "/usr/src/app/init.sh" ]
