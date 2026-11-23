"""controle de avaliacoes

- usuarios: suspenso_em e suspenso_motivo (quando e por que a conta saiu do app:
  suspensao pela administracao ou exclusao automatica por media baixa)
- alertas: novos tipos "avaliacao_baixa" (nota abaixo do limite) e
  "exclusao_automatica" (aluno removido por media abaixo do minimo)

Revision ID: cb5b5f498d40
Revises: cfa0c1b082ea
Create Date: 2026-11-23 09:01:03.497091

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cb5b5f498d40'
down_revision = 'cfa0c1b082ea'
branch_labels = None
depends_on = None

TIPOS_ANTES = "tipo IN ('parada_longa', 'sinal_perdido', 'desvio_rota', 'pin_sem_gps', 'botao_panico')"
TIPOS_DEPOIS = ("tipo IN ('parada_longa', 'sinal_perdido', 'desvio_rota', 'pin_sem_gps', 'botao_panico', "
                "'avaliacao_baixa', 'exclusao_automatica')")


def upgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('suspenso_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('suspenso_motivo', sa.String(length=255), nullable=True))

    with op.batch_alter_table('alertas', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_alertas_tipo'), type_='check')
        batch_op.create_check_constraint(op.f('ck_alertas_tipo'), TIPOS_DEPOIS)


def downgrade():
    # Os alertas de avaliacao so existem nesta versao: saem antes de voltar a constraint antiga
    op.execute("DELETE FROM alertas WHERE tipo IN ('avaliacao_baixa', 'exclusao_automatica')")
    with op.batch_alter_table('alertas', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_alertas_tipo'), type_='check')
        batch_op.create_check_constraint(op.f('ck_alertas_tipo'), TIPOS_ANTES)

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('suspenso_motivo')
        batch_op.drop_column('suspenso_em')
