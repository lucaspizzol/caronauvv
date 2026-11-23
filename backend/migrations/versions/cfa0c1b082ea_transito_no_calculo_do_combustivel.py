"""transito no calculo do combustivel

- caronas.trechos_transito: trechos criticos escolhidos (Terceira Ponte, Segunda Ponte,
  Rodovia do Sol, BR-101/Carapina), separados por virgula
- caronas.transito_percentual: acrescimo no consumo aplicado na conta (horario de pico + trechos)
- revisada a mao: so colunas novas e opcionais (os valores validos sao checados no schema)

Revision ID: cfa0c1b082ea
Revises: ef668f938e45
Create Date: 2026-11-23 04:34:40.267733

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cfa0c1b082ea'
down_revision = 'ef668f938e45'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trechos_transito', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('transito_percentual', sa.Integer(), nullable=True))



def downgrade():
    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.drop_column('transito_percentual')
        batch_op.drop_column('trechos_transito')

