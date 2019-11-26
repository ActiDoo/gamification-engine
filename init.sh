cd /usr/src/app/ && \
initialize_gengine_db $INI_FILE $RESET_DB admin_password=$ADMIN_PASSWORD admin_user=$ADMIN_USER && \
if [ -z "$UWSGI_CONF" ]
then 
    pserve development.ini
else
    # --lazy-apps -> https://stackoverflow.com/questions/43648075/uwsgi-flask-sqlalchemy-intermittent-postgresql-errors-with-warning-there-is-al
    # or change to 1 worker
    uwsgi --lazy-apps --ini-paste $UWSGI_CONF
fi