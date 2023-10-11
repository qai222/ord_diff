from __future__ import annotations

from enum import Enum

import numpy as np
from deepdiff import DeepDiff
from google.protobuf import json_format
from pydantic import BaseModel

from .utils import parse_deepdiff, flatten, find_best_match


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


class OrdDiff(BaseModel):
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


class OrdListDiff(BaseModel):
    """ base model for a comparison between two lists of messages """
    m1: list[OrdDictionary]
    m2: list[OrdDictionary]

    # the num of pairs is always equal to len(m1)
    pair_comparisons: list[OrdDiff | None]

    # num of message pairs that have at least one field added/removed/changed
    n_changed: int

    # self.index_match[i] = <the matched index of Compound in self.m2> | None if no match
    index_match: dict[int, int | None]

    @property
    def n_m1(self):
        """ number of messages in the m1 list """
        return len(self.m1)

    @property
    def n_m2(self):
        """ number of messages in the m2 list """
        return len(self.m2)

    @property
    def n_absent(self):
        """ messages that are absent in the m2 list but present in the m1 list """
        n = self.n_m1 - self.n_m2
        if n > 0:
            return n
        else:
            return 0

    @property
    def n_excess(self):
        """ messages in the m2 list that has no match to a m1 message """
        n = self.n_m2 - self.n_m1
        if n > 0:
            return n
        else:
            return 0

    @classmethod
    def from_ord(cls, m1_list, m2_list, message_type="COMPOUND"):
        m1_list = [json_format.MessageToDict(c) for c in m1_list]
        m2_list = [json_format.MessageToDict(c) for c in m2_list]
        return OrdListDiff.from_pair(m1_list, m2_list, message_type)

    @classmethod
    def from_pair(
            cls,
            m1_list: list[OrdDictionary],
            m2_list: list[OrdDictionary],
            message_type: str = "COMPOUND",
    ):
        """
        find the differences between two lists of compound messages
        1. each compound in ref_compounds is matched with one from act_compounds, matched with None if missing
        2. use deepdiff to inspect matched pairs
        """
        # make sure names are defined for every compound
        for c in m1_list + m2_list:
            assert isinstance(c.compound_name, str)

        if message_type == "COMPOUND":
            matched_i2s = OrdListDiff.get_index_match_compound(m1_list, m2_list)
        else:
            matched_i2s = OrdListDiff.get_index_match_dummy(m1_list, m2_list)

        pair_comparisons = []
        n_changed = 0
        for i, m1 in enumerate(m1_list):
            j = matched_i2s[i]
            if j is None:
                pair_comparison = None
            else:
                m2 = m2_list[j]
                pair_comparison = OrdDiff.from_pair(m1, m2)
                if pair_comparison.deep_distance > 0:
                    n_changed += 1
            pair_comparisons.append(pair_comparison)

        return cls(
            m1=m1_list,
            m2=m2_list,
            pair_comparisons=pair_comparisons,
            n_changed=n_changed,
            index_match=matched_i2s,
        )

    @staticmethod
    def get_index_match_dummy(m1_list: list[OrdDictionary], m2_list: list[OrdDictionary], ):
        if len(m1_list) <= len(m2_list):
            return [*range(len(m1_list))]
        else:
            return [*range(len(m2_list))] + [None, ] * (len(m1_list) - len(m2_list))

    @staticmethod
    def get_index_match_compound(m1_list: list[OrdDictionary], m2_list: list[OrdDictionary], ):
        """
        for each compound in m1,
        find the most similar one in m2 based on their **names**, use the full dicts to break tie
        """
        if len(m1_list) == 0:
            return []

        indices1 = [*range(len(m1_list))]
        indices2 = [*range(len(m2_list))]

        # get distance matrix
        dist_mat = np.zeros((len(indices1), len(indices2)))
        for i1 in indices1:
            cd1 = m1_list[i1]
            name1 = cd1.compound_name
            for i2 in indices2:
                cd2 = m2_list[i2]
                name2 = cd2.compound_name
                try:
                    distance_name = DeepDiff(name1, name2, get_deep_distance=True).to_dict()['deep_distance']
                except KeyError:
                    distance_name = 0
                try:
                    distance_full = DeepDiff(
                        cd1, cd2, get_deep_distance=True, ignore_order=True
                    ).to_dict()['deep_distance']
                except KeyError:
                    distance_full = 0
                distance = distance_name * 100 + distance_full  # large penalty for wrong names
                dist_mat[i1][i2] = distance

        while len(indices2) < len(indices1):
            indices2.append(None)

        return find_best_match(indices1, indices2, dist_mat)


class DeltaType(str, Enum):
    """ used to describe a result entry from `deepdiff` """

    # ref is None, act is not None (addition)
    ADDITION = "ADDITION"

    # ref is not None, act is None (removal)
    REMOVAL = "REMOVAL"

    # ref is not None, act is not None (alteration)
    ALTERATION = "ALTERATION"
