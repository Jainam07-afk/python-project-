"""
data_manager.py - Storage and CRUD for books, members and transactions
(user-defined module 2).

Data lives in three pandas DataFrames and is persisted to CSV files
inside `data_dir`, so the app keeps its records between runs.
"""
import os

try:
    import numpy as np  # pyright: ignore[reportMissingImports]
except ImportError:
    class _NumPyCompat:
        @staticmethod
        def nanmax(values):
            items = [v for v in values if v is not None and not pd.isna(v)]
            return max(items) if items else 0

        @staticmethod
        def where(condition, true_value, false_value):
            cond = list(condition.tolist() if hasattr(condition, "tolist") else condition)
            true_list = list(true_value.tolist() if hasattr(true_value, "tolist") else true_value)
            false_list = list(false_value.tolist() if hasattr(false_value, "tolist") else false_value)
            return [true_list[i] if c else false_list[i] for i, c in enumerate(cond)]


    np = _NumPyCompat()

import pandas as pd  # pyright: ignore[reportMissingModuleSource]

import validators as v

BOOK_COLS = ["book_id", "title", "author", "category", "copies"]
MEMBER_COLS = ["member_id", "name", "email"]
TXN_COLS = ["txn_id", "member_id", "book_id", "borrow_date", "return_date"]


class LibraryError(Exception):
    """Raised for rule violations (duplicates, missing records, no copies...)."""


def _next_id(series, prefix, width=3):
    """Generate the next id such as B007 from an existing id column."""
    nums = pd.to_numeric(series.astype(str).str[len(prefix):], errors="coerce")
    top = int(np.nanmax(nums.to_numpy())) if len(nums) and nums.notna().any() else 0
    return f"{prefix}{top + 1:0{width}d}"


class LibraryData:
    """In-memory tables + CSV persistence + validated operations."""

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.load()

    # ------------------------------------------------------------ persistence
    def _path(self, name):
        return os.path.join(self.data_dir, f"{name}.csv")

    def _read(self, name, cols):
        path = self._path(name)
        if not os.path.exists(path):
            return pd.DataFrame(columns=cols)
        try:
            df = pd.read_csv(path)
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise LibraryError(f"Could not read {path}: {exc}")
        missing = set(cols) - set(df.columns)
        if missing:
            raise LibraryError(f"{path} is missing columns: {sorted(missing)}")
        return df[cols]

    def load(self):
        """(Re)load all three tables from disk."""
        books = self._read("books", BOOK_COLS)
        members = self._read("members", MEMBER_COLS)
        txns = self._read("transactions", TXN_COLS)

        for col in ("book_id", "title", "author", "category"):
            books[col] = books[col].fillna("").astype(str)
        books["copies"] = pd.to_numeric(books["copies"], errors="coerce").fillna(1).astype(int)
        for col in MEMBER_COLS:
            members[col] = members[col].fillna("").astype(str)
        txns["txn_id"] = pd.to_numeric(txns["txn_id"], errors="coerce").astype("Int64")
        txns["member_id"] = txns["member_id"].astype(str)
        txns["book_id"] = txns["book_id"].astype(str)
        txns["borrow_date"] = pd.to_datetime(txns["borrow_date"], errors="coerce")
        txns["return_date"] = pd.to_datetime(txns["return_date"], errors="coerce")

        self.books = books.reset_index(drop=True)
        self.members = members.reset_index(drop=True)
        self.transactions = txns.dropna(subset=["txn_id", "borrow_date"]).reset_index(drop=True)

    def save(self):
        """Write all tables to CSV."""
        try:
            self.books.to_csv(self._path("books"), index=False)
            self.members.to_csv(self._path("members"), index=False)
            self.transactions.to_csv(self._path("transactions"), index=False)
        except OSError as exc:
            raise LibraryError(f"Could not save data: {exc}")

    # ------------------------------------------------------------------ books
    def _book_mask(self, book_id):
        mask = self.books["book_id"] == book_id
        if not mask.any():
            raise LibraryError(f"Book {book_id} does not exist.")
        return mask

    def active_loans(self, book_id):
        t = self.transactions
        return int(((t["book_id"] == book_id) & t["return_date"].isna()).sum())

    def available_copies(self, book_id):
        copies = int(self.books.loc[self._book_mask(book_id), "copies"].iloc[0])
        return copies - self.active_loans(book_id)

    def add_book(self, title, author, category, copies):
        title = v.require_text(title, "Title", 120)
        author = v.require_text(author, "Author")
        category = v.require_text(category, "Category", 40)
        copies = v.parse_positive_int(copies, "Copies")
        b = self.books
        dup = (b["title"].str.lower() == title.lower()) & (b["author"].str.lower() == author.lower())
        if dup.any():
            raise LibraryError("This book (title + author) already exists.")
        book_id = _next_id(b["book_id"], "B")
        row = pd.DataFrame([[book_id, title, author, category, copies]], columns=BOOK_COLS)
        self.books = pd.concat([b, row], ignore_index=True)
        self.save()
        return book_id

    def update_book(self, book_id, title, author, category, copies):
        mask = self._book_mask(book_id)
        title = v.require_text(title, "Title", 120)
        author = v.require_text(author, "Author")
        category = v.require_text(category, "Category", 40)
        copies = v.parse_positive_int(copies, "Copies")
        if copies < self.active_loans(book_id):
            raise LibraryError("Copies cannot be fewer than the number currently on loan.")
        self.books.loc[mask, BOOK_COLS[1:]] = [title, author, category, copies]
        self.save()

    def delete_book(self, book_id):
        mask = self._book_mask(book_id)
        if (self.transactions["book_id"] == book_id).any():
            raise LibraryError("Cannot delete a book that has borrowing history.")
        self.books = self.books[~mask].reset_index(drop=True)
        self.save()

    def search_books(self, text=""):
        text = str(text).strip().lower()
        b = self.books.copy()
        b["available"] = [self.available_copies(i) for i in b["book_id"]]
        if not text:
            return b
        hay = (b["title"] + " " + b["author"] + " " + b["category"]).str.lower()
        return b[hay.str.contains(text, regex=False)].reset_index(drop=True)

    # ---------------------------------------------------------------- members
    def _member_mask(self, member_id):
        mask = self.members["member_id"] == member_id
        if not mask.any():
            raise LibraryError(f"Member {member_id} does not exist.")
        return mask

    def add_member(self, name, email=""):
        name = v.require_text(name, "Name")
        email = v.validate_email(email)
        m = self.members
        if (m["name"].str.lower() == name.lower()).any():
            raise LibraryError("A member with this name already exists.")
        member_id = _next_id(m["member_id"], "M")
        row = pd.DataFrame([[member_id, name, email]], columns=MEMBER_COLS)
        self.members = pd.concat([m, row], ignore_index=True)
        self.save()
        return member_id

    def update_member(self, member_id, name, email=""):
        mask = self._member_mask(member_id)
        name = v.require_text(name, "Name")
        email = v.validate_email(email)
        self.members.loc[mask, ["name", "email"]] = [name, email]
        self.save()

    def delete_member(self, member_id):
        mask = self._member_mask(member_id)
        if (self.transactions["member_id"] == member_id).any():
            raise LibraryError("Cannot delete a member who has borrowing history.")
        self.members = self.members[~mask].reset_index(drop=True)
        self.save()

    def search_members(self, text=""):
        text = str(text).strip().lower()
        m = self.members
        if not text:
            return m.copy()
        hay = (m["name"] + " " + m["email"]).str.lower()
        return m[hay.str.contains(text, regex=False)].reset_index(drop=True)

    # ----------------------------------------------------------- transactions
    def borrow(self, member_id, book_id, borrow_date):
        self._member_mask(member_id)
        self._book_mask(book_id)
        when = v.parse_date(borrow_date, "Borrow date")
        if when > pd.Timestamp.today().normalize():
            raise LibraryError("Borrow date cannot be in the future.")
        if self.available_copies(book_id) < 1:
            raise LibraryError("No copies of this book are currently available.")
        t = self.transactions
        txn_id = int(t["txn_id"].max()) + 1 if len(t) else 1
        row = pd.DataFrame([[txn_id, member_id, book_id, when, pd.NaT]], columns=TXN_COLS)
        self.transactions = pd.concat([t, row], ignore_index=True)
        self.save()
        return txn_id

    def return_book(self, txn_id, return_date):
        mask = self.transactions["txn_id"] == txn_id
        if not mask.any():
            raise LibraryError(f"Transaction {txn_id} does not exist.")
        if self.transactions.loc[mask, "return_date"].notna().any():
            raise LibraryError("This book has already been returned.")
        when = v.parse_date(return_date, "Return date")
        if when < self.transactions.loc[mask, "borrow_date"].iloc[0]:
            raise LibraryError("Return date cannot be before the borrow date.")
        self.transactions.loc[mask, "return_date"] = when
        self.save()

    def delete_transaction(self, txn_id):
        mask = self.transactions["txn_id"] == txn_id
        if not mask.any():
            raise LibraryError(f"Transaction {txn_id} does not exist.")
        self.transactions = self.transactions[~mask].reset_index(drop=True)
        self.save()

    def transactions_view(self):
        """Transactions joined with member and book details (used by analytics)."""
        t = self.transactions.merge(self.books[["book_id", "title", "author", "category"]],
                                    on="book_id", how="left")
        t = t.merge(self.members[["member_id", "name"]], on="member_id", how="left")
        t = t.rename(columns={"name": "member"})
        t["status"] = np.where(t["return_date"].isna(), "Borrowed", "Returned")
        cols = ["txn_id", "member_id", "member", "book_id", "title", "author",
                "category", "borrow_date", "return_date", "status"]
        return t[cols].sort_values("borrow_date", ascending=False).reset_index(drop=True)

    def search_transactions(self, member_id=None, book_id=None, status=None,
                            start=None, end=None):
        """Filter the joined view. Dates may be strings (YYYY-MM-DD) or None."""
        start = v.parse_date(start, "From date", allow_empty=True) if start else None
        end = v.parse_date(end, "To date", allow_empty=True) if end else None
        v.validate_range(start, end)
        df = self.transactions_view()
        if member_id:
            df = df[df["member_id"] == member_id]
        if book_id:
            df = df[df["book_id"] == book_id]
        if status in ("Borrowed", "Returned"):
            df = df[df["status"] == status]
        if start is not None:
            df = df[df["borrow_date"] >= start]
        if end is not None:
            df = df[df["borrow_date"] <= end]
        return df.reset_index(drop=True)
