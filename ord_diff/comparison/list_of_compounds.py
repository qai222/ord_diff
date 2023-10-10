from __future__ import annotations

import numpy as np
import pandas as pd
from deepdiff import DeepDiff
from ord_schema.proto import reaction_pb2

from .compound import OrdDiffCompound, OrdDiff, DiffKind, CompoundDictionary, json_format
from ..base import FieldChangeType
from ..utils import find_best_match


class OrdDiffListOfCompounds(OrdDiff):
    """ comparison between two lists of `Compound` dictionaries """

    kind: DiffKind = DiffKind.LIST_OF_COMPOUNDS

    m1: list[CompoundDictionary]

    m2: list[CompoundDictionary]

    # the num of compound pairs is always equal to len(m1)
    pair_comparisons: list[OrdDiffCompound | None]

    # num of compound pairs that have at least one field added/removed/changed
    n_altered_compounds: int

    # deep distances of compound pairs, https://zepworks.com/deepdiff/current/deep_distance.html
    # note their average may be different from direct comparison between two lists of compounds with ignore_order=True
    deep_distances: list[float | None]

    # self.index_match[i] = <the matched index of Compound in self.m2> | None if no match
    index_match: dict[int, int | None]

    @property
    def leaf_df(self):
        dfs = []
        for i, diff in enumerate(self.pair_comparisons):
            df = diff.leaf_df
            df['pair_index'] = i
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)

    @property
    def compound_changes(self) -> dict[FieldChangeType, int]:
        d = {
            FieldChangeType.ADDITION: self.n_excess_compounds,
            FieldChangeType.REMOVAL: self.n_absent_compounds,
            FieldChangeType.ALTERATION: self.n_altered_compounds,
        }
        return d

    @property
    def n_m1_compounds(self):
        """ number of compounds in the m1 list """
        return len(self.m1)

    @property
    def n_m2_compounds(self):
        """ number of compounds in the m2 list """
        return len(self.m2)

    @property
    def n_absent_compounds(self):
        """ compounds that are absent in the m2 list but present in the m1 list """
        n = self.n_m1_compounds - self.n_m2_compounds
        if n > 0:
            return n
        else:
            return 0

    @property
    def n_excess_compounds(self):
        """ compounds in the m2 list that has no match to a m1 compound """
        n = self.n_m2_compounds - self.n_m1_compounds
        if n > 0:
            return n
        else:
            return 0

    @staticmethod
    def get_index_match(m1: list[CompoundDictionary], m2: list[CompoundDictionary]) -> list[int | None]:
        """
        for each compound in m1, find the most similar one in m2 based on their **names**, use the full dicts to break tie
        """
        if len(m1) == 0:
            return []

        indices1 = [*range(len(m1))]
        indices2 = [*range(len(m2))]

        # get distance matrix
        dist_mat = np.zeros((len(indices1), len(indices2)))
        for i1 in indices1:
            cd1 = m1[i1]
            name1 = cd1.compound_name
            for i2 in indices2:
                cd2 = m2[i2]
                name2 = cd2.compound_name
                try:
                    distance_name = DeepDiff(name1, name2, get_deep_distance=True).to_dict()['deep_distance']
                except KeyError:
                    distance_name = 0
                try:
                    distance_full = DeepDiff(cd1, cd2, get_deep_distance=True, ignore_order=True).to_dict()[
                        'deep_distance']
                except KeyError:
                    distance_full = 0
                distance = distance_name * 100 + distance_full  # large penalty for wrong names
                dist_mat[i1][i2] = distance

        while len(indices2) < len(indices1):
            indices2.append(None)

        return find_best_match(indices1, indices2, dist_mat)

    @classmethod
    def from_ord(
            cls,
            m1_list: list[reaction_pb2.Compound] | list[reaction_pb2.ProductCompound],
            m2_list: list[reaction_pb2.Compound] | list[reaction_pb2.ProductCompound],
    ):
        m1_list = [json_format.MessageToDict(c) for c in m1_list]
        m2_list = [json_format.MessageToDict(c) for c in m2_list]
        return OrdDiffListOfCompounds.from_pair(m1_list, m2_list)

    @classmethod
    def from_pair(
            cls,
            m1_list: list[CompoundDictionary],
            m2_list: list[CompoundDictionary],
    ):
        """
        find the differences between two lists of compound messages
        1. each compound in ref_compounds is matched with one from act_compounds, matched with None if missing
        2. use deepdiff to inspect matched pairs
        """
        # make sure names are defined for every compound
        for c in m1_list + m2_list:
            assert isinstance(c.compound_name, str)

        matched_i2s = OrdDiffListOfCompounds.get_index_match(m1_list, m2_list)
        pair_comparisons = []
        deep_distances = []
        n_altered_compounds = 0
        for i, m1 in enumerate(m1_list):
            j = matched_i2s[i]
            if j is None:
                pair_comparison = None
                deep_distance = None
            else:
                m2 = m2_list[j]
                pair_comparison = OrdDiffCompound.from_pair(m1, m2)
                if pair_comparison.deep_distance > 0:
                    n_altered_compounds += 1
                deep_distance = pair_comparison.deep_distance
            pair_comparisons.append(pair_comparison)
            deep_distances.append(deep_distance)

        return cls(
            m1=m1_list,
            m2=m2_list,
            pair_comparisons=pair_comparisons,
            n_altered_compounds=n_altered_compounds,
            deep_distances=deep_distances,
            index_match=matched_i2s,
        )
