import json
import random

import pytest
from deepdiff import DeepDiff
from google.protobuf import json_format
from ord_schema.message_helpers import find_submessages
from ord_schema.proto import reaction_pb2

from ord_diff.report import report_diff, MDictDiff, MessageType, report_diff_compound_list, MDictListDiff
from ord_diff.utils import flatten, flat_deepdiff_entry, flat_list_of_lists


class TestUtils:

    @pytest.fixture
    def nested_dictionary1(self):
        return {
            1: {"2": 5},
            "lalala": {7: [8, {9: 12}], "kkk": "11"}
        }

    @pytest.fixture
    def nested_dictionary2(self):
        return {
            1: {"2": 5},
            "lalala": {7: [7, {9: 12, 91: 121}], "kkk": "11"}
        }

    def test_flatten(self, nested_dictionary1):
        flat = {(1, '2'): 5, ('lalala', 7, 0): 8, ('lalala', 7, 1, 9): 12, ('lalala', 'kkk'): '11'}
        assert flatten(nested_dictionary1) == flat

    def test_flat_deepdiff_entry(self, nested_dictionary1, nested_dictionary2):
        dd = DeepDiff(nested_dictionary1, nested_dictionary2, ignore_order=True, verbose_level=2, view="tree")
        for dd_report_key, v in dd.to_dict().items():
            for value_altered_level in v:
                path_list_to_t1 = value_altered_level.path(output_format='list', use_t2=False)
                path_list_to_t2 = value_altered_level.path(output_format='list', use_t2=True)
                flat_deepdiff_entry(value_altered_level.t1, path_list_to_t1)
                flat_deepdiff_entry(value_altered_level.t2, path_list_to_t2)


class TestSchema:

    @pytest.fixture
    def sample_reaction_pairs(self):
        with open("pairs_20230731.json", "r") as f:
            data = json.load(f)
        pairs = []
        for rid, r1_json, r2_json in data:
            message_1 = json_format.Parse(r1_json, reaction_pb2.Reaction())
            message_2 = json_format.Parse(r2_json, reaction_pb2.Reaction())
            pairs.append([rid, message_1, message_2])
        return pairs

    @pytest.fixture
    def sample_compound_pairs(self, sample_reaction_pairs):
        compounds = []
        for _, m1, _ in sample_reaction_pairs:
            compounds.extend(find_submessages(m1, reaction_pb2.Compound))
        random.seed(42)
        pairs = []
        for _ in range(50):
            c1, c2 = random.sample(compounds, 2)
            pairs.append([c1, c2])
        return pairs

    @pytest.fixture
    def sample_compound_list_pairs(self, sample_reaction_pairs):
        pairs = []
        for _, m1, m2 in sample_reaction_pairs[:50]:
            compound_list1, _ = flat_list_of_lists(
                [find_submessages(ri, reaction_pb2.Compound) for ri in m1.inputs.values()])
            compound_list2, _ = flat_list_of_lists(
                [find_submessages(ri, reaction_pb2.Compound) for ri in m2.inputs.values()])
            pairs.append([compound_list1, compound_list2])
        return pairs

    @pytest.fixture
    def sample_workup_pairs(self, sample_reaction_pairs):
        workups = []
        for _, m1, _ in sample_reaction_pairs:
            workups.extend(find_submessages(m1, reaction_pb2.ReactionWorkup))
        random.seed(42)
        pairs = []
        for _ in range(50):
            c1, c2 = random.sample(workups, 2)
            pairs.append([c1, c2])
        return pairs

    def test_diff_compound(self, sample_compound_pairs):
        for c1, c2 in sample_compound_pairs:
            df = report_diff(MDictDiff.from_message_pair(c1, c2, MessageType.COMPOUND), message_type=MessageType.COMPOUND)
            assert df.shape

    def test_diff_compound_list(self, sample_compound_list_pairs):
        for cl1, cl2 in sample_compound_list_pairs:
            diff = MDictListDiff.from_message_list_pair(cl1, cl2, MessageType.COMPOUND)
            df = report_diff_compound_list(diff)
            assert df.shape
