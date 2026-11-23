"""historico da administracao

- acoes_admin: cada acao de moderacao (aprovar/recusar selo e documento, suspender,
  reativar, remover foto, desligar 2 etapas, denuncia, alerta, regras, exportar dados)
  e a exclusao automatica feita pelo sistema (admin_id vazio)
- revisada a mao: o CHECK das acoes esta no create_table

Revision ID: d7a3c19e5b20
Revises: cb5b5f498d40
Create Date: 2026-11-23 11:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7a3c19e5b20'
down_revision = 'cb5b5f498d40'
branch_labels = None
depends_on = None

ACOES = ("acao IN ('aprovar_selo', 'recusar_selo', 'suspender', 'reativar', 'remover_foto', 'resetar_2fa', "
         "'aprovar_documento', 'recusar_documento', 'analisar_denuncia', 'encerrar_denuncia', "
         "'resolver_alerta', 'alterar_regras', 'exportar_dados', 'exclusao_automatica')")


def upgrade():
    op.create_table('acoes_admin',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=True),
    sa.Column('acao', sa.String(length=30), nullable=False),
    sa.Column('alvo_id', sa.Integer(), nullable=True),
    sa.Column('alvo_nome', sa.String(length=120), nullable=True),
    sa.Column('detalhe', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint(ACOES, name=op.f('ck_acoes_admin_acao')),
    sa.ForeignKeyConstraint(['admin_id'], ['usuarios.id'], name=op.f('fk_acoes_admin_admin_id_usuarios'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['alvo_id'], ['usuarios.id'], name=op.f('fk_acoes_admin_alvo_id_usuarios'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_acoes_admin'))
    )
    with op.batch_alter_table('acoes_admin', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_acoes_admin_acao'), ['acao'], unique=False)
        batch_op.create_index(batch_op.f('ix_acoes_admin_admin_id'), ['admin_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_acoes_admin_alvo_id'), ['alvo_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_acoes_admin_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('acoes_admin', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_acoes_admin_created_at'))
        batch_op.drop_index(batch_op.f('ix_acoes_admin_alvo_id'))
        batch_op.drop_index(batch_op.f('ix_acoes_admin_admin_id'))
        batch_op.drop_index(batch_op.f('ix_acoes_admin_acao'))

    op.drop_table('acoes_admin')
