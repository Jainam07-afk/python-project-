"""
test_library.py - Unit tests. Run with:  python -m unittest -v
(The GUI is not tested here; the logic modules are.)
"""
import tempfile
import unittest

import pandas as pd

import analytics as an
import charts
import sample_data
import validators as v
from data_manager import LibraryData, LibraryError


class ValidatorTests(unittest.TestCase):
    def test_text(self):
        self.assertEqual(v.require_text("  hi  ", "X"), "hi")
        with self.assertRaises(v.ValidationError):
            v.require_text("   ", "X")

    def test_int(self):
        self.assertEqual(v.parse_positive_int("3", "N"), 3)
        for bad in ("0", "-1", "abc", ""):
            with self.assertRaises(v.ValidationError):
                v.parse_positive_int(bad, "N")

    def test_date(self):
        self.assertEqual(v.parse_date("2026-02-01"), pd.Timestamp("2026-02-01"))
        for bad in ("01-02-2026", "2026-13-40", "", "yesterday"):
            with self.assertRaises(v.ValidationError):
                v.parse_date(bad)

    def test_email(self):
        self.assertEqual(v.validate_email(""), "")
        with self.assertRaises(v.ValidationError):
            v.validate_email("not-an-email")


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = LibraryData(self.tmp.name)
        self.bid = self.lib.add_book("Dune", "Frank Herbert", "Fiction", 1)
        self.mid = self.lib.add_member("Asha", "asha@example.com")

    def tearDown(self):
        self.tmp.cleanup()

    def test_duplicate_book_rejected(self):
        with self.assertRaises(LibraryError):
            self.lib.add_book("dune", "frank herbert", "Fiction", 2)

    def test_borrow_return_cycle(self):
        t = self.lib.borrow(self.mid, self.bid, "2026-01-05")
        self.assertEqual(self.lib.available_copies(self.bid), 0)
        with self.assertRaises(LibraryError):  # only one copy
            self.lib.borrow(self.mid, self.bid, "2026-01-06")
        with self.assertRaises(LibraryError):  # before borrow date
            self.lib.return_book(t, "2026-01-01")
        self.lib.return_book(t, "2026-01-10")
        self.assertEqual(self.lib.available_copies(self.bid), 1)
        with self.assertRaises(LibraryError):  # already returned
            self.lib.return_book(t, "2026-01-11")

    def test_future_date_rejected(self):
        with self.assertRaises(LibraryError):
            self.lib.borrow(self.mid, self.bid, "2999-01-01")

    def test_delete_blocked_by_history(self):
        self.lib.borrow(self.mid, self.bid, "2026-01-05")
        with self.assertRaises(LibraryError):
            self.lib.delete_book(self.bid)
        with self.assertRaises(LibraryError):
            self.lib.delete_member(self.mid)

    def test_persistence(self):
        self.lib.borrow(self.mid, self.bid, "2026-01-05")
        again = LibraryData(self.tmp.name)
        self.assertEqual(len(again.books), 1)
        self.assertEqual(len(again.transactions), 1)
        self.assertTrue(pd.isna(again.transactions["return_date"].iloc[0]))

    def test_filters(self):
        self.lib.add_book("Emma", "Jane Austen", "Fiction", 2)
        t = self.lib.borrow(self.mid, self.bid, "2026-01-05")
        self.lib.return_book(t, "2026-01-09")
        self.assertEqual(len(self.lib.search_transactions(status="Returned")), 1)
        self.assertEqual(len(self.lib.search_transactions(status="Borrowed")), 0)
        self.assertEqual(len(self.lib.search_transactions(start="2026-02-01")), 0)
        with self.assertRaises(v.ValidationError):
            self.lib.search_transactions(start="2026-03-01", end="2026-01-01")


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = LibraryData(cls.tmp.name)
        sample_data.generate(cls.lib)
        cls.df = cls.lib.transactions_view()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_add_up(self):
        self.assertEqual(int(an.borrow_counts(self.df).sum()), len(self.df))
        self.assertEqual(int(an.monthly_trend(self.df).sum()), len(self.df))
        self.assertEqual(int(an.weekday_activity(self.df).sum()), len(self.df))

    def test_top_books_sorted(self):
        top = an.top_books(self.df, 5)
        self.assertLessEqual(len(top), 5)
        self.assertTrue(top["borrows"].is_monotonic_decreasing)

    def test_summary_and_report(self):
        s = an.summary(self.df, total_members=len(self.lib.members))
        self.assertEqual(s["total_borrows"], len(self.df))
        self.assertGreater(s["avg_loan_days"], 0)
        self.assertIn("LIBRARY USAGE REPORT", an.build_report(self.df))

    def test_compare_periods(self):
        lo, hi = self.df["borrow_date"].min(), self.df["borrow_date"].max()
        mid = lo + (hi - lo) / 2
        comp = an.compare_periods(self.df, lo, mid, mid + pd.Timedelta(days=1), hi)
        self.assertEqual(int(comp["period_a"].sum() + comp["period_b"].sum()), len(self.df))

    def test_empty_data_is_safe(self):
        empty = self.df.iloc[0:0]
        self.assertEqual(an.summary(empty)["total_borrows"], 0)
        self.assertTrue(an.top_books(empty).empty)
        for fn in charts.CHARTS.values():
            self.assertIsNotNone(fn(empty))

    def test_charts_render(self):
        for fn in charts.CHARTS.values():
            fig = fn(self.df)
            fig.savefig(f"{self.tmp.name}/c.png")


if __name__ == "__main__":
    unittest.main()
