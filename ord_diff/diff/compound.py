from __future__ import annotations

from collections import defaultdict
from enum import Enum

from deepdiff import DeepDiff

from ..base import OrdDiff, DiffKind, OrdLeaf, OrdDictionary
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
    kind = DiffKind.COMPOUND

    m1: CompoundDictionary

    m2: CompoundDictionary

    leafs_added: list[CompoundLeaf]  # from m2

    leafs_removed: list[CompoundLeaf]  # from m1

    leafs_altered: list[tuple[CompoundLeaf, CompoundLeaf]]  # from (m1, m2)

    @classmethod
    def from_pair(cls, m1: CompoundDictionary, m2: CompoundDictionary):
        dd = DeepDiff(
            m1.d, m2.d,
            ignore_order=True, verbose_level=2, view='tree', get_deep_distance=True
        )
        deep_distance, leafs_added, leafs_removed, leafs_altered = parse_deepdiff(dd)
        return cls(
            m1=m1,
            m2=m2,
            leafs_added=[m2.get_leaf(path_tuple=pt) for pt in leafs_added],
            leafs_removed=[m1.get_leaf(path_tuple=pt) for pt in leafs_removed],
            leafs_altered=[m1.get_leaf(path_tuple=pt) for pt in leafs_altered],
        )
