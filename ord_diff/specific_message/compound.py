from __future__ import annotations

from enum import Enum

import pandas as pd

from ..base import OrdDiff, OrdLeaf, OrdDictionary, DeltaType


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
