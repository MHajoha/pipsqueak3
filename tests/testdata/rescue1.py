import datetime
import json
import os
from typing import NamedTuple
from uuid import UUID

from Modules.mark_for_deletion import MarkForDeletion
from Modules.rat import Rat
from Modules.rat_quotation import Quotation
from Modules.rat_rescue import Rescue
from utils.ratlib import Platforms

RescueJSONTuple = NamedTuple("RescueJSONTuple", rescue=Rescue, json_rescue=dict)


def get_rescue1():
    with open(os.path.join(os.path.dirname(__file__), "rescue1.json")) as file:
        json_rescue = json.load(file)

    result = RescueJSONTuple(
        Rescue(
            UUID("bede70e3-a695-448a-8376-ecbcf74385b6"),
            client="Some Client",
            system="ALPHA CENTAURI",
            irc_nickname="Some_Client",
            created_at=datetime.datetime(2018, 1, 7, 22, 48, 38, 123000),
            updated_at=datetime.datetime(2018, 1, 8, 10, 34, 40, 123000),
            unidentified_rats=["unable_to_use_nickserv[PC]"],
            quotes=[
                Quotation(
                    message="RATSIGNAL - CMDR Some Client - System: Alpha Centauri - Platform: PC - O2: OK - Language: English (en-GB) - IRC Nickname: Some_Client",
                    author="Mecha",
                    created_at=datetime.datetime(2018, 1, 7, 22, 48, 38, 123456),
                    updated_at=datetime.datetime(2018, 1, 7, 22, 48, 38, 123456),
                    last_author="Mecha"
                ),
                Quotation(
                    message="[Autodetected system: Alpha Centauri]",
                    author="Mecha",
                    created_at=datetime.datetime(2018, 1, 7, 22, 48, 38, 123458),
                    updated_at=datetime.datetime(2018, 1, 7, 22, 48, 38, 123458),
                    last_author="Mecha"
                )
            ],
            title="Operation Go Away",
            first_limpet=UUID("dc9c91fb-9ead-47e9-8771-81da2c1971bc"),
            board_index=9,
            mark_for_deletion=MarkForDeletion(False, None, None),
            lang_id="en",
            rats=[
                Rat(
                    uuid=UUID("dc9c91fb-9ead-47e9-8771-81da2c1971bc"),
                    name="Rat1",
                    platform=Platforms.PC,
                ),
                Rat(
                    uuid=UUID("aa42e51c-5e55-4261-9958-6f1743957d70"),
                    name="Rat2",
                    platform=Platforms.PC
                )
            ]
        ),
        json_rescue
    )
    result.rescue.platform = Platforms.PC
    return result
