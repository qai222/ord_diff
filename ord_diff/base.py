from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class OrdLeaf(BaseModel):
    """ base model for an ORD literal field """

    path_list: list[str, int]

    value: str | int | float

    is_implicit: bool | None = None
    """ if this information is explicitly included in the text, only used for IE evaluation """

    @property
    def path_tuple(self):
        return tuple(self.path_list)

    def __eq__(self, other: OrdLeaf):
        return self.path_tuple == other.path_tuple

    def __hash__(self):
        return hash(self.path_tuple)

    class Config:
        validate_assignment = True


class OrdDictionary(BaseModel):
    """ base model for a message dictionary """

    d: dict
    """ the actual dictionary """

    leafs: list[OrdLeaf]

    def get_leaf(self, path_tuple: tuple[str | int, ...]):
        for leaf in self.leafs:
            if path_tuple == leaf.path_tuple:
                return leaf
        raise KeyError


class DiffKind(str, Enum):
    """ what is this comparison about? """

    COMPOUND = "COMPOUND"

    LIST_OF_COMPOUND_LISTS = "LIST_OF_COMPOUND_LISTS"

    LIST_OF_COMPOUNDS = "LIST_OF_COMPOUNDS"

    REACTION_CONDITIONS = "REACTION_CONDITIONS"

    LIST_OF_REACTION_WORKUPS = "LIST_OF_REACTION_WORKUPS"


class OrdDiff(BaseModel):
    """ base model for a comparison """

    kind: DiffKind

    m1: OrdDictionary | list[OrdDictionary] | list[list[OrdDictionary]] | None = None

    m2: OrdDictionary | list[OrdDictionary] | list[list[OrdDictionary]] | None = None

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class FieldChangeType(str, Enum):
    """ used to describe a result entry from `deepdiff` """

    # ref is None, act is not None (addition)
    ADDITION = "ADDITION"

    # ref is not None, act is None (removal)
    REMOVAL = "REMOVAL"

    # ref is not None, act is not None (alteration)
    ALTERATION = "ALTERATION"
