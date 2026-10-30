"""Peran Analyzer: satu definisi bersama dengan modul Worth to Buy Analyzer.

Grup "Analyzer", pemeriksaan role, dan decorator-nya didefinisikan di
worth_to_buy_analyzer/roles.py. Modul ini hanya memakai ulang supaya aturan
aksesnya identik di seluruh proyek:

- Ruang Analyzer: akun di grup Analyzer atau superuser (`analyzer_required`).
- Halaman pribadi user (Numbers, daftar, form): akun Analyzer ditolak 403,
  sedangkan user biasa dan superuser boleh (`user_pages_only`).
"""
from worth_to_buy_analyzer.roles import (
    ANALYZER_GROUP,
    analyzer_required,
    is_analyzer,
    purchase_user_required as user_pages_only,
)

__all__ = ["ANALYZER_GROUP", "analyzer_required", "is_analyzer", "user_pages_only", "can_open_analyzer"]


def can_open_analyzer(user):
    """Boleh membuka ruang Analyzer (dipakai untuk menampilkan tautan)."""
    return user.is_authenticated and (user.is_superuser or is_analyzer(user))
