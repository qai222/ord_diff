from __future__ import annotations

from collections import defaultdict
from enum import Enum

import pandas as pd
from deepdiff import DeepDiff
from google.protobuf import json_format
from ord_schema import reaction_pb2

from ..base import OrdDiff, DiffKind, OrdLeaf, OrdDictionary, FieldChangeType
from ..utils import flatten, parse_deepdiff


class CompoundLeafType(str, Enum):
    """ they should be *disjoint* so any leaf of a compound can only be one of the these classes """

    reaction_role = 'reactionRole'
    # NOTE: this would have been `reaction_role` but field names are turned into camelCase by default

    identifiers = 'identifiers'

    amount = 'amount'


class CompoundLeaf(OrdLeaf):

    @property
    def leaf_type(self) -> CompoundLeafType | None:
        for ck in list(CompoundLeafType):
            if ck in self.path_list:
                return CompoundLeafType(ck)


class CompoundDictionary(OrdDictionary):
    leafs: list[CompoundLeaf]

    @property
    def compound_name(self):
        for identifier in self.d["identifiers"]:
            if identifier['type'] == 'NAME':
                return identifier['value']
        raise ValueError('`NAME` not found in the compound dict')

    @property
    def leaf_type_counter(self):
        counter = {clt: 0 for clt in list(CompoundLeafType) + [None, ]}
        for leaf in self.leafs:
            counter[leaf.leaf_type] += 1
        return counter

    @classmethod
    def from_dict(cls, compound_dict: dict):
        leafs = []
        for path_tuple, value in flatten(compound_dict).items():
            leaf = CompoundLeaf(path_list=list(path_tuple), value=value, is_implicit=None)
            leafs.append(leaf)
        return cls(fields=leafs, d=compound_dict)

    @property
    def leaf_path_tuple_to_leaf_type(self) -> dict[
        tuple[str | int, ...], CompoundLeafType | None
    ]:
        return {leaf.path_tuple: leaf.leaf_type for leaf in self.fields}

    @property
    def leaf_type_to_leaf_path_tuples(self) -> dict[
        CompoundLeafType | None, list[tuple[str | int, ...]]
    ]:
        d = defaultdict(list)
        for path_tuple, leaf_type in self.leaf_path_tuple_to_leaf_type.items():
            d[leaf_type].append(path_tuple)
        return d


class OrdDiffCompound(OrdDiff):
    """ comparison between two `Compound` dictionaries """

    kind = DiffKind.COMPOUND

    m1: CompoundDictionary

    m2: CompoundDictionary

    leafs_added: list[CompoundLeaf]  # from m2

    leafs_removed: list[CompoundLeaf]  # from m1

    leafs_altered_1: list[CompoundLeaf]  # from m1

    leafs_altered_2: list[CompoundLeaf]  # from m2

    paths_added: list[tuple]  # from m2

    paths_removed: list[tuple]  # from m1

    paths_altered_1: list[tuple]  # from m1

    paths_altered_2: list[tuple]  # from m2

    deep_distance: float

    @property
    def leaf_df(self):
        records = []
        for leaf in self.m1.leafs:
            if leaf in self.leafs_removed:
                ct = FieldChangeType.REMOVAL
            elif leaf in self.leafs_altered_1:
                ct = FieldChangeType.ALTERATION
            else:
                ct = None
            record = {
                "from": "m1",
                "path": ".".join(leaf.path_list),
                "leaf_type": leaf.leaf_type,
                "change_type": ct,
            }
            records.append(record)
        for leaf in self.m2.leafs:
            if leaf in self.leafs_added:
                record = {
                    "from": "m2",
                    "path": ".".join(leaf.path_list),
                    "leaf_type": leaf.leaf_type,
                    "change_type": FieldChangeType.ADDITION,
                }
                records.append(record)
        return pd.DataFrame.from_records(records)

    @classmethod
    def from_pair(cls, m1: CompoundDictionary, m2: CompoundDictionary):
        dd = DeepDiff(
            m1.d, m2.d,
            ignore_order=True, verbose_level=2, view='tree', get_deep_distance=True
        )

        (
            deep_distance,
            paths_added, paths_removed, paths_altered_1, paths_altered_2,
            leafs_added, leafs_removed, leafs_altered_1, leafs_altered_2,
        ) = parse_deepdiff(dd)
        return cls(
            m1=m1,
            m2=m2,
            paths_added=paths_added,
            paths_removed=paths_removed,
            paths_altered_1=paths_altered_1,
            paths_altered_2=paths_altered_2,
            leafs_added=[m2.get_leaf(path_tuple=pt) for pt in leafs_added],
            leafs_removed=[m1.get_leaf(path_tuple=pt) for pt in leafs_removed],
            leafs_altered_1=[m1.get_leaf(path_tuple=pt) for pt in leafs_altered_1],
            leafs_altered_2=[m1.get_leaf(path_tuple=pt) for pt in leafs_altered_2],
            deep_distance=deep_distance,
        )

    @classmethod
    def from_ord(
            cls,
            m1: reaction_pb2.Compound | reaction_pb2.ProductCompound,
            m2: reaction_pb2.Compound | reaction_pb2.ProductCompound,
    ):
        d1 = json_format.MessageToDict(m1)
        d2 = json_format.MessageToDict(m2)
        return OrdDiffCompound.from_pair(
            m1=CompoundDictionary.from_dict(d1),
            m2=CompoundDictionary.from_dict(d2)
        )
