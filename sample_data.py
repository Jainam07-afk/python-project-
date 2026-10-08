"""
sample_data.py - Generates realistic demo data (user-defined module 5).
"""
import numpy as np
import pandas as pd

from data_manager import BOOK_COLS, MEMBER_COLS, TXN_COLS

BOOKS = [
    ("Wings of Fire", "A. P. J. Abdul Kalam", "Biography"),
    ("The Alchemist", "Paulo Coelho", "Fiction"),
    ("Godan", "Munshi Premchand", "Fiction"),
    ("Malgudi Days", "R. K. Narayan", "Fiction"),
    ("A Brief History of Time", "Stephen Hawking", "Science"),
    ("Cosmos", "Carl Sagan", "Science"),
    ("The Selfish Gene", "Richard Dawkins", "Science"),
    ("Python Crash Course", "Eric Matthes", "Technology"),
    ("Automate the Boring Stuff", "Al Sweigart", "Technology"),
    ("Operating System Concepts", "Silberschatz", "Technology"),
    ("Computer Networks", "Andrew Tanenbaum", "Technology"),
    ("Wireless Communications", "Andrea Goldsmith", "Technology"),
    ("Discovery of India", "Jawaharlal Nehru", "History"),
    ("India After Gandhi", "Ramachandra Guha", "History"),
    ("Sapiens", "Yuval Noah Harari", "History"),
    ("My Experiments with Truth", "M. K. Gandhi", "Biography"),
    ("Steve Jobs", "Walter Isaacson", "Biography"),
    ("Atomic Habits", "James Clear", "Self-Help"),
    ("Deep Work", "Cal Newport", "Self-Help"),
    ("Ikigai", "Garcia & Miralles", "Self-Help"),
    ("The Innovator's Dilemma", "Clayton Christensen", "Management"),
    ("Good to Great", "Jim Collins", "Management"),
    ("Zero to One", "Peter Thiel", "Management"),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "Management"),
]

MEMBERS = ["Aarav Shah", "Diya Mehta", "Kabir Joshi", "Isha Desai", "Rohan Trivedi",
           "Meera Pandya", "Yash Vora", "Nisha Parikh", "Harsh Bhatt", "Tanvi Rao",
           "Krish Modi", "Anaya Gupta", "Dev Thakkar", "Riya Solanki", "Om Chauhan"]


def generate(data, n_transactions=320, seed=42):
    """Replace the data in a LibraryData object with random demo records."""
    rng = np.random.default_rng(seed)

    books = pd.DataFrame(
        [[f"B{i + 1:03d}", t, a, c, int(rng.integers(2, 5))] for i, (t, a, c) in enumerate(BOOKS)],
        columns=BOOK_COLS)
    members = pd.DataFrame(
        [[f"M{i + 1:03d}", n, f"{n.split()[0].lower()}@example.com"] for i, n in enumerate(MEMBERS)],
        columns=MEMBER_COLS)

    today = pd.Timestamp.today().normalize()
    days = pd.date_range(today - pd.Timedelta(days=364), today)
    # busier before exams (months 3 and 10 of the cycle) and on weekdays
    month_boost = np.where(np.isin(days.month, [3, 4, 10, 11]), 2.0, 1.0)
    weekday_boost = np.where(days.dayofweek >= 5, 0.4, 1.0)
    day_w = month_boost * weekday_boost
    day_w = day_w / day_w.sum()

    book_w = rng.zipf(1.6, len(books)).astype(float)
    book_w = book_w / book_w.sum()

    borrow_dates = days[rng.choice(len(days), n_transactions, p=day_w)]
    book_ids = rng.choice(books["book_id"], n_transactions, p=book_w)
    member_ids = rng.choice(members["member_id"], n_transactions)
    loan_len = rng.integers(3, 22, n_transactions)
    returns = borrow_dates + pd.to_timedelta(loan_len, unit="D")
    returns = pd.Series(returns).where(returns <= today, pd.NaT)

    txns = pd.DataFrame({
        "txn_id": np.arange(1, n_transactions + 1),
        "member_id": member_ids, "book_id": book_ids,
        "borrow_date": borrow_dates, "return_date": returns.to_numpy(),
    })[TXN_COLS].sort_values("borrow_date").reset_index(drop=True)
    txns["txn_id"] = np.arange(1, len(txns) + 1)

    data.books, data.members, data.transactions = books, members, txns
    data.save()
    data.load()
