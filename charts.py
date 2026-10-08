"""
charts.py - Matplotlib visual reports (user-defined module 4).

Each function returns a matplotlib Figure, so the Tkinter app can embed it
and tests / scripts can save it with fig.savefig(...).
"""
from matplotlib.figure import Figure

import analytics as an


def _new_fig():
    return Figure(figsize=(7, 4.6), dpi=100, layout="constrained")


def _empty(fig, title):
    ax = fig.subplots()
    ax.set_title(title)
    ax.text(0.5, 0.5, "No data to display", ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()
    return fig


def top_books_chart(df, n=8):
    """Horizontal bar chart of the most borrowed books."""
    fig = _new_fig()
    data = an.top_books(df, n)
    if data.empty:
        return _empty(fig, "Most borrowed books")
    ax = fig.subplots()
    data = data.iloc[::-1]
    bars = ax.barh(data["title"], data["borrows"], color="#2f6f9f")
    ax.bar_label(bars, padding=3)
    ax.set_title(f"Top {len(data)} most borrowed books")
    ax.set_xlabel("Number of borrows")
    return fig


def monthly_trend_chart(df):
    """Line chart of borrows per month with the average marked."""
    fig = _new_fig()
    trend = an.monthly_trend(df)
    if trend.empty:
        return _empty(fig, "Monthly borrowing trend")
    ax = fig.subplots()
    labels = trend.index.astype(str)
    ax.plot(labels, trend.to_numpy(), marker="o", color="#c0562b")
    ax.axhline(trend.to_numpy().mean(), linestyle="--", color="grey", label="Monthly average")
    ax.set_title("Borrowing trend by month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Borrows")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def category_chart(df):
    """Pie chart of borrowing share per category."""
    fig = _new_fig()
    counts = an.borrow_counts(df, "category")
    if counts.empty:
        return _empty(fig, "Borrowing by category")
    ax = fig.subplots()
    ax.pie(counts.to_numpy(), labels=counts.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Share of borrows by category")
    return fig


def weekday_chart(df):
    """Bar chart showing which weekdays are busiest."""
    fig = _new_fig()
    if df.empty:
        return _empty(fig, "Borrowing by weekday")
    ax = fig.subplots()
    act = an.weekday_activity(df)
    ax.bar([d[:3] for d in act.index], act.to_numpy(), color="#4a8f5b")
    ax.set_title("Borrows by day of week")
    ax.set_ylabel("Borrows")
    return fig


def period_comparison_chart(comparison, label_a="Period A", label_b="Period B"):
    """Grouped bar chart from analytics.compare_periods() output."""
    import numpy as np
    fig = _new_fig()
    if comparison.empty:
        return _empty(fig, "Period comparison")
    ax = fig.subplots()
    x = np.arange(len(comparison))
    w = 0.38
    ax.bar(x - w / 2, comparison["period_a"], w, label=label_a, color="#7a9cc6")
    ax.bar(x + w / 2, comparison["period_b"], w, label=label_b, color="#e08a4b")
    ax.set_xticks(x, comparison.iloc[:, 0], rotation=30, ha="right")
    ax.set_ylabel("Borrows")
    ax.set_title("Borrowing comparison between two periods")
    ax.legend()
    return fig


CHARTS = {
    "Top borrowed books": top_books_chart,
    "Monthly trend": monthly_trend_chart,
    "Category share": category_chart,
    "Weekday activity": weekday_chart,
}
