"""pedir carona (fila com prioridade)

- pedidos_carona: o aluno entra na fila (bairro, sentido, dia e faixa de horario);
  bairro_chave e o bairro sem acento/minusculo, para comparar com a carona
- caronas.prioridade_ate: ate esta hora so quem estava na fila pode pedir vaga
- revisada a mao: os CHECK (sentido, status, faixa) estao no create_table

Revision ID: 9f48643d2109
Revises: 5d1529e98c6a
Create Date: 2026-11-23 04:11:53.894166

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f48643d2109'
down_revision = '5d1529e98c6a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('pedidos_carona',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('bairro', sa.String(length=100), nullable=False),
    sa.Column('bairro_chave', sa.String(length=100), nullable=False),
    sa.Column('sentido', sa.String(length=10), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('hora_inicio', sa.Time(), nullable=False),
    sa.Column('hora_fim', sa.Time(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('carona_id', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atendido_em', sa.DateTime(), nullable=True),
    sa.CheckConstraint("sentido IN ('ida', 'volta')", name=op.f('ck_pedidos_carona_sentido')),
    sa.CheckConstraint("status IN ('aberto', 'atendido', 'expirado', 'cancelado')", name=op.f('ck_pedidos_carona_status')),
    sa.CheckConstraint('hora_fim > hora_inicio', name=op.f('ck_pedidos_carona_faixa')),
    sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id'], name=op.f('fk_pedidos_carona_aluno_id_usuarios'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['carona_id'], ['caronas.id'], name=op.f('fk_pedidos_carona_carona_id_caronas'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pedidos_carona'))
    )
    with op.batch_alter_table('pedidos_carona', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pedidos_carona_aluno_id'), ['aluno_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pedidos_carona_bairro_chave'), ['bairro_chave'], unique=False)
        batch_op.create_index(batch_op.f('ix_pedidos_carona_data'), ['data'], unique=False)
        batch_op.create_index(batch_op.f('ix_pedidos_carona_status'), ['status'], unique=False)

    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prioridade_ate', sa.DateTime(), nullable=True))



def downgrade():
    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.drop_column('prioridade_ate')

    with op.batch_alter_table('pedidos_carona', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pedidos_carona_status'))
        batch_op.drop_index(batch_op.f('ix_pedidos_carona_data'))
        batch_op.drop_index(batch_op.f('ix_pedidos_carona_bairro_chave'))
        batch_op.drop_index(batch_op.f('ix_pedidos_carona_aluno_id'))

    op.drop_table('pedidos_carona')
