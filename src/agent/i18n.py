"""Internationalization (i18n) backend support [BLK-065].

Provides:
- ``SUPPORTED_LOCALES``: List of supported language codes.
- ``DEFAULT_LOCALE``: Default locale (en).
- ``get_error_message``: Get localized error message.
- ``detect_document_language``: Basic document language detection.
- ``get_locales``: List supported locales for API response.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_LOCALES = ["en", "es", "fr", "de", "pt", "zh"]
DEFAULT_LOCALE = "en"

ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "not_found": "Resource not found",
        "already_exists": "Resource already exists",
        "budget_exceeded": "Budget limit exceeded",
        "unsupported_format": "Unsupported file format",
        "file_too_large": "File size exceeds limit",
        "password_protected": "Password-protected PDFs are not supported",
        "internal_error": "Internal server error",
        "invalid_request": "Invalid request",
    },
    "es": {
        "not_found": "Recurso no encontrado",
        "already_exists": "El recurso ya existe",
        "budget_exceeded": "Límite de presupuesto excedido",
        "unsupported_format": "Formato de archivo no compatible",
        "file_too_large": "El tamaño del archivo excede el límite",
        "password_protected": "Los PDF protegidos con contraseña no son compatibles",
        "internal_error": "Error interno del servidor",
        "invalid_request": "Solicitud no válida",
    },
    "fr": {
        "not_found": "Ressource introuvable",
        "already_exists": "La ressource existe déjà",
        "budget_exceeded": "Limite de budget dépassée",
        "unsupported_format": "Format de fichier non pris en charge",
        "file_too_large": "La taille du fichier dépasse la limite",
        "password_protected": "Les PDF protégés par mot de passe ne sont pas pris en charge",
        "internal_error": "Erreur interne du serveur",
        "invalid_request": "Demande invalide",
    },
    "de": {
        "not_found": "Ressource nicht gefunden",
        "already_exists": "Ressource existiert bereits",
        "budget_exceeded": "Budgetlimit überschritten",
        "unsupported_format": "Nicht unterstütztes Dateiformat",
        "file_too_large": "Dateigröße überschreitet Limit",
        "password_protected": "Passwortgeschützte PDFs werden nicht unterstützt",
        "internal_error": "Interner Serverfehler",
        "invalid_request": "Ungültige Anfrage",
    },
    "pt": {
        "not_found": "Recurso não encontrado",
        "already_exists": "Recurso já existe",
        "budget_exceeded": "Limite de orçamento excedido",
        "unsupported_format": "Formato de arquivo não suportado",
        "file_too_large": "O tamanho do arquivo excede o limite",
        "password_protected": "PDFs protegidos por senha não são suportados",
        "internal_error": "Erro interno do servidor",
        "invalid_request": "Solicitação inválida",
    },
    "zh": {
        "not_found": "未找到资源",
        "already_exists": "资源已存在",
        "budget_exceeded": "预算限制已超出",
        "unsupported_format": "不支持的文件格式",
        "file_too_large": "文件大小超过限制",
        "password_protected": "不支持受密码保护的PDF",
        "internal_error": "内部服务器错误",
        "invalid_request": "无效请求",
    },
}


@dataclass
class LocaleInfo:
    """Information about a supported locale [BLK-065]."""

    code: str
    name: str
    native_name: str


LOCALE_INFO: dict[str, LocaleInfo] = {
    "en": LocaleInfo("en", "English", "English"),
    "es": LocaleInfo("es", "Spanish", "Español"),
    "fr": LocaleInfo("fr", "French", "Français"),
    "de": LocaleInfo("de", "German", "Deutsch"),
    "pt": LocaleInfo("pt", "Portuguese", "Português"),
    "zh": LocaleInfo("zh", "Chinese (Simplified)", "简体中文"),
}


def parse_accept_language(header: str | None) -> str:
    """Parse Accept-Language header and return best matching locale [BLK-065].

    Args:
        header: Accept-Language header value (e.g. "es-ES,es;q=0.9,en;q=0.8").

    Returns:
        Best matching locale code (e.g. "es"), or DEFAULT_LOCALE.
    """
    if not header:
        return DEFAULT_LOCALE

    # Parse languages with quality values
    languages: list[tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if ";q=" in part:
            lang, q = part.split(";q=", 1)
            try:
                quality = float(q)
            except ValueError:
                quality = 1.0
        else:
            lang = part
            quality = 1.0
        languages.append((lang.strip().lower(), quality))

    # Sort by quality (descending)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Find first matching locale
    for lang, _ in languages:
        # Exact match (e.g. "es")
        if lang in SUPPORTED_LOCALES:
            return lang
        # Prefix match (e.g. "es-es" → "es")
        prefix = lang.split("-")[0]
        if prefix in SUPPORTED_LOCALES:
            return prefix

    return DEFAULT_LOCALE


def get_error_message(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """Get a localized error message [BLK-065].

    Args:
        key: Error message key (e.g. "not_found", "budget_exceeded").
        locale: Locale code (e.g. "en", "es").

    Returns:
        Localized error message, or English fallback.
    """
    messages = ERROR_MESSAGES.get(locale, ERROR_MESSAGES[DEFAULT_LOCALE])
    return messages.get(key, ERROR_MESSAGES[DEFAULT_LOCALE].get(key, key))


def get_locales() -> list[dict[str, str]]:
    """Get list of supported locales for API response [BLK-065].

    Returns:
        List of locale dicts with code, name, and native_name.
    """
    return [
        {"code": info.code, "name": info.name, "native_name": info.native_name}
        for info in LOCALE_INFO.values()
    ]


def detect_document_language(text_sample: str) -> str:
    """Basic document language detection from text sample [BLK-065].

    Uses simple Unicode range heuristics. For production use, integrate
    a proper language detection library (e.g., langdetect, fasttext).

    Args:
        text_sample: Sample text from the document (first page OCR).

    Returns:
        Detected language code (e.g. "en", "zh").
    """
    if not text_sample:
        return DEFAULT_LOCALE

    # Check for CJK characters (Chinese, Japanese, Korean)
    cjk_count = sum(
        1 for c in text_sample
        if "\u4e00" <= c <= "\u9fff"  # CJK Unified Ideographs
    )
    if cjk_count > len(text_sample) * 0.3:
        return "zh"

    # Default to English for Latin script
    # (Proper detection requires more sophisticated NLP)
    return "en"
