"""
analytics.py - Borrowing statistics and trends (user-defined module 3).

All functions take the joined transactions DataFrame produced by
LibraryData.transactions_view() and return pandas / NumPy results,
so they are easy to test and reuse from the GUI or charts.
"""
import numpy as np
import pandas as pd

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def borrow_counts(df, by="title"):
    """Number of borrows per book title / category / member (highest first)."""
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby(by).size().sort_values(ascending=False, kind="stable")


def top_books(df, n=5):
    """Most frequently borrowed books as a DataFrame (title, borrows)."""
    counts = borrow_counts(df, "title").head(n)
    return counts.rename("borrows").reset_index()


def monthly_trend(df):
    """Borrows per calendar month, with zero-filled gaps."""
    if df.empty:
        return pd.Series(dtype=int)
    series = df.groupby(df["borrow_date"].dt.to_period("M")).size()
    full = pd.period_range(series.index.min(), series.index.max(), freq="M")
    return series.reindex(full, fill_value=0)


def weekday_activity(df):
    """Borrows per day of the week (Monday..Sunday)."""
    names = df["borrow_date"].dt.day_name()
    return names.value_counts().reindex(WEEKDAYS, fill_value=0)


def peak_periods(df, n=3):
    """Busiest months with how far above the monthly average they are (%)."""
    trend = monthly_trend(df)
    if trend.empty:
        return pd.DataFrame(columns=["month", "borrows", "vs_average_pct"])
    avg = float(np.mean(trend.to_numpy()))
    top = trend.sort_values(ascending=False, kind="stable").head(n)
    return pd.DataFrame({
        "month": top.index.astype(str),
        "borrows": top.to_numpy(),
        "vs_average_pct": np.round((top.to_numpy() - avg) / avg * 100, 1),
    })


def member_activity(df, n=5):
    """Most active members."""
    return borrow_counts(df, "member").head(n).rename("borrows").reset_index()


def average_loan_days(df):
    """Mean number of days books are kept (returned loans only)."""
    returned = df.dropna(subset=["return_date"])
    if returned.empty:
        return 0.0
    days = (returned["return_date"] - returned["borrow_date"]).dt.days.to_numpy()
    return float(np.mean(days))


def filter_period(df, start, end):
    """Rows whose borrow_date lies in [start, end] (inclusive)."""
    return df[(df["borrow_date"] >= pd.Timestamp(start)) & (df["borrow_date"] <= pd.Timestamp(end))]


def compare_periods(df, start_a, end_a, start_b, end_b, by="category"):
    """Compare borrow counts per category (or title) between two periods."""
    a = borrow_counts(filter_period(df, start_a, end_a), by).rename("period_a")
    b = borrow_counts(filter_period(df, start_b, end_b), by).rename("period_b")
    out = pd.concat([a, b], axis=1).fillna(0).astype(int)
    if out.empty:
        return pd.DataFrame(columns=[by, "period_a", "period_b", "change", "change_pct"])
    out["change"] = out["period_b"] - out["period_a"]
    base = out["period_a"].to_numpy(dtype=float)
    out["change_pct"] = np.where(base > 0, np.round(out["change"].to_numpy() / np.where(base > 0, base, 1) * 100, 1), np.nan)
    return out.sort_values("period_b", ascending=False).rename_axis(by).reset_index()


def summary(df, total_members=None):
    """Headline numbers for the dashboard."""
    if df.empty:
        return {"total_borrows": 0, "active_loans": 0, "unique_books": 0, "unique_members": 0,
                "avg_per_member": 0.0, "avg_loan_days": 0.0,
                "most_borrowed": "-", "busiest_month": "-"}
    per_member = borrow_counts(df, "member_id").to_numpy()
    divisor = total_members if total_members else len(per_member)
    trend = monthly_trend(df)
    return {
        "total_borrows": int(len(df)),
        "active_loans": int((df["status"] == "Borrowed").sum()),
        "unique_books": int(df["book_id"].nunique()),
        "unique_members": int(df["member_id"].nunique()),
        "avg_per_member": round(float(per_member.sum()) / divisor, 2),
        "avg_loan_days": round(average_loan_days(df), 1),
        "most_borrowed": str(borrow_counts(df, "title").index[0]),
        "busiest_month": str(trend.idxmax()),
    }


def build_report(df, total_members=None):
    """Plain-text report shown in the Analytics tab."""
    s = summary(df, total_members)
    lines = [
        "LIBRARY USAGE REPORT", "=" * 36,
        f"Total borrows         : {s['total_borrows']}",
        f"Currently on loan     : {s['active_loans']}",
        f"Distinct books used   : {s['unique_books']}",
        f"Active borrowers      : {s['unique_members']}",
        f"Avg borrows / member  : {s['avg_per_member']}",
        f"Avg loan length       : {s['avg_loan_days']} days",
        f"Most borrowed book    : {s['most_borrowed']}",
        f"Busiest month         : {s['busiest_month']}",
        "", "Top 5 books", "-" * 36,
    ]
    for _, r in top_books(df).iterrows():
        lines.append(f"  {r['borrows']:>3}  {r['title']}")
    lines += ["", "Peak months", "-" * 36]
    for _, r in peak_periods(df).iterrows():
        lines.append(f"  {r['month']}  {r['borrows']:>3} borrows  ({r['vs_average_pct']:+.1f}% vs avg)")
    lines += ["", "Most active members", "-" * 36]
    for _, r in member_activity(df).iterrows():
        lines.append(f"  {r['borrows']:>3}  {r['member']}")
    return "\n".join(lines)
