from __future__ import annotations

from abc import ABC
from enum import Enum
from typing import Any
from pydantic import BaseModel


class DiffReportKind(str, Enum):
    """ what is this comparison about? """

    LIST_OF_COMPOUND_LISTS = "LIST_OF_COMPOUND_LISTS"

    LIST_OF_COMPOUNDS = "LIST_OF_COMPOUNDS"

    REACTION_CONDITIONS = "REACTION_CONDITIONS"

    LIST_OF_REACTION_WORKUPS = "LIST_OF_REACTION_WORKUPS"


class DiffReport(ABC, BaseModel):
    """ base model for a formatted report """

    kind: DiffReportKind

    reference: dict | list[dict] | list[list[dict]] | None = None

    actual: dict | list[dict] | list[list[dict]] | None = None

    class Config:
        validate_assignment = True


class OrdField(BaseModel):
    """ base model for an ORD field """

    path: str

    path_list: list[str, int]

    value: Any


class FieldChangeType(str, Enum):
    """ used to describe a result entry from `deepdiff` """

    # ref is None, act is not None (addition)
    ADDITION = "ADDITION"

    # ref is not None, act is None (removal)
    REMOVAL = "REMOVAL"

    # ref is not None, act is not None (alteration)
    ALTERATION = "ALTERATION"


