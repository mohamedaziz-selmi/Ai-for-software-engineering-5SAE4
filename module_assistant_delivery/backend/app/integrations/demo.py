"""[DEMO] Stand-ins for platform identity and project data.

The platform has no authentication, users, projects or membership (docs/AUDIT.md). These adapters
serve synthetic records from data/seed/projects.json. Selecting a demo identity is NOT
authentication: any caller can claim any identity. Replace this module with real adapters when the
platform provides them; endpoint code only depends on the methods below.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEMO_NOTICE = "Demo identity selection, not authentication. Any visitor can choose any identity."


@dataclass(frozen=True)
class DemoUser:
    id: str
    display_name: str
    role: str


@dataclass(frozen=True)
class DemoProject:
    id: str
    name: str
    members: dict[str, str] = field(default_factory=dict)  # user_id -> project role
    documents: tuple[str, ...] = ()
    milestones: tuple[tuple[str, str], ...] = ()  # (id, name), [DEMO]


class DemoDirectory:
    """Identity + project directory backed by a synthetic seed file."""

    mode = "demo_adapter"
    authentication = False

    def __init__(self, seed_file: Path) -> None:
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        self._users = {u["id"]: DemoUser(u["id"], u["display_name"], u["role"]) for u in data["users"]}
        self._projects = {
            p["id"]: DemoProject(p["id"], p["name"], dict(p["members"]), tuple(p.get("documents", [])),
                                 tuple((m["id"], m["name"]) for m in p.get("milestones", [])))
            for p in data["projects"]
        }

    def users(self) -> list[DemoUser]:
        return list(self._users.values())

    def get_user(self, user_id: str | None) -> DemoUser | None:
        return self._users.get(user_id or "")

    def get_project(self, project_id: str) -> DemoProject | None:
        return self._projects.get(project_id)

    def projects_for(self, user_id: str) -> list[DemoProject]:
        return [p for p in self._projects.values() if user_id in p.members]

    def all_projects(self) -> list[DemoProject]:
        return list(self._projects.values())

    def project_role(self, user_id: str, project_id: str) -> str | None:
        project = self._projects.get(project_id)
        return project.members.get(user_id) if project else None
