"""rename properties to achievement properties

Revision ID: 3740c3deb378
Revises: 5018059c5c8f
Create Date: 2015-09-23 12:23:05.418501

"""

# revision identifiers, used by Alembic.
revision = '3740c3deb378'
down_revision = '5018059c5c8f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('properties','achievementproperties')
    op.rename_table('achievements_properties','achievements_achievementproperties')

def downgrade():
    op.rename_table('achievementproperties','properties')
    op.rename_table('achievements_achievementproperties','achievements_properties')