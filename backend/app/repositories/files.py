from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Union

import asyncpg
from typing_extensions import TypedDict

# ─── connection type alias ────────────────────────────────────────────────────
Conn = Union[asyncpg.Connection, asyncpg.Pool]


# ─── typed return type ────────────────────────────────────────────────────────


class FileMeta(TypedDict):
    """Typed representation of a single ``files`` table row."""

    file_id: uuid.UUID
    owner_id: uuid.UUID
    # Storage location
    bucket: str
    folder: str
    file_key: str
    # File identity
    original_name: str
    current_name: str
    content_type: Optional[str]
    size_bytes: int
    sha256_hex: str
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]


# ─── internal helpers ─────────────────────────────────────────────────────────


def _to_file_meta(record: asyncpg.Record) -> FileMeta:
    return FileMeta(  # type: ignore[call-arg]
        file_id=record["file_id"],
        owner_id=record["owner_id"],
        bucket=record["bucket"],
        folder=record["folder"],
        file_key=record["file_key"],
        original_name=record["original_name"],
        current_name=record["current_name"],
        content_type=record["content_type"],
        size_bytes=record["size_bytes"],
        sha256_hex=record["sha256_hex"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


def _to_file_meta_list(records: list[asyncpg.Record]) -> list[FileMeta]:
    return [_to_file_meta(r) for r in records]


# ─── CREATE ───────────────────────────────────────────────────────────────────


async def create_file(
    *,
    conn: Conn,
    file_id: uuid.UUID,
    owner_id: uuid.UUID,
    bucket: str,
    folder: str,
    file_key: str,
    original_name: str,
    current_name: str,
    content_type: Optional[str],
    size_bytes: int,
    sha256_hex: str,
) -> FileMeta:
    """
    Insert a new file row and return the complete persisted record.

    Raises
    ------
    asyncpg.UniqueViolationError
        If ``file_key`` already exists.
    asyncpg.ForeignKeyViolationError
        If ``owner_id`` does not reference a valid user.
    asyncpg.CheckViolationError
        If any DB constraint is violated (size, hash format, folder, names).
    """
    row = await conn.fetchrow(
        """
        INSERT INTO files (
            file_id, owner_id,
            bucket, folder, file_key,
            original_name, current_name,
            content_type, size_bytes, sha256_hex
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        file_id,
        owner_id,
        bucket,
        folder,
        file_key,
        original_name,
        current_name,
        content_type,
        size_bytes,
        sha256_hex,
    )
    return _to_file_meta(row)  # type: ignore


# ─── READ ─────────────────────────────────────────────────────────────────────


async def get_file_by_id(
    conn: Conn,
    file_id: uuid.UUID,
) -> Optional[FileMeta]:
    """Return the ``FileMeta`` for *file_id*, or ``None`` if not found."""
    row = await conn.fetchrow(
        "SELECT * FROM files WHERE file_id = $1",
        file_id,
    )
    return _to_file_meta(row) if row else None


async def get_file_by_key(
    conn: Conn,
    file_key: str,
) -> Optional[FileMeta]:
    """Return the ``FileMeta`` for the unique *file_key*, or ``None``."""
    row = await conn.fetchrow(
        "SELECT * FROM files WHERE file_key = $1",
        file_key,
    )
    return _to_file_meta(row) if row else None


async def list_files_by_owner(
    conn: Conn,
    owner_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "created_at",
    ascending: bool = False,
) -> list[FileMeta]:
    """
    Return a paginated list of files belonging to *owner_id*.

    Parameters
    ----------
    order_by:
        Column name to sort by.  Accepted values:
        ``created_at`` (default), ``current_name``, ``size_bytes``, ``updated_at``.
    ascending:
        Sort direction; ``False`` → most-recent first.

    Raises
    ------
    ValueError
        If *order_by* is not an allowed column name.
    """
    _ALLOWED_ORDER = {"created_at", "current_name", "size_bytes", "updated_at"}
    if order_by not in _ALLOWED_ORDER:
        raise ValueError(f"order_by must be one of {_ALLOWED_ORDER!r}")

    direction = "ASC" if ascending else "DESC"
    rows = await conn.fetch(
        f"""
        SELECT * FROM files
        WHERE owner_id = $1
        ORDER BY {order_by} {direction}
        LIMIT $2 OFFSET $3
        """,
        owner_id,
        limit,
        offset,
    )
    return _to_file_meta_list(rows)


async def list_files_by_folder(
    conn: Conn,
    owner_id: uuid.UUID,
    folder: str,
    *,
    recursive: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[FileMeta]:
    """
    Return files in *folder* for the given *owner_id*.

    Parameters
    ----------
    recursive:
        If ``True``, match all sub-folders via a ``LIKE`` prefix query
        (e.g. ``/docs`` also returns ``/docs/reports``).
        If ``False``, only exact folder matches are returned.
    """
    if recursive:
        # Ensure prefix ends with / so /docs does not match /docs2
        prefix = folder.rstrip("/") + "/%"
        rows = await conn.fetch(
            """
            SELECT * FROM files
            WHERE owner_id = $1
              AND (folder = $2 OR folder LIKE $3)
            ORDER BY folder, current_name
            LIMIT $4 OFFSET $5
            """,
            owner_id,
            folder,
            prefix,
            limit,
            offset,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT * FROM files
            WHERE owner_id = $1 AND folder = $2
            ORDER BY current_name
            LIMIT $3 OFFSET $4
            """,
            owner_id,
            folder,
            limit,
            offset,
        )
    return _to_file_meta_list(rows)


async def get_file_by_sha256(
    conn: Conn,
    sha256_hex: str,
    *,
    owner_id: Optional[uuid.UUID] = None,
) -> Optional[FileMeta]:
    """
    Look up a file by its SHA-256 hash.

    If *owner_id* is supplied the lookup is scoped to that owner
    (useful for per-user deduplication).  Returns the **first** match.
    """
    if owner_id is not None:
        row = await conn.fetchrow(
            """
            SELECT * FROM files
            WHERE sha256_hex = $1 AND owner_id = $2
            LIMIT 1
            """,
            sha256_hex,
            owner_id,
        )
    else:
        row = await conn.fetchrow(
            "SELECT * FROM files WHERE sha256_hex = $1 LIMIT 1",
            sha256_hex,
        )
    return _to_file_meta(row) if row else None


# ─── UPDATE ───────────────────────────────────────────────────────────────────


async def rename_file(
    conn: Conn,
    file_id: uuid.UUID,
    new_name: str,
) -> Optional[FileMeta]:
    """
    Update *current_name* for the file.

    Returns the updated ``FileMeta``, or ``None`` if *file_id* was not found.

    Raises
    ------
    asyncpg.CheckViolationError
        If *new_name* is blank (DB constraint ``chk_files_names_not_blank``).
    """
    row = await conn.fetchrow(
        """
        UPDATE files
        SET current_name = $2
        WHERE file_id = $1
        RETURNING *
        """,
        file_id,
        new_name,
    )
    return _to_file_meta(row) if row else None


async def move_file(
    conn: Conn,
    file_id: uuid.UUID,
    *,
    bucket: Optional[str] = None,
    folder: Optional[str] = None,
    file_key: Optional[str] = None,
) -> Optional[FileMeta]:
    """
    Relocate a file by updating its *bucket*, *folder*, and/or *file_key*.

    Only supplied (non-``None``) fields are changed.  Returns the updated
    ``FileMeta``, or ``None`` if *file_id* was not found.

    Raises
    ------
    asyncpg.UniqueViolationError
        If *file_key* collides with an existing row.
    asyncpg.CheckViolationError
        If *folder* does not start with ``/``.
    """
    updates: list[str] = []
    params: list[object] = [file_id]

    if bucket is not None:
        params.append(bucket)
        updates.append(f"bucket = ${len(params)}")
    if folder is not None:
        params.append(folder)
        updates.append(f"folder = ${len(params)}")
    if file_key is not None:
        params.append(file_key)
        updates.append(f"file_key = ${len(params)}")

    if not updates:
        # Nothing to do – return the current row unchanged
        return await get_file_by_id(conn, file_id)

    set_clause = ", ".join(updates)
    row = await conn.fetchrow(
        f"""
        UPDATE files
        SET {set_clause}
        WHERE file_id = $1
        RETURNING *
        """,
        *params,
    )
    return _to_file_meta(row) if row else None


# ─── DELETE ───────────────────────────────────────────────────────────────────


async def delete_file(
    conn: Conn,
    file_id: uuid.UUID,
) -> bool:
    """
    Delete the file row identified by *file_id*.

    Returns ``True`` if a row was deleted, ``False`` if not found.
    """
    result: str = await conn.execute(
        "DELETE FROM files WHERE file_id = $1",
        file_id,
    )
    # asyncpg returns e.g. "DELETE 1" or "DELETE 0"
    return result.endswith(" 1")


# ─── AGGREGATE / UTILITY ──────────────────────────────────────────────────────


async def count_files_by_owner(
    conn: Conn,
    owner_id: uuid.UUID,
) -> int:
    """Return the total number of files owned by *owner_id*."""
    return await conn.fetchval(
        "SELECT COUNT(*) FROM files WHERE owner_id = $1",
        owner_id,
    )  # type: ignore


async def total_bytes_by_owner(
    conn: Conn,
    owner_id: uuid.UUID,
) -> int:
    """Return the sum of *size_bytes* for all files owned by *owner_id*."""
    value = await conn.fetchval(
        "SELECT COALESCE(SUM(size_bytes), 0) FROM files WHERE owner_id = $1",
        owner_id,
    )
    return int(value)  # type: ignore


async def file_exists(
    conn: Conn,
    file_id: uuid.UUID,
) -> bool:
    """Cheap existence check – avoids fetching the full row."""
    value = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM files WHERE file_id = $1)",
        file_id,
    )
    return bool(value)
