"""Registro anônimo das interações, para os testes com usuários.

Grava em registros/interacoes.csv (fora do git): data e hora, um código de sessão aleatório, o evento,
a pergunta, o tipo de resposta e a avaliação 👍/👎. Não grava nome, e-mail, IP nem nada que identifique a pessoa.

Atenção: no Streamlit Community Cloud o arquivo some quando o app reinicia ou recebe um commit novo.
Baixe o registro (aba Sobre > Área da equipe) ao fim de cada sessão de testes.
"""
import csv
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ARQUIVO = Path(__file__).parent / "registros" / "interacoes.csv"
CAMPOS = ["data_hora", "sessao", "evento", "pergunta", "tipo_resposta", "avaliacao"]
_trava = threading.Lock()


def registrar(sessao, evento, pergunta="", tipo_resposta="", avaliacao="", arquivo=ARQUIVO):
    """Acrescenta uma linha ao registro. Nunca derruba o app: se der erro ao gravar, ignora."""
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        linha = {
            "data_hora": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S"),
            "sessao": sessao, "evento": evento, "pergunta": (pergunta or "")[:1000],
            "tipo_resposta": tipo_resposta, "avaliacao": avaliacao,
        }
        with _trava:
            novo = not arquivo.exists()
            with arquivo.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS)
                if novo:
                    w.writeheader()
                w.writerow(linha)
    except Exception:
        pass


def conteudo(arquivo=ARQUIVO):
    """Texto do CSV (ou só o cabeçalho, se ainda não houver registros)."""
    if arquivo.exists():
        return arquivo.read_text(encoding="utf-8")
    return ",".join(CAMPOS) + "\n"


def total_linhas(arquivo=ARQUIVO):
    return max(0, len(conteudo(arquivo).splitlines()) - 1)
