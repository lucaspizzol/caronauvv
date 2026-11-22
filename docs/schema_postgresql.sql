-- CaronaUVV - esquema para PostgreSQL (gerado de db.metadata).
-- Em producao o normal e rodar 'flask db upgrade'; este arquivo serve de referencia.

CREATE TABLE configuracoes (
	chave VARCHAR(60) NOT NULL, 
	valor VARCHAR(255) NOT NULL, 
	descricao VARCHAR(255), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_configuracoes PRIMARY KEY (chave)
);


CREATE TABLE usuarios (
	id SERIAL NOT NULL, 
	matricula VARCHAR(20) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	nome VARCHAR(150) NOT NULL, 
	curso VARCHAR(120), 
	telefone VARCHAR(20) NOT NULL, 
	bairro VARCHAR(100) NOT NULL, 
	endereco VARCHAR(255), 
	casa_lat FLOAT, 
	casa_lng FLOAT, 
	foto_url VARCHAR(500), 
	chave_pix VARCHAR(150), 
	senha_hash VARCHAR(255) NOT NULL, 
	is_admin BOOLEAN NOT NULL, 
	verificado BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	ultimo_login_em TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_usuarios PRIMARY KEY (id)
);

CREATE INDEX ix_usuarios_bairro ON usuarios (bairro);
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);
CREATE UNIQUE INDEX ix_usuarios_matricula ON usuarios (matricula);

CREATE TABLE buscas (
	id SERIAL NOT NULL, 
	usuario_id INTEGER, 
	bairro VARCHAR(100) NOT NULL, 
	sentido VARCHAR(10) NOT NULL, 
	data_desejada DATE NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE, 
	hora_fim TIME WITHOUT TIME ZONE, 
	qtd_resultados INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_buscas PRIMARY KEY (id), 
	CONSTRAINT ck_buscas_sentido CHECK (sentido IN ('ida', 'volta')), 
	CONSTRAINT fk_buscas_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_buscas_bairro ON buscas (bairro);
CREATE INDEX ix_buscas_created_at ON buscas (created_at);
CREATE INDEX ix_buscas_usuario_id ON buscas (usuario_id);

CREATE TABLE contatos_confianca (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	telefone VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_contatos_confianca PRIMARY KEY (id), 
	CONSTRAINT fk_contatos_confianca_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_contatos_confianca_usuario_id ON contatos_confianca (usuario_id);

CREATE TABLE veiculos (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	modelo VARCHAR(80) NOT NULL, 
	cor VARCHAR(30) NOT NULL, 
	placa VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_veiculos PRIMARY KEY (id), 
	CONSTRAINT fk_veiculos_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	CONSTRAINT uq_veiculos_placa UNIQUE (placa)
);

CREATE INDEX ix_veiculos_usuario_id ON veiculos (usuario_id);

CREATE TABLE caronas (
	id SERIAL NOT NULL, 
	motorista_id INTEGER NOT NULL, 
	veiculo_id INTEGER, 
	sentido VARCHAR(10) NOT NULL, 
	bairro_origem VARCHAR(100) NOT NULL, 
	endereco_origem VARCHAR(255) NOT NULL, 
	destino VARCHAR(255) NOT NULL, 
	origem_lat FLOAT, 
	origem_lng FLOAT, 
	destino_lat FLOAT, 
	destino_lng FLOAT, 
	distancia_km FLOAT, 
	duracao_min INTEGER, 
	rota_polyline TEXT, 
	data_hora_saida TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	vagas INTEGER NOT NULL, 
	valor_por_passageiro NUMERIC(6, 2) NOT NULL, 
	reserva_automatica BOOLEAN NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	iniciada_em TIMESTAMP WITHOUT TIME ZONE, 
	concluida_em TIMESTAMP WITHOUT TIME ZONE, 
	cancelada_em TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_caronas PRIMARY KEY (id), 
	CONSTRAINT ck_caronas_vagas CHECK (vagas BETWEEN 1 AND 6), 
	CONSTRAINT ck_caronas_valor CHECK (valor_por_passageiro >= 0), 
	CONSTRAINT ck_caronas_sentido CHECK (sentido IN ('ida', 'volta')), 
	CONSTRAINT ck_caronas_status CHECK (status IN ('ativa', 'lotada', 'em_andamento', 'concluida', 'cancelada')), 
	CONSTRAINT fk_caronas_motorista_id_usuarios FOREIGN KEY(motorista_id) REFERENCES usuarios (id), 
	CONSTRAINT fk_caronas_veiculo_id_veiculos FOREIGN KEY(veiculo_id) REFERENCES veiculos (id) ON DELETE SET NULL
);

CREATE INDEX ix_caronas_bairro_origem ON caronas (bairro_origem);
CREATE INDEX ix_caronas_data_hora_saida ON caronas (data_hora_saida);
CREATE INDEX ix_caronas_motorista_id ON caronas (motorista_id);
CREATE INDEX ix_caronas_status ON caronas (status);

CREATE TABLE alertas (
	id SERIAL NOT NULL, 
	carona_id INTEGER NOT NULL, 
	usuario_id INTEGER, 
	tipo VARCHAR(30) NOT NULL, 
	detalhe VARCHAR(300), 
	lat FLOAT, 
	lng FLOAT, 
	resposta VARCHAR(20), 
	respondido_em TIMESTAMP WITHOUT TIME ZONE, 
	status VARCHAR(20) NOT NULL, 
	contatos_avisados_em TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	resolvido_em TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT pk_alertas PRIMARY KEY (id), 
	CONSTRAINT ck_alertas_tipo CHECK (tipo IN ('parada_longa', 'sinal_perdido', 'desvio_rota', 'pin_sem_gps')), 
	CONSTRAINT ck_alertas_resposta CHECK (resposta IN ('tudo_bem', 'preciso_ajuda', 'sem_resposta')), 
	CONSTRAINT ck_alertas_status CHECK (status IN ('aguardando', 'em_revisao', 'resolvido')), 
	CONSTRAINT fk_alertas_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alertas_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_alertas_carona_id ON alertas (carona_id);
CREATE INDEX ix_alertas_created_at ON alertas (created_at);
CREATE INDEX ix_alertas_status ON alertas (status);

CREATE TABLE denuncias (
	id SERIAL NOT NULL, 
	denunciante_id INTEGER NOT NULL, 
	denunciado_id INTEGER NOT NULL, 
	carona_id INTEGER, 
	motivo VARCHAR(60) NOT NULL, 
	descricao TEXT, 
	status VARCHAR(20) NOT NULL, 
	analisada_por_id INTEGER, 
	resolucao TEXT, 
	encerrada_em TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_denuncias PRIMARY KEY (id), 
	CONSTRAINT ck_denuncias_nao_autodenunciar CHECK (denunciante_id <> denunciado_id), 
	CONSTRAINT ck_denuncias_status CHECK (status IN ('aberta', 'em_analise', 'encerrada')), 
	CONSTRAINT fk_denuncias_denunciante_id_usuarios FOREIGN KEY(denunciante_id) REFERENCES usuarios (id), 
	CONSTRAINT fk_denuncias_denunciado_id_usuarios FOREIGN KEY(denunciado_id) REFERENCES usuarios (id), 
	CONSTRAINT fk_denuncias_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE SET NULL, 
	CONSTRAINT fk_denuncias_analisada_por_id_usuarios FOREIGN KEY(analisada_por_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_denuncias_denunciado_id ON denuncias (denunciado_id);
CREATE INDEX ix_denuncias_denunciante_id ON denuncias (denunciante_id);
CREATE INDEX ix_denuncias_status ON denuncias (status);

CREATE TABLE links_compartilhados (
	id SERIAL NOT NULL, 
	carona_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	contato_id INTEGER, 
	token VARCHAR(64) NOT NULL, 
	expira_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revogado_em TIMESTAMP WITHOUT TIME ZONE, 
	acessos INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_links_compartilhados PRIMARY KEY (id), 
	CONSTRAINT fk_links_compartilhados_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE CASCADE, 
	CONSTRAINT fk_links_compartilhados_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	CONSTRAINT fk_links_compartilhados_contato_id_contatos_confianca FOREIGN KEY(contato_id) REFERENCES contatos_confianca (id) ON DELETE SET NULL
);

CREATE INDEX ix_links_compartilhados_carona_id ON links_compartilhados (carona_id);
CREATE UNIQUE INDEX ix_links_compartilhados_token ON links_compartilhados (token);

CREATE TABLE notificacoes (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	carona_id INTEGER, 
	tipo VARCHAR(40) NOT NULL, 
	titulo VARCHAR(120) NOT NULL, 
	texto VARCHAR(500) NOT NULL, 
	lida BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_notificacoes PRIMARY KEY (id), 
	CONSTRAINT fk_notificacoes_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	CONSTRAINT fk_notificacoes_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE SET NULL
);

CREATE INDEX ix_notificacoes_created_at ON notificacoes (created_at);
CREATE INDEX ix_notificacoes_usuario_id ON notificacoes (usuario_id);
CREATE INDEX ix_notificacoes_usuario_lida ON notificacoes (usuario_id, lida);

CREATE TABLE posicoes_gps (
	id SERIAL NOT NULL, 
	carona_id INTEGER NOT NULL, 
	lat FLOAT NOT NULL, 
	lng FLOAT NOT NULL, 
	registrada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_posicoes_gps PRIMARY KEY (id), 
	CONSTRAINT fk_posicoes_gps_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE CASCADE
);

CREATE INDEX ix_posicoes_gps_carona_id ON posicoes_gps (carona_id);
CREATE INDEX ix_posicoes_gps_registrada_em ON posicoes_gps (registrada_em);

CREATE TABLE solicitacoes (
	id SERIAL NOT NULL, 
	carona_id INTEGER NOT NULL, 
	passageiro_id INTEGER NOT NULL, 
	endereco_embarque VARCHAR(255), 
	embarque_lat FLOAT, 
	embarque_lng FLOAT, 
	desvio_min INTEGER, 
	distancia_rota_m INTEGER, 
	mensagem VARCHAR(300), 
	status VARCHAR(20) NOT NULL, 
	respondida_em TIMESTAMP WITHOUT TIME ZONE, 
	expira_em TIMESTAMP WITHOUT TIME ZONE, 
	pin_embarque VARCHAR(4), 
	embarcou_em TIMESTAMP WITHOUT TIME ZONE, 
	metodo_embarque VARCHAR(20), 
	faltou BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_solicitacoes PRIMARY KEY (id), 
	CONSTRAINT uq_solicitacao_carona_passageiro UNIQUE (carona_id, passageiro_id), 
	CONSTRAINT ck_solicitacoes_status CHECK (status IN ('pendente', 'aceita', 'recusada', 'cancelada', 'expirada')), 
	CONSTRAINT ck_solicitacoes_metodo_embarque CHECK (metodo_embarque IN ('pin+gps', 'gps', 'manual')), 
	CONSTRAINT fk_solicitacoes_carona_id_caronas FOREIGN KEY(carona_id) REFERENCES caronas (id) ON DELETE CASCADE, 
	CONSTRAINT fk_solicitacoes_passageiro_id_usuarios FOREIGN KEY(passageiro_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_solicitacoes_carona_id ON solicitacoes (carona_id);
CREATE INDEX ix_solicitacoes_passageiro_id ON solicitacoes (passageiro_id);
CREATE INDEX ix_solicitacoes_status ON solicitacoes (status);

CREATE TABLE avaliacoes (
	id SERIAL NOT NULL, 
	solicitacao_id INTEGER NOT NULL, 
	avaliador_id INTEGER NOT NULL, 
	avaliado_id INTEGER NOT NULL, 
	nota INTEGER NOT NULL, 
	comentario VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_avaliacoes PRIMARY KEY (id), 
	CONSTRAINT ck_avaliacoes_nota CHECK (nota BETWEEN 1 AND 5), 
	CONSTRAINT ck_avaliacoes_nao_autoavaliar CHECK (avaliador_id <> avaliado_id), 
	CONSTRAINT uq_avaliacao_solicitacao_avaliador UNIQUE (solicitacao_id, avaliador_id), 
	CONSTRAINT fk_avaliacoes_solicitacao_id_solicitacoes FOREIGN KEY(solicitacao_id) REFERENCES solicitacoes (id) ON DELETE CASCADE, 
	CONSTRAINT fk_avaliacoes_avaliador_id_usuarios FOREIGN KEY(avaliador_id) REFERENCES usuarios (id), 
	CONSTRAINT fk_avaliacoes_avaliado_id_usuarios FOREIGN KEY(avaliado_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_avaliacoes_avaliado_id ON avaliacoes (avaliado_id);
CREATE INDEX ix_avaliacoes_avaliador_id ON avaliacoes (avaliador_id);
CREATE INDEX ix_avaliacoes_solicitacao_id ON avaliacoes (solicitacao_id);

CREATE TABLE pagamentos (
	id SERIAL NOT NULL, 
	solicitacao_id INTEGER NOT NULL, 
	valor NUMERIC(6, 2) NOT NULL, 
	metodo VARCHAR(20) NOT NULL, 
	pix_copia_cola TEXT, 
	status VARCHAR(20) NOT NULL, 
	pago_em TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_pagamentos PRIMARY KEY (id), 
	CONSTRAINT ck_pagamentos_valor CHECK (valor >= 0), 
	CONSTRAINT ck_pagamentos_metodo CHECK (metodo IN ('pix', 'dinheiro')), 
	CONSTRAINT ck_pagamentos_status CHECK (status IN ('pendente', 'pago', 'cancelado')), 
	CONSTRAINT uq_pagamentos_solicitacao_id UNIQUE (solicitacao_id), 
	CONSTRAINT fk_pagamentos_solicitacao_id_solicitacoes FOREIGN KEY(solicitacao_id) REFERENCES solicitacoes (id) ON DELETE CASCADE
);


CREATE TABLE avaliacao_tags (
	id SERIAL NOT NULL, 
	avaliacao_id INTEGER NOT NULL, 
	tag VARCHAR(40) NOT NULL, 
	CONSTRAINT pk_avaliacao_tags PRIMARY KEY (id), 
	CONSTRAINT uq_avaliacao_tag UNIQUE (avaliacao_id, tag), 
	CONSTRAINT fk_avaliacao_tags_avaliacao_id_avaliacoes FOREIGN KEY(avaliacao_id) REFERENCES avaliacoes (id) ON DELETE CASCADE
);

CREATE INDEX ix_avaliacao_tags_avaliacao_id ON avaliacao_tags (avaliacao_id);
