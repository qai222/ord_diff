from __future__ import annotations

from abc import ABC
from enum import Enum

from deepdiff import DeepDiff
from google.protobuf import json_format
from pydantic import BaseModel

from .utils import parse_deepdiff, flatten


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

    @classmethod
    def from_dict(cls, compound_dict: dict):
        leafs = []
        for path_tuple, value in flatten(compound_dict).items():
            leaf = OrdLeaf(path_list=list(path_tuple), value=value, is_implicit=None)
            leafs.append(leaf)
        return cls(leafs=leafs, d=compound_dict)


class OrdDiff(ABC, BaseModel):
    """ base model for a comparison """

    m1: OrdDictionary

    m2: OrdDictionary

    delta_leafs: dict[DeltaType, list[OrdLeaf]]
    # addition leafs come from m2
    # removal leafs come from m1
    # for alteration only look at m1 leafs

    delta_paths: dict[DeltaType, list[tuple[str | int, ...]]]
    # addition paths come from m2
    # removal paths come from m1
    # for alteration only look at m1 paths

    deep_distance: float

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

    @classmethod
    def from_pair(cls, m1: OrdDictionary, m2: OrdDictionary):
        dd = DeepDiff(
            m1.d, m2.d,
            ignore_order=True, verbose_level=2, view='tree', get_deep_distance=True
        )

        (
            deep_distance,
            paths_added, paths_removed, paths_altered_1, paths_altered_2,
            leafs_added, leafs_removed, leafs_altered_1, leafs_altered_2,
        ) = parse_deepdiff(dd)

        delta_leafs = {
            DeltaType.ADDITION: leafs_added,
            DeltaType.REMOVAL: leafs_removed,
            DeltaType.ALTERATION: leafs_altered_1
        }

        delta_paths = {
            DeltaType.ADDITION: paths_added,
            DeltaType.REMOVAL: paths_removed,
            DeltaType.ALTERATION: paths_altered_1
        }

        return cls(
            m1=m1,
            m2=m2,
            deep_distance=deep_distance,
            delta_paths=delta_paths,
            delta_leafs=delta_leafs,
        )

    @classmethod
    def from_ord(cls, m1, m2, ):
        d1 = json_format.MessageToDict(m1)
        d2 = json_format.MessageToDict(m2)
        return OrdDiff.from_pair(
            m1=OrdDictionary.from_dict(d1),
            m2=OrdDictionary.from_dict(d2)
        )


class DeltaType(str, Enum):
    """ used to describe a result entry from `deepdiff` """

    # ref is None, act is not None (addition)
    ADDITION = "ADDITION"

    # ref is not None, act is None (removal)
    REMOVAL = "REMOVAL"

    # ref is not None, act is not None (alteration)
    ALTERATION = "ALTERATION"
