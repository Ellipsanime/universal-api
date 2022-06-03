from datetime import datetime
from itertools import groupby
from typing import List, Dict, Any

from box import Box

from app.record.query import VersionChangeQuery
from app.util import db
from app.util.data import boxify

_SQL_ALL_FILES = "SELECT * FROM client_file"
_SQL_ALL_PROJECT_SPLITS = "SELECT * FROM client_project_split"
_SQL_ALL_VERSION_CHANGES = "SELECT * FROM client_version_change"
_SQL_ALL_PROJECTS = "SELECT * FROM client_project"


def _get_version_change_view_sql(query: VersionChangeQuery) -> str:
    if query.value is None:
        return f"""
            SELECT * FROM client_version_file_view
            WHERE project_name = ? 
            ORDER BY {query.sort_field} {query.sort_order}
            LIMIT ? OFFSET ?
        """

    return f"""
        SELECT * FROM client_version_file_view
        WHERE project_name = ? AND {query.field} = ? 
        ORDER BY {query.sort_field} {query.sort_order}
        LIMIT ? OFFSET ?
    """


async def fetch_version_changes_per_project(
    query: VersionChangeQuery,
) -> List[Box]:
    params = tuple(
        x
        for x in [
            query.identifier,
            query.value,
            query.limit,
            query.skip,
        ]
        if x is not None
    )
    raw_changes = await db.fetch_all(
        _get_version_change_view_sql(query),
        params,
    )
    return [
        _map_group(list(g))
        for _, g in groupby(raw_changes, lambda x: x.version_id)
    ]


async def fetch_project_splits() -> List[Box]:
    raw_projects = await db.fetch_all(_SQL_ALL_PROJECT_SPLITS)
    return [boxify(x) for x in raw_projects]


async def fetch_version_changes() -> List[Box]:
    version_change = await db.fetch_all(_SQL_ALL_VERSION_CHANGES)
    return [_convert_datetime(x) for x in version_change]


async def fetch_files() -> List[Box]:
    files = await db.fetch_all(_SQL_ALL_FILES)
    return [_convert_datetime(x) for x in files]


async def fetch_projects() -> List[Box]:
    projects = await db.fetch_all(_SQL_ALL_PROJECTS)
    return [boxify(x) for x in projects]


def _convert_datetime(entity: Box | Dict, field: Any = "datetime") -> Box:
    if field not in entity:
        return entity
    return boxify({**entity, field: datetime.fromtimestamp(entity[field])})


def _get_subdict(entity: Dict[str, Any], key: str) -> Dict[str, Any]:
    return {
        k.replace(key, ""): v for k, v in entity.items() if k.startswith(key)
    }


def _map_group(group: List[Box]) -> Box:
    version = _convert_datetime(_get_subdict(group[0], "version_"))
    project = _get_subdict(group[0], "project_")
    linked_files = [
        _convert_datetime(_get_subdict(x, "file_")) for x in group if x.file_id
    ]
    return boxify(
        {
            **version,
            "project": project,
            "linked_files": linked_files,
        }
    )
