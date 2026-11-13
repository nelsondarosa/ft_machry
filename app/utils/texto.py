import re
import unicodedata


def normalizar_nome(texto: str) -> str:
    """Chave de comparação de nomes: sem acentos, minúsculas e espaços simples."""
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).strip().lower()
