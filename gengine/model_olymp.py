from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.orm import mapper
from sqlalchemy.sql.schema import Table, Column, MetaData
import sqlalchemy.types as ty

from gengine.metadata import Base, DBSession
from gengine.model_base import ABase

OLYMP_SCHEMA = "olymp"

t_tenants = Table("tenants", Base.metadata,
    Column("id", ty.String(), primary_key=True),
    schema = OLYMP_SCHEMA
)


class Tenant(ABase):
    def __unicode__(self, *args, **kwargs):
        return "(ID: %s)" % (self.id,)


mapper(Tenant, t_tenants)


@event.listens_for(Tenant, "after_insert")
def create_tenant_schema(mapper, connection, target):
    tenant_meta = MetaData(bind=connection)
    schema = "t_"+target.id

    connection.execute("CREATE SCHEMA IF NOT EXISTS "+schema)
    connection.execute("SET search_path TO "+schema)

    from . import model_tenant

    tables = [t.tometadata(tenant_meta, schema=schema) for name, t in model_tenant.__dict__.items() if isinstance(t, Table)]

    tenant_meta.create_all(tables=tables)

    alembic_cfg = Config(attributes={
        'engine' : connection,
        'schema' : schema
    })
    alembic_cfg.set_main_option("script_location", "gengine/alembic")
    command.stamp(alembic_cfg, "head")