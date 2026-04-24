"""SQLite-backed storage for per-user settings, article cache, filters,
favorites, and operation audit log.

Public API:
    - db.connect() / db.close() — lifecycle
    - user_settings.{get, set, get_all, migrate_from_json}
    - article_cache.{lookup, store, purge_expired}
    - filters.{list, add, remove, apply}
    - favorites.{add, remove, list, exists}
    - op_log.{start, complete, fail}
"""
