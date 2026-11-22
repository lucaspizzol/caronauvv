"""confianca, preferencias e ciclo da viagem

- usuarios: bio, preferencias de viagem (conversa, musica, animais, fumar),
  verificacao do e-mail UVV por codigo e pedido do selo "perfil verificado"
- caronas: observacoes do motorista
- solicitacoes: novo metodo de embarque "pin" (motorista digita o PIN do passageiro)
- alertas: novo tipo "botao_panico" (botao de emergencia)

Revision ID: 7c882a589454
Revises: 147f968c7f74
Create Date: 2026-11-22 17:53:04.530118

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c882a589454'
down_revision = '147f968c7f74'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('observacoes', sa.String(length=300), nullable=True))

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bio', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('pref_conversa', sa.String(length=15), server_default='depende', nullable=False))
        batch_op.add_column(sa.Column('pref_musica', sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(sa.Column('pref_animais', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('pref_fumar', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('email_verificado', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('codigo_verificacao_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('codigo_expira_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('codigo_tentativas', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('verificacao_solicitada_em', sa.DateTime(), nullable=True))
        batch_op.create_check_constraint(
            op.f('ck_usuarios_pref_conversa'), "pref_conversa IN ('quieto', 'depende', 'conversador')")

    # Quem ja tinha conta antes da verificacao por codigo entra como e-mail confirmado
    op.execute(sa.text("UPDATE usuarios SET email_verificado = :sim").bindparams(sim=True))

    with op.batch_alter_table('solicitacoes', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_solicitacoes_metodo_embarque'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_solicitacoes_metodo_embarque'), "metodo_embarque IN ('pin', 'pin+gps', 'gps', 'manual')")

    with op.batch_alter_table('alertas', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_alertas_tipo'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_alertas_tipo'),
            "tipo IN ('parada_longa', 'sinal_perdido', 'desvio_rota', 'pin_sem_gps', 'botao_panico')")


def downgrade():
    # Antes de voltar as constraints antigas, converte os valores que so existem nesta versao
    op.execute("UPDATE solicitacoes SET metodo_embarque = 'manual' WHERE metodo_embarque = 'pin'")
    op.execute("UPDATE alertas SET tipo = 'parada_longa' WHERE tipo = 'botao_panico'")

    with op.batch_alter_table('alertas', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_alertas_tipo'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_alertas_tipo'), "tipo IN ('parada_longa', 'sinal_perdido', 'desvio_rota', 'pin_sem_gps')")

    with op.batch_alter_table('solicitacoes', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_solicitacoes_metodo_embarque'), type_='check')
        batch_op.create_check_constraint(
            op.f('ck_solicitacoes_metodo_embarque'), "metodo_embarque IN ('pin+gps', 'gps', 'manual')")

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_usuarios_pref_conversa'), type_='check')
        batch_op.drop_column('verificacao_solicitada_em')
        batch_op.drop_column('codigo_tentativas')
        batch_op.drop_column('codigo_expira_em')
        batch_op.drop_column('codigo_verificacao_hash')
        batch_op.drop_column('email_verificado')
        batch_op.drop_column('pref_fumar')
        batch_op.drop_column('pref_animais')
        batch_op.drop_column('pref_musica')
        batch_op.drop_column('pref_conversa')
        batch_op.drop_column('bio')

    with op.batch_alter_table('caronas', schema=None) as batch_op:
        batch_op.drop_column('observacoes')
