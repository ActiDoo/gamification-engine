#!/bin/bash

cd /usr/src/app/ || exit

if [[ ! $APP_DB_HOST ]]; then
    echo "\$APP_DB_HOST is unset";
    exit 1;
fi

if [[ ! $APP_DB_PORT ]]; then
    echo "\$APP_DB_PORT is unset";
    exit 1;
fi

if [[ ! $APP_DB_USER ]]; then
    echo "\$APP_DB_USER is unset";
    exit 1;
fi

if [[ ! $APP_DB_PASSWORD ]]; then
    echo "\$APP_DB_PASSWORD is unset";
    exit 1;
fi

if [[ ! $APP_DB_NAME ]]; then
    echo "\$APP_DB_NAME is unset";
    exit 1;
fi

if [[ !  $APP_DB_DRIVER ]]; then
    export APP_DB_DRIVER="postgres";
    echo "\$APP_DB_DRIVER is unset, assuming postgres";
fi

export DATABASE_URL="${APP_DB_DRIVER}://${APP_DB_USER}:${APP_DB_PASSWORD}@${APP_DB_HOST}:${APP_DB_PORT}/${APP_DB_NAME}"

./wait-for-it.sh -t 30 -s "${APP_DB_HOST}:${APP_DB_PORT}"

sleep 10

if [ "$MODE" == "dev" ]
then
  initialize_gengine_db development.ini "admin_password=${ADMIN_PASSWORD}" "admin_user=${ADMIN_USER}" "populate_demo=true"
  uwsgi --lazy-apps --ini-paste docker-files/development.uwsgi --py-autoreload=1
else
  initialize_gengine_db docker-files/production.ini "admin_password=${ADMIN_PASSWORD}" "admin_user=${ADMIN_USER}"
  uwsgi --lazy-apps --ini-paste docker-files/production.uwsgi
fi
