from __future__ import annotations

import os
from typing import Any


_CONFIGURED = False
_TRUTHY = {"1", "true", "yes", "on"}


def configure_mupdf_logging(fitz_module: Any) -> None:
    """Configure MuPDF diagnostics output once per process.

    By default diagnostics are silenced to avoid noisy stderr output from
    malformed-but-readable PDFs. Set AUDITORIA_PDF_SHOW_MUPDF_MESSAGES=1 to
    keep MuPDF messages visible.
    """

    global _CONFIGURED

    if _CONFIGURED or fitz_module is None:
        return

    show_messages = (
        os.getenv("AUDITORIA_PDF_SHOW_MUPDF_MESSAGES", "0").strip().lower()
        in _TRUTHY
    )
    if show_messages:
        _CONFIGURED = True
        return

    tools = getattr(fitz_module, "TOOLS", None)
    if tools is None:
        _CONFIGURED = True
        return

    try:
        tools.mupdf_display_errors(False)
    except Exception:
        pass

    try:
        tools.mupdf_display_warnings(False)
    except Exception:
        pass

    _CONFIGURED = True
