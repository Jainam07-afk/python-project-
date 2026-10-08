0# Library Borrowing Analyzer (P12 - Library)

**Student:** JAINAM HIREN PATEL  |  **Enrollment:** IU2441230395

Records every library borrowing transaction and turns it into usage insight:
frequently borrowed books, borrowing trends, and periods of higher activity.

## Setup
    pip install pandas numpy matplotlib      (Tkinter ships with Python on Windows/macOS)
    python app.py                            (then File > Load sample data to try it out)
    python -m unittest -v                    (run the tests)

## Modules
| File | Purpose |
|---|---|
| `validators.py` | Input validation (text, numbers, dates, email) |
| `data_manager.py` | Books / members / transactions CRUD, search, CSV persistence (Pandas) |
| `analytics.py` | Counts, averages, top books, monthly trend, peak periods, period comparison (NumPy + Pandas) |
| `charts.py` | Matplotlib charts: top books, monthly trend, category share, weekday activity, period comparison |
| `sample_data.py` | Random demo data generator |
| `app.py` | Tkinter GUI (Books, Members, Transactions, Analytics tabs) |
| `test_library.py` | 16 unit tests |
