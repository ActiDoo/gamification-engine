FROM python:3.6-stretch

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
     postgresql-client git-core libgeos-dev libldap2-dev libsasl2-dev build-essential \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /usr/local/nvm

WORKDIR /usr/src/app

RUN addgroup --system gengine \
    && adduser --system --disabled-password --home /usr/src/app --ingroup gengine gengine \
    && mkdir /run/uwsgi \
    && chown -R gengine:gengine /run/uwsgi

COPY . .

RUN pip install -r requirements.txt && pip install -r optional-requirements.txt \
&& pip install -e . \
&& chown -R gengine:gengine /usr/src/app

CMD [ "/bin/bash", "/usr/src/app/init.sh" ]