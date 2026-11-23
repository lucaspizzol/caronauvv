"""documentos e calculo do combustivel

- documentos: identidade e CNH enviadas para verificacao (a imagem e apagada
  depois da analise da administracao; fica so o resultado)
- veiculos: tipo de energia (gasolina, etanol, flex, diesel, hibrido, eletrico)
  e consumo (km por litro; no eletrico, km por kWh)
- caronas: detalhamento do rateio (energia e consumo usados, combustivel e
  adicional por passageiro)

Revision ID: 5d1529e98c6a
Revises: 3075fbee8d79
Create Date: 2026-11-22 23:26:11.124691

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d1529e98c6a'
down_revision = '3075fbee8d79'
branch_labels = None
depends_on = None

ENERGIAS = "energia IN ('gasolina', 'etanol', 'flex', 'diesel', 'hibrido', 'eletrico')"


def upgrade():
    op.create_table('documentos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('validade', sa.Date(), nullable=True),
    sa.Column('mime', sa.String(length=20), nullable=True),
    sa.Column('tamanho', sa.Integer(), nullable=True),
    sa.Column('dados', sa.LargeBinary(), nullable=True),
    sa.Column('motivo_recusa', sa.String(length=255), nullable=True),
    sa.Column('enviado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('analisado_em', sa.DateTime(), nullable=True),
    sa.Column('analisado_por_id', sa.Integer(), nullable=True),
    sa.CheckConstraint("status IN ('pendente', 'aprovado', 'recusado')", name=op.f('ck_documentos_status')),
    sa.CheckConstraint("tipo IN ('identidade', 'cnh')", name=op.f('ck_documentos_tipo')),
    sa.ForeignKeyConstraint(['analisado_por_id'], ['usuarios.id'], name=op.f('fk_documentos_analisado_por_id_usuarios'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_documentos_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documentos')),
    sa.UniqueConstraint('usuario_id', 'tipo', name='uq_documentos_usuario_tipo')
    )
    with op.batch_alter_table('documentos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documentos_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_documentos_usuario_id'), ['usuario_id'], unique=False)

    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('energia', sa.String(length=15), nullable=True))
        batch_op.add_column(sa.Column('consumo_km', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('combustivel_por_passageiro', sa.Numeric(precision=6, scale=2), nullable=True))
        batch_op.add_column(sa.Column('adicional_por_passageiro', sa.Numeric(precision=6, scale=2), nullable=True))
        batch_op.create_check_constraint(
            op.f('ck_caronas_adicional'), "adicional_por_passageiro IS NULL OR adicional_por_passageiro >= 0")

    # Carros ja cadastrados entram como "flex", sem consumo (o calculo usa a media ate o dono informar)
    with op.batch_alter_table('veiculos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('energia', sa.String(length=15), server_default='flex', nullable=False))
        batch_op.add_column(sa.Column('consumo_km', sa.Float(), nullable=True))
        batch_op.create_check_constraint(op.f('ck_veiculos_energia'), ENERGIAS)
        batch_op.create_check_constraint(
            op.f('ck_veiculos_consumo'), "consumo_km IS NULL OR (consumo_km > 0 AND consumo_km <= 60)")


def downgrade():
    with op.batch_alter_table('veiculos', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_veiculos_consumo'), type_='check')
        batch_op.drop_constraint(op.f('ck_veiculos_energia'), type_='check')
        batch_op.drop_column('consumo_km')
        batch_op.drop_column('energia')

    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_caronas_adicional'), type_='check')
        batch_op.drop_column('adicional_por_passageiro')
        batch_op.drop_column('combustivel_por_passageiro')
        batch_op.drop_column('consumo_km')
        batch_op.drop_column('energia')

    with op.batch_alter_table('documentos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documentos_usuario_id'))
        batch_op.drop_index(batch_op.f('ix_documentos_status'))

    op.drop_table('documentos')
