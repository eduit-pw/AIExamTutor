"""Tests for the v1.1 exam selector catalog and UI contract."""

import os
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout

from app.core.exam_catalog import EXAM_ENTRIES, entries_for_category
from app.ui.startup_screen import StartupScreen


class ExamCatalogTests(unittest.TestCase):
    """Verify stable category metadata and availability states."""

    def test_catalog_has_three_categories_in_display_order(self) -> None:
        """
        Scenario: The startup catalog groups exams by the public categories
        Given: the built-in v1.1 exam catalog
        When: category ids are read in order
        Then: E8, Matura and vocational exams are present in that order
        """
        # --- ARRANGE ---
        expected = ("e8", "matura", "vocational")
        # --- ACT ---
        categories = tuple(dict.fromkeys(entry.category_id for entry in EXAM_ENTRIES))
        # --- ASSERT ---
        self.assertEqual(categories, expected)

    def test_inf03_is_available_and_inf04_is_planned(self) -> None:
        """
        Scenario: The selector distinguishes implemented and planned workspaces
        Given: the current repository workspace registry
        When: vocational entries are inspected
        Then: INF.03 is available and INF.04 remains planned
        """
        # --- ARRANGE ---
        entries = entries_for_category("vocational")
        # --- ACT ---
        states = {entry.workspace_id: entry.is_available for entry in entries}
        # --- ASSERT ---
        self.assertTrue(states["inf03"])
        self.assertFalse(states["inf04"])

    def test_matura_subjects_have_the_requested_levels(self) -> None:
        """
        Scenario: Matura subjects expose the correct exam levels
        Given: the built-in Matura catalog
        When: entries are grouped by subject
        Then: English, Polish and Mathematics have both levels and the rest only extended
        """
        # --- ARRANGE ---
        expected_levels = {
            "English": {"Matura podstawowa", "Matura rozszerzona"},
            "Język polski": {"Matura podstawowa", "Matura rozszerzona"},
            "Matematyka": {"Matura podstawowa", "Matura rozszerzona"},
            "Historia": {"Matura rozszerzona"},
            "Fizyka": {"Matura rozszerzona"},
            "Biologia": {"Matura rozszerzona"},
            "Geografia": {"Matura rozszerzona"},
            "Chemia": {"Matura rozszerzona"},
        }
        matura_entries = entries_for_category("matura")
        # --- ACT ---
        levels_by_subject = {
            subject: {
                entry.level_label
                for entry in matura_entries
                if entry.subject_label == subject
            }
            for subject in expected_levels
        }
        # --- ASSERT ---
        self.assertEqual(levels_by_subject, expected_levels)
        self.assertEqual(len(matura_entries), 11)
        self.assertEqual(len({entry.entry_id for entry in matura_entries}), 11)


class StartupScreenTests(unittest.TestCase):
    """Verify the StartupScreen.ui object-name contract."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def test_ui_contains_one_button_per_subject_group(self) -> None:
        """
        Scenario: StartupScreen exposes one action per subject
        Given: a running Qt application and the StartupScreen.ui file
        When: catalog entries are grouped by their selector button
        Then: every subject group has exactly one matching button
        """
        # --- ARRANGE / ACT ---
        screen = StartupScreen()
        # --- ASSERT ---
        button_names = {StartupScreen.button_name(entry) for entry in EXAM_ENTRIES}
        buttons = screen.findChildren(QPushButton)
        entry_buttons = {button.objectName() for button in buttons if button.property("examEntry")}
        self.assertEqual(entry_buttons, button_names)
        self.assertEqual(
            StartupScreen.button_name(
                next(entry for entry in EXAM_ENTRIES if entry.entry_id == "matura_english_basic")
            ),
            "examButton_matura_english",
        )

    def test_clicking_available_entry_emits_workspace_id(self) -> None:
        """
        Scenario: Selecting an available exam emits its workspace id
        Given: the startup screen with INF.03 available
        When: the INF.03 button is clicked
        Then: the screen emits 'inf03'
        """
        # --- ARRANGE ---
        screen = StartupScreen()
        selected: list[str] = []
        screen.exam_selected.connect(selected.append)
        button = screen.findChild(QPushButton, "examButton_vocational_inf03")
        # --- ACT ---
        assert button is not None
        button.click()
        # --- ASSERT ---
        self.assertEqual(selected, ["inf03"])

    def test_categories_share_one_scalable_vertical_layout(self) -> None:
        """
        Scenario: The selector uses one consistent card model
        Given: a constructed StartupScreen
        When: category cards and their child layouts are inspected
        Then: all cards use the same vertical layout without redundant metadata
        """
        # --- ARRANGE ---
        screen = StartupScreen()
        card_names = ("e8Card", "maturaCard", "vocationalCard")
        # --- ACT ---
        cards = [screen.findChild(QFrame, name) for name in card_names]
        scroll_area = screen.findChild(QScrollArea, "categoriesScroll")
        # --- ASSERT ---
        self.assertTrue(all(card is not None for card in cards))
        self.assertIsNotNone(scroll_area)
        assert scroll_area is not None
        self.assertEqual(
            scroll_area.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for card in cards:
            assert card is not None
            self.assertIsInstance(card.layout(), QVBoxLayout)
            self.assertTrue(card.property("categoryCard"))
            self.assertIsNone(card.findChild(QLabel, "categoryMeta"))
        self.assertIsNone(screen.findChild(QLabel, "e8Level"))
        self.assertIsNone(screen.findChild(QLabel, "maturaLevel"))
        self.assertIsNone(screen.findChild(QLabel, "vocationalLevel"))
        self.assertIsNotNone(screen.findChild(QLabel, "e8Title"))
        self.assertIsNotNone(screen.findChild(QLabel, "maturaTitle"))
        self.assertIsNotNone(screen.findChild(QLabel, "vocationalTitle"))

    def test_category_cards_share_top_alignment_and_minimum_height(self) -> None:
        """
        Scenario: Category cards form a stable aligned row
        Given: a visible StartupScreen
        When: card geometry is measured after layout
        Then: all cards share the same top edge and height
        """
        # --- ARRANGE ---
        screen = StartupScreen()
        screen.resize(1200, 900)
        screen.show()
        self.application.processEvents()
        cards = [
            screen.findChild(QFrame, name)
            for name in ("e8Card", "maturaCard", "vocationalCard")
        ]
        # --- ACT ---
        geometries = [card.geometry() for card in cards if card is not None]
        # --- ASSERT ---
        self.assertEqual({geometry.top() for geometry in geometries}, {2})
        self.assertEqual(len({geometry.height() for geometry in geometries}), 1)
        self.assertGreaterEqual(geometries[0].height(), 440)
        screen.close()

    def test_exam_buttons_are_top_aligned_and_text_only(self) -> None:
        """
        Scenario: Exam actions are easy to scan and do not imply info dialogs
        Given: a visible StartupScreen with its category cards
        When: button geometry and icons are inspected
        Then: each list starts in the upper half and uses text without generic icons
        """
        # --- ARRANGE ---
        screen = StartupScreen()
        screen.resize(1200, 900)
        screen.show()
        self.application.processEvents()
        first_button_names = (
            "examButton_e8_english",
            "examButton_matura_english",
            "examButton_vocational_inf03",
        )
        # --- ACT / ASSERT ---
        for button_name in first_button_names:
            button = screen.findChild(QPushButton, button_name)
            self.assertIsNotNone(button)
            assert button is not None
            card = button.parentWidget().parentWidget()
            self.assertLess(button.geometry().top(), card.height() // 2)
            self.assertTrue(button.icon().isNull())
        screen.close()


if __name__ == "__main__":
    unittest.main()