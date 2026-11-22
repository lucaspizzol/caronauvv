"""
Ponto de entrada da API na Vercel (funcao serverless Python).
A Vercel chama o objeto WSGI "app"; todo /api/* e redirecionado para ca
(ver vercel.json) e o Flask recebe o caminho original da requisicao.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from caronauvv import create_app  # noqa: E402

app = create_app()
