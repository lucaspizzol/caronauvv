"""foto de perfil, autenticador e recuperacao de senha

- fotos_perfil: arquivo da foto de perfil (no banco, porque a Vercel nao guarda arquivos em disco)
- codigos_reserva: codigos de uso unico da verificacao em duas etapas
- usuarios: segredo e estado do autenticador (TOTP), codigo do "esqueci minha senha"
  e sessao_versao (trocar a senha derruba os logins antigos)

Revision ID: 3075fbee8d79
Revises: 7c882a589454
Create Date: 2026-11-22 19:45:20.162426

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3075fbee8d79'
down_revision = '7c882a589454'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('codigos_reserva',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('codigo_hash', sa.String(length=64), nullable=False),
    sa.Column('usado_em', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_codigos_reserva_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_codigos_reserva'))
    )
    with op.batch_alter_table('codigos_reserva', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_codigos_reserva_usuario_id'), ['usuario_id'], unique=False)

    op.create_table('fotos_perfil',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=32), nullable=False),
    sa.Column('mime', sa.String(length=20), nullable=False),
    sa.Column('tamanho', sa.Integer(), nullable=False),
    sa.Column('dados', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_fotos_perfil_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fotos_perfil')),
    sa.UniqueConstraint('usuario_id', name=op.f('uq_fotos_perfil_usuario_id'))
    )
    with op.batch_alter_table('fotos_perfil', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fotos_perfil_token'), ['token'], unique=True)

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sessao_versao', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('reset_codigo_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('reset_expira_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reset_tentativas', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('reset_enviado_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('totp_segredo', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('totp_ativo', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('totp_ativado_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('totp_ultimo_passo', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('totp_falhas', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('totp_bloqueado_ate', sa.DateTime(), nullable=True))



def downgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('totp_bloqueado_ate')
        batch_op.drop_column('totp_falhas')
        batch_op.drop_column('totp_ultimo_passo')
        batch_op.drop_column('totp_ativado_em')
        batch_op.drop_column('totp_ativo')
        batch_op.drop_column('totp_segredo')
        batch_op.drop_column('reset_enviado_em')
        batch_op.drop_column('reset_tentativas')
        batch_op.drop_column('reset_expira_em')
        batch_op.drop_column('reset_codigo_hash')
        batch_op.drop_column('sessao_versao')

    with op.batch_alter_table('fotos_perfil', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fotos_perfil_token'))

    op.drop_table('fotos_perfil')
    with op.batch_alter_table('codigos_reserva', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_codigos_reserva_usuario_id'))

    op.drop_table('codigos_reserva')
