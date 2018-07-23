import json
import os
from typing import NamedTuple
from uuid import UUID

from Modules.rat import Rat
from utils.ratlib import Platforms

RatJSONTuple = NamedTuple("RatJSONTuple", rat=Rat, json_rat=dict)


def get_rat1() -> RatJSONTuple:
    with open(os.path.join(os.path.dirname(__file__), "rat1.json")) as file:
        json_rat = json.load(file)

    return RatJSONTuple(
        Rat(
            uuid=UUID("dc9c91fb-9ead-47e9-8771-81da2c1971bc"),
            name="MrRatMan",
            platform=Platforms.PC
        ),
        json_rat
    )
