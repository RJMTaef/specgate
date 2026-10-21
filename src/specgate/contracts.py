"""Structured acceptance contract alongside spec-kit's canonical Markdown artifacts."""

import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SmokeCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^AC-\d{3}$")
    method: Literal["GET", "POST"]
    path: Literal["/health", "/screen"]
    body: dict[str, Any] | None = None
    status: int = Field(ge=100, le=599)
    expected: dict[str, Any] = Field(min_length=1)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str = Field(pattern=r"^\d{3}-[a-z0-9-]+$")
    checks: list[SmokeCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [check.id for check in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("Acceptance IDs must be unique")
        return self


def feature_path(root: Path, feature: str) -> Path:
    if not re.fullmatch(r"\d{3}-[a-z0-9-]+", feature):
        raise ValueError("Invalid feature identifier")
    path = (root / "specs" / feature).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Feature escapes repository")
    return path


def load_contract(path: Path) -> Contract:
    return Contract.model_validate(yaml.safe_load(path.read_text()))
