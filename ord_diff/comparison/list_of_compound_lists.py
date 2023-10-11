from __future__ import annotations

from google.protobuf import json_format
from ord_schema.proto import reaction_pb2

from .list_of_compounds import OrdDiffListOfCompounds, CompoundDictionary
from ..base import OrdDiff, DiffKind
from ..utils import flat_list_of_lists


class OrdDiffCompoundLol(OrdDiff):
    kind: DiffKind = DiffKind.LIST_OF_COMPOUND_LISTS

    m1: list[list[CompoundDictionary]]

    m2: list[list[CompoundDictionary]]

    n_misplaced_groups: int = 0

    @property
    def n_ref_groups(self):
        return len(self.m1)

    @property
    def n_act_groups(self):
        return len(self.m2)

    @classmethod
    def from_ord(
            cls,
            lol_c1: list[list[reaction_pb2.Compound]],
            lol_c2: list[list[reaction_pb2.Compound]],
    ):
        lol_cd1 = [[json_format.MessageToDict(m) for m in sublist] for sublist in lol_c1]
        lol_cd2 = [[json_format.MessageToDict(m) for m in sublist] for sublist in lol_c2]
        return OrdDiffCompoundLol.from_pair(lol_cd1, lol_cd2)

    @classmethod
    def from_pair(
            cls,
            lol_cd1: list[list[CompoundDictionary]],
            lol_cd2: list[list[CompoundDictionary]],
    ):
        """ determine how many compound lists in `lol_c1` are misplaced in `lol_c2` """
        lol_cd1_flat, lol_to_flat_cd1 = flat_list_of_lists(lol_cd1)
        lol_cd2_flat, lol_to_flat_cd2 = flat_list_of_lists(lol_cd2)
        flat_to_lol_cd1 = {v: k for k, v in lol_to_flat_cd1.items()}
        flat_to_lol_cd2 = {v: k for k, v in lol_to_flat_cd2.items()}
        matched_i2s = OrdDiffListOfCompounds.get_index_match(lol_cd1_flat, lol_cd2_flat)
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

        return cls(
            m1=lol_cd1,
            m2=lol_cd2,
            n_misplaced_groups=len(misplaced_groups)
        )
