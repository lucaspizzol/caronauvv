"""entrada e saida do passageiro com gps

- solicitacoes.embarque_gps_lat/lng: onde o passageiro entrou (GPS na hora do PIN)
- solicitacoes.desembarcou_em, desembarque_lat/lng: quando e onde desceu
- revisada a mao: so colunas novas e opcionais (nenhum CHECK novo)

Revision ID: ef668f938e45
Revises: 9f48643d2109
Create Date: 2026-11-23 04:28:13.437575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef668f938e45'
down_revision = '9f48643d2109'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('solicitacoes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embarque_gps_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('embarque_gps_lng', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('desembarcou_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('desembarque_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('desembarque_lng', sa.Float(), nullable=True))



def downgrade():
    with op.batch_alter_table('solicitacoes', schema=None) as batch_op:
        batch_op.drop_column('desembarque_lng')
        batch_op.drop_column('desembarque_lat')
        batch_op.drop_column('desembarcou_em')
        batch_op.drop_column('embarque_gps_lng')
        batch_op.drop_column('embarque_gps_lat')

