from __future__ import annotations

from enum import Enum

import pandas as pd

from ..base import OrdDiff, OrdLeaf, OrdDictionary, DeltaType, OrdListDiff
from ..utils import flat_list_of_lists


class CompoundLeafType(str, Enum):
    """ they should be *disjoint* so any leaf of a compound can only be one of the these classes """

    reaction_role = 'reactionRole'
    # NOTE: this would have been `reaction_role` but field names are turned into camelCase by default

    identifiers = 'identifiers'

    amount = 'amount'

    other = 'other'


def get_compound_leaf_type(leaf: OrdLeaf):
    for ck in list(CompoundLeafType):
        if ck == CompoundLeafType.other:
            continue
        if ck in leaf.path_list:
            return CompoundLeafType(ck)
    return CompoundLeafType.other


def get_compound_leaf_type_counter(cd: OrdDictionary):
    counter = {clt: 0 for clt in list(CompoundLeafType) + [None, ]}
    for leaf in cd.leafs:
        counter[get_compound_leaf_type(leaf)] += 1
    return counter


def get_compound_name(cd: OrdDictionary):
    for identifier in cd.d["identifiers"]:
        if identifier['type'] == 'NAME':
            return identifier['value']  # assuming only one name is defined
    raise ValueError('`NAME` not found in the compound dict')


def get_compound_leaf_diff(compound_diff: OrdDiff):
    records = []
    for leaf in compound_diff.m1.leafs:
        if leaf in compound_diff.delta_leafs[DeltaType.REMOVAL]:
            ct = DeltaType.REMOVAL
        elif leaf in compound_diff.delta_leafs[DeltaType.ALTERATION]:
            ct = DeltaType.ALTERATION
        else:
            ct = None
        record = {
            "from": "m1",
            "path": ".".join(leaf.path_list),
            "leaf_type": leaf.leaf_type,
            "change_type": ct,
        }
        records.append(record)
    for leaf in compound_diff.m2.leafs:
        if leaf in compound_diff.delta_leafs[DeltaType.ADDITION]:
            record = {
                "from": "m2",
                "path": ".".join(leaf.path_list),
                "leaf_type": leaf.leaf_type,
                "change_type": DeltaType.ADDITION,
            }
            records.append(record)
    return pd.DataFrame.from_records(records)


def get_compound_list_leaf_diff(compound_list_diff: OrdListDiff):
    dfs = []
    for i, diff in enumerate(compound_list_diff.pair_comparisons):
        if diff is None:
            continue
        df = get_compound_leaf_diff(diff)
        df['pair_index'] = i
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def get_misplaced_lol(
        lol_cd1: list[list[OrdDictionary]],
        lol_cd2: list[list[OrdDictionary]],
):
    """ determine how many compound lists in `lol_c1` are misplaced in `lol_c2` """
    lol_cd1_flat, lol_to_flat_cd1 = flat_list_of_lists(lol_cd1)
    lol_cd2_flat, lol_to_flat_cd2 = flat_list_of_lists(lol_cd2)
    flat_to_lol_cd1 = {v: k for k, v in lol_to_flat_cd1.items()}
    flat_to_lol_cd2 = {v: k for k, v in lol_to_flat_cd2.items()}

    matched_i2s = OrdListDiff.get_index_match_compound(lol_cd1_flat, lol_cd2_flat)
    lol1_to_lol2 = dict()
    for lol_index_1 in lol_to_flat_cd1:
        flat_index_1 = lol_to_flat_cd1[lol_index_1]
        matched_index_2 = matched_i2s[flat_index_1]
        if matched_index_2 is None:
            lol_index_2 = None
        else:
            lol_index_2 = flat_to_lol_cd2[matched_index_2]
        lol1_to_lol2[lol_index_1] = lol_index_2

    misplaced_groups = []
    for i, group in enumerate(lol_cd1):
        is_misplaced = False
        group_indices_1 = [(i, j) for j in range(len(group))]
        group_indices_2 = [lol1_to_lol2[gi] for gi in group_indices_1]
        if None in group_indices_2:
            # print("group element missing")
            is_misplaced = True
        elif len(set([x[0] for x in group_indices_2])) != 1:
            # print("group split")
            is_misplaced = True
        elif len(lol_cd2[group_indices_2[0][0]]) > len(group):
            # print("group expanded")
            is_misplaced = True
        elif len(lol_cd2[group_indices_2[0][0]]) < len(group):
            # print("group contracted")  # never happens as the matching algo fills None
            is_misplaced = True
        if is_misplaced:
            misplaced_groups.append(group)
    return misplaced_groups
