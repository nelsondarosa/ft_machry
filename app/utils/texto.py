import re
import unicodedata


def normalizar_nome(texto: str) -> str:
    """Chave de comparação de nomes: sem acentos, minúsculas e espaços simples."""
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).strip().lower()


def padronizar_nome(texto: str) -> str:
    """Remove espaços excedentes e usa uma grafia consistente no catálogo."""
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    return texto[:1].upper() + texto[1:]
