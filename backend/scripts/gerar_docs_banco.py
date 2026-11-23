"""
Gera a documentacao do banco a partir dos models (db.metadata):

  docs/banco_de_dados.md       diagrama Mermaid + dicionario de dados (o texto antes de
                               "## Diagrama fisico" e mantido; o resto e regerado)
  docs/banco.dbml              para colar em https://dbdiagram.io (diagrama visual)
  docs/schema_postgresql.sql   CREATE TABLE para PostgreSQL (producao)

Uso (dentro de backend/):  python scripts/gerar_docs_banco.py   ou   invoke docsdb
"""
import json
import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from caronauvv import create_app
from caronauvv.config import TestConfig
from caronauvv.ext.db import db

DOCS = Path(__file__).resolve().parents[2] / "docs"
MARCADOR = "## Diagrama físico"

MODULOS = {
    "auth": ["usuarios", "veiculos", "contatos_confianca", "fotos_perfil", "documentos", "codigos_reserva"],
    "caronas": ["caronas", "solicitacoes", "posicoes_gps", "pedidos_carona"],
    "avaliacoes": ["avaliacoes", "avaliacao_tags", "pagamentos"],
    "notificacoes": ["notificacoes"],
    "seguranca": ["alertas", "links_compartilhados", "denuncias"],
    "admin": ["buscas", "configuracoes"],
}
ORDEM = [t for tabelas in MODULOS.values() for t in tabelas]


# ==========================================================
# LEITURA DO METADATA
# ==========================================================
def tipo(col) -> str:
    t = col.type
    nome = type(t).__name__.upper()
    if getattr(t, "length", None):
        return f"{nome}({t.length})"
    if nome == "NUMERIC":
        return f"NUMERIC({t.precision},{t.scale})"
    return nome


def padrao(col) -> str | None:
    if col.default is not None and not callable(col.default.arg):
        return repr(col.default.arg).replace("'", '"')
    if col.server_default is not None or col.default is not None:
        return "agora"
    return None


def descrever(tabelas) -> list[dict]:
    """Estrutura neutra usada por todos os formatos de saida."""
    saida = []
    for nome in ORDEM:
        t = tabelas[nome]
        colunas = []
        for col in t.columns:
            fks = [
                {"tabela": fk.column.table.name, "coluna": fk.column.name, "ondelete": fk.ondelete}
                for fk in col.foreign_keys
            ]
            colunas.append({
                "nome": col.name, "tipo": tipo(col), "nulo": col.nullable,
                "pk": col.primary_key, "unique": bool(col.unique),
                "indice": bool(col.index) and not col.unique, "fks": fks, "padrao": padrao(col),
            })
        regras = []
        for c in sorted(t.constraints, key=lambda c: str(c.name)):
            if isinstance(c, CheckConstraint):
                regras.append({"tipo": "CHECK", "nome": c.name, "def": str(c.sqltext)})
            elif isinstance(c, UniqueConstraint) and len(c.columns) > 1:
                regras.append({"tipo": "UNIQUE", "nome": c.name, "def": ", ".join(x.name for x in c.columns)})
        for i in sorted(t.indexes, key=lambda i: i.name):
            if len(i.columns) > 1:
                regras.append({"tipo": "ÍNDICE", "nome": i.name, "def": ", ".join(x.name for x in i.columns)})
        modulo = next(m for m, ts in MODULOS.items() if nome in ts)
        saida.append({"nome": nome, "modulo": modulo, "colunas": colunas, "regras": regras})
    return saida


# ==========================================================
# MARKDOWN (Mermaid + dicionario)
# ==========================================================
def markdown(esquema) -> str:
    out = [MARCADOR, "", "```mermaid", "erDiagram"]
    for t in esquema:
        for c in t["colunas"]:
            for fk in c["fks"]:
                um = "|o" if c["nulo"] else "||"
                muitos = "o|" if c["unique"] else "o{"
                out.append(f'    {fk["tabela"]} {um}--{muitos} {t["nome"]} : "{c["nome"]}"')
    for t in esquema:
        out.append(f"    {t['nome']} {{")
        for c in t["colunas"]:
            chaves = [k for k, ok in (("PK", c["pk"]), ("FK", c["fks"]), ("UK", c["unique"])) if ok]
            out.append(f"        {c['tipo'].split('(')[0].lower()} {c['nome']}{' ' + ','.join(chaves) if chaves else ''}")
        out.append("    }")
    out += ["```", "", "## Dicionário de dados", ""]

    for t in esquema:
        out += [f"### `{t['nome']}` (módulo `{t['modulo']}`)", "",
                "| Coluna | Tipo | Nulo | Chave | Padrão |", "|---|---|---|---|---|"]
        for c in t["colunas"]:
            chaves = ["PK"] if c["pk"] else []
            for fk in c["fks"]:
                regra = f", ON DELETE {fk['ondelete']}" if fk["ondelete"] else ""
                chaves.append(f"FK → `{fk['tabela']}.{fk['coluna']}`{regra}")
            if c["unique"]:
                chaves.append("UNIQUE")
            if c["indice"]:
                chaves.append("índice")
            valor = f"`{c['padrao']}`" if c["padrao"] and c["padrao"] != "agora" else (c["padrao"] or "")
            out.append(f"| `{c['nome']}` | {c['tipo']} | {'sim' if c['nulo'] else 'não'} | {'; '.join(chaves)} | {valor} |")
        if t["regras"]:
            out += ["", "**Restrições:**", ""]
            out += [f"- {r['tipo']} `{r['nome']}`: `{r['def']}`" for r in t["regras"]]
        out.append("")
    return "\n".join(out)


# ==========================================================
# DBML (https://dbdiagram.io)
# ==========================================================
def dbml(esquema) -> str:
    tipos_dbml = {"STRING": "varchar", "INTEGER": "integer", "FLOAT": "float", "BOOLEAN": "boolean",
                  "DATETIME": "timestamp", "DATE": "date", "TIME": "time", "TEXT": "text", "NUMERIC": "numeric"}
    out = ["// CaronaUVV - gerado por backend/scripts/gerar_docs_banco.py", "// Cole em https://dbdiagram.io", ""]
    refs = []
    for t in esquema:
        out.append(f"Table {t['nome']} {{")
        for c in t["colunas"]:
            base, _, resto = c["tipo"].partition("(")
            tipo_dbml = tipos_dbml.get(base, base.lower()) + (f"({resto}" if resto else "")
            attrs = []
            if c["pk"]:
                attrs.append("pk")
            if c["unique"]:
                attrs.append("unique")
            if not c["nulo"] and not c["pk"]:
                attrs.append("not null")
            if c["padrao"] == "agora":
                attrs.append("default: `now()`")
            elif c["padrao"] in ("True", "False"):
                attrs.append(f"default: {c['padrao'].lower()}")
            elif c["padrao"]:
                attrs.append(f"default: {c['padrao']}".replace('"', "'"))
            out.append(f"  {c['nome']} {tipo_dbml}{' [' + ', '.join(attrs) + ']' if attrs else ''}")
            for fk in c["fks"]:
                seta = "-" if c["unique"] else ">"
                regra = f" [delete: {fk['ondelete'].lower()}]" if fk["ondelete"] else ""
                refs.append(f"Ref: {t['nome']}.{c['nome']} {seta} {fk['tabela']}.{fk['coluna']}{regra}")
        compostos = [r for r in t["regras"] if r["tipo"] in ("UNIQUE", "ÍNDICE")]
        if compostos:
            out.append("  indexes {")
            for r in compostos:
                unico = "unique, " if r["tipo"] == "UNIQUE" else ""
                out.append(f"    ({r['def']}) [{unico}name: '{r['nome']}']")
            out.append("  }")
        checks = [r for r in t["regras"] if r["tipo"] == "CHECK"]
        if checks:
            texto = "\\n".join(f"CHECK {r['def']}" for r in checks).replace("'", "\\'")
            out.append(f"  Note: '{texto}'")
        out += ["}", ""]
    out += refs + [""]
    for modulo, tabelas in MODULOS.items():
        out += [f"TableGroup {modulo} {{", *[f"  {t}" for t in tabelas], "}", ""]
    return "\n".join(out)


# ==========================================================
# SQL PostgreSQL
# ==========================================================
def sql_postgresql() -> str:
    dialeto = postgresql.dialect()
    out = ["-- CaronaUVV - esquema para PostgreSQL (gerado de db.metadata).",
           "-- Em producao o normal e rodar 'flask db upgrade'; este arquivo serve de referencia.", ""]
    for t in db.metadata.sorted_tables:
        out.append(str(CreateTable(t).compile(dialect=dialeto)).strip() + ";\n")
        for i in sorted(t.indexes, key=lambda i: i.name):
            out.append(str(CreateIndex(i).compile(dialect=dialeto)).strip() + ";")
        out.append("")
    return "\n".join(out)


def main() -> None:
    app = create_app(TestConfig)
    with app.app_context():
        tabelas = db.metadata.tables
        assert sorted(ORDEM) == sorted(tabelas), f"Atualize MODULOS: {set(tabelas) ^ set(ORDEM)}"
        esquema = descrever(tabelas)

        md = DOCS / "banco_de_dados.md"
        cabecalho = md.read_text(encoding="utf-8").split(MARCADOR)[0] if md.exists() else "# Banco de dados\n\n"
        md.write_text(cabecalho + markdown(esquema), encoding="utf-8")
        (DOCS / "banco.dbml").write_text(dbml(esquema), encoding="utf-8")
        (DOCS / "schema_postgresql.sql").write_text(sql_postgresql(), encoding="utf-8")

        if "--json" in sys.argv:  # usado para montar a pagina interativa do diagrama
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(esquema, ensure_ascii=False))
        else:
            print(f"Gerados em {DOCS}: banco_de_dados.md, banco.dbml, schema_postgresql.sql")


if __name__ == "__main__":
    main()
