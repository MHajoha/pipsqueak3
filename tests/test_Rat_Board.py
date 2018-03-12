"""
Unittest file for the Rat_Board module.
"""
from unittest import TestCase
from uuid import uuid4

from Modules.Rat_Board import RatBoard, IndexNotFreeError
from Modules.rat_rescue import Rescue


class RatBoardTests(TestCase):
    """
    Tests for RatBoard
    """

    def setUp(self):
        """
        Set up for each test
        """
        super().setUp()
        self.board = RatBoard()
        self.some_rescue = Rescue(uuid4(), "unit_test[BOT]", "snafu", "unit_test", board_index=-42)

    def test_rescue_creation_existing_good_index(self):
        """
        verifies a rescue can be added to the board when it already has an index
        """
        # spawn a new rescue with a ID
        self.board.append(rescue=self.some_rescue)
        self.assertEqual(self.board._rescues[-42], self.some_rescue)

    def test_def_rescue_creation_existing_bad_index(self):
        """
        Verifies a rescue cannot be added when its defined index is already in use.
        """
        # add it once
        self.board.append(rescue=self.some_rescue)
        # and try to add it again
        with self.assertRaises(IndexNotFreeError):
            self.board.append(rescue=self.some_rescue)

    def test_rescue_creation_with_overwrite(self):
        """
        Verifies a rescue can be added as to overwrite an existing entry.
        """
        self.board.append(rescue=self.some_rescue)
        my_rescue = Rescue(uuid4(), "foo", "bar", "foo", board_index=-42)
        self.board.append(rescue=my_rescue, overwrite=True)
        self.assertEqual(self.board._rescues[-42], my_rescue)

    def test_search_by_index(self):
        """
        Verifies `a case can be found via RescueBoard.search(index=x)
        """
        self.board.append(rescue=self.some_rescue)
        found = self.board.search(index=-42)
        self.assertEqual(found, self.some_rescue)

    def test_search_by_client(self):
        """
        Verifies a case can be found via RescueBoard.search(name="foo")
        """
        self.board.append(rescue=self.some_rescue)
        found = self.board.search(client=self.some_rescue.client)
        self.assertEqual(found.client, self.some_rescue.client)