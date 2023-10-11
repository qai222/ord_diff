import json
import random

import pytest
from google.protobuf import json_format
from ord_schema.message_helpers import find_submessages
from ord_schema.proto import reaction_pb2

from ord_diff.base import OrdDiff
from ord_diff.utils import flatten


class TestUtils:

    @pytest.fixture
    def nested_dictionary(self):
        return {
            1: {"2": 5},
            "lalala": {7: [8, {9: 12}], "kkk": "11"}
        }

    def test_flatten(self, nested_dictionary):
        flat = {(1, '2'): 5, ('lalala', 7, 0): 8, ('lalala', 7, 1, 9): 12, ('lalala', 'kkk'): '11'}
        assert flatten(nested_dictionary) == flat


class TestOrdDiff:

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

    def test_compound_diff(self, sample_reaction_pairs):
        compounds = []
        for _, m1, _ in sample_reaction_pairs:
            compounds.extend(find_submessages(m1, reaction_pb2.Compound))
        random.seed(42)
        for _ in range(50):
            c1, c2 = random.sample(compounds, 2)
            OrdDiff.from_ord(c1, c2)
