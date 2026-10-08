
"""
app.py - Library Borrowing Analyzer (Tkinter GUI, main entry point).

Run:  python app.py

Student : JAINAM HIREN PATEL
Enrol.  : IU2441230395
Project : P12 - Library: borrowing transactions, trends and usage analysis
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd  # type: ignore[import-not-found]
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # pyright: ignore[reportMissingModuleSource]
except ImportError:  # pragma: no cover - optional runtime dependency
    FigureCanvasTkAgg = None

import analytics as an
import charts
import sample_data
import validators as v
from data_manager import LibraryData, LibraryError

TODAY = pd.Timestamp.today().strftime("%Y-%m-%d")


def make_tree(parent, columns, widths=None):
    """Create a Treeview with a vertical scrollbar; returns the tree."""
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=6, pady=6)
    tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
    for i, col in enumerate(columns):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=(widths[i] if widths else 110), anchor="w")
    bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    tree.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    return tree


def fill_tree(tree, df, columns):
    """Replace all rows of a Treeview with the given DataFrame."""
    tree.delete(*tree.get_children())
    for _, row in df.iterrows():
        values = []
        for c in columns:
            val = row[c]
            if isinstance(val, pd.Timestamp):
                val = val.strftime("%Y-%m-%d")
            elif pd.isna(val):
                val = ""
            values.append(val)
        tree.insert("", "end", values=values)


def labeled_entry(parent, label, row, col, width=22, default=""):
    ttk.Label(parent, text=label).grid(row=row, column=col, sticky="e", padx=4, pady=3)
    var = tk.StringVar(value=default)
    ttk.Entry(parent, textvariable=var, width=width).grid(row=row, column=col + 1, sticky="w", padx=4, pady=3)
    return var


class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Library Borrowing Analyzer  -  Jainam Hiren Patel (IU2441230395)")
        self.geometry("1150x700")
        try:
            self.data = LibraryData("data")
        except LibraryError as exc:
            messagebox.showerror("Startup error", str(exc))
            self.data = LibraryData("data_fallback")

        self._build_menu()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self._build_books_tab()
        self._build_members_tab()
        self._build_transactions_tab()
        self._build_analytics_tab()
        self.refresh_all()

    # --------------------------------------------------------------- helpers
    def guard(self, func, *args):
        """Run func; show friendly dialogs for expected errors."""
        try:
            return func(*args)
        except (v.ValidationError, LibraryError) as exc:
            messagebox.showwarning("Cannot complete action", str(exc))
        except Exception as exc:  # last-resort safety net
            messagebox.showerror("Unexpected error", f"{type(exc).__name__}: {exc}")
        return None

    def _build_menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Load sample data", command=self.load_sample)
        file_menu.add_command(label="Export transactions to CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)

    def load_sample(self):
        if messagebox.askyesno("Load sample data", "This replaces all current records. Continue?"):
            self.guard(sample_data.generate, self.data)
            self.refresh_all()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.guard(lambda: self.data.transactions_view().to_csv(path, index=False))

    def refresh_all(self):
        self.refresh_books()
        self.refresh_members()
        self.refresh_transactions()
        self.refresh_analytics()

    @staticmethod
    def selected_value(tree, index=0):
        sel = tree.selection()
        return tree.item(sel[0])["values"][index] if sel else None

    # ----------------------------------------------------------------- books
    def _build_books_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="Books")
        top = ttk.Frame(tab)
        top.pack(fill="x", padx=6, pady=4)
        self.book_search = tk.StringVar()
        ttk.Label(top, text="Search:").pack(side="left")
        ttk.Entry(top, textvariable=self.book_search, width=30).pack(side="left", padx=4)
        ttk.Button(top, text="Search", command=self.refresh_books).pack(side="left")
        ttk.Button(top, text="Clear", command=lambda: (self.book_search.set(""), self.refresh_books())).pack(side="left", padx=4)

        self.book_cols = ["book_id", "title", "author", "category", "copies", "available"]
        self.book_tree = make_tree(tab, self.book_cols, [70, 300, 200, 110, 70, 80])
        self.book_tree.bind("<<TreeviewSelect>>", self._on_book_select)

        form = ttk.LabelFrame(tab, text="Book details")
        form.pack(fill="x", padx=6, pady=6)
        self.b_title = labeled_entry(form, "Title", 0, 0, 36)
        self.b_author = labeled_entry(form, "Author", 0, 2, 26)
        self.b_cat = labeled_entry(form, "Category", 1, 0, 20)
        self.b_copies = labeled_entry(form, "Copies", 1, 2, 8, "1")
        btns = ttk.Frame(form)
        btns.grid(row=2, column=0, columnspan=4, pady=4)
        ttk.Button(btns, text="Add", command=self.add_book).pack(side="left", padx=4)
        ttk.Button(btns, text="Update selected", command=self.update_book).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete selected", command=self.delete_book).pack(side="left", padx=4)

    def refresh_books(self):
        df = self.data.search_books(self.book_search.get())
        fill_tree(self.book_tree, df, self.book_cols)
        self._refresh_combos()

    def _on_book_select(self, _event=None):
        sel = self.book_tree.selection()
        if sel:
            _, title, author, cat, copies, _ = self.book_tree.item(sel[0])["values"]
            for var, val in ((self.b_title, title), (self.b_author, author), (self.b_cat, cat), (self.b_copies, copies)):
                var.set(val)

    def add_book(self):
        if self.guard(lambda: self.data.add_book(self.b_title.get(), self.b_author.get(), self.b_cat.get(), self.b_copies.get())):
            self.refresh_all()

    def update_book(self):
        bid = self.selected_value(self.book_tree)
        if not bid:
            return messagebox.showinfo("Select a book", "Click a book in the table first.")
        self.guard(self.data.update_book, bid, self.b_title.get(), self.b_author.get(), self.b_cat.get(), self.b_copies.get())
        self.refresh_all()

    def delete_book(self):
        bid = self.selected_value(self.book_tree)
        if bid and messagebox.askyesno("Delete", f"Delete book {bid}?"):
            self.guard(self.data.delete_book, bid)
            self.refresh_all()

    # --------------------------------------------------------------- members
    def _build_members_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="Members")
        top = ttk.Frame(tab)
        top.pack(fill="x", padx=6, pady=4)
        self.member_search = tk.StringVar()
        ttk.Label(top, text="Search:").pack(side="left")
        ttk.Entry(top, textvariable=self.member_search, width=30).pack(side="left", padx=4)
        ttk.Button(top, text="Search", command=self.refresh_members).pack(side="left")
        ttk.Button(top, text="Clear", command=lambda: (self.member_search.set(""), self.refresh_members())).pack(side="left", padx=4)

        self.member_cols = ["member_id", "name", "email"]
        self.member_tree = make_tree(tab, self.member_cols, [90, 260, 280])
        self.member_tree.bind("<<TreeviewSelect>>", self._on_member_select)

        form = ttk.LabelFrame(tab, text="Member details")
        form.pack(fill="x", padx=6, pady=6)
        self.m_name = labeled_entry(form, "Name", 0, 0, 30)
        self.m_email = labeled_entry(form, "Email (optional)", 0, 2, 30)
        btns = ttk.Frame(form)
        btns.grid(row=1, column=0, columnspan=4, pady=4)
        ttk.Button(btns, text="Add", command=self.add_member).pack(side="left", padx=4)
        ttk.Button(btns, text="Update selected", command=self.update_member).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete selected", command=self.delete_member).pack(side="left", padx=4)

    def refresh_members(self):
        fill_tree(self.member_tree, self.data.search_members(self.member_search.get()), self.member_cols)
        self._refresh_combos()

    def _on_member_select(self, _event=None):
        sel = self.member_tree.selection()
        if sel:
            _, name, email = self.member_tree.item(sel[0])["values"]
            self.m_name.set(name)
            self.m_email.set(email)

    def add_member(self):
        if self.guard(lambda: self.data.add_member(self.m_name.get(), self.m_email.get())):
            self.refresh_all()

    def update_member(self):
        mid = self.selected_value(self.member_tree)
        if not mid:
            return messagebox.showinfo("Select a member", "Click a member in the table first.")
        self.guard(self.data.update_member, mid, self.m_name.get(), self.m_email.get())
        self.refresh_all()

    def delete_member(self):
        mid = self.selected_value(self.member_tree)
        if mid and messagebox.askyesno("Delete", f"Delete member {mid}?"):
            self.guard(self.data.delete_member, mid)
            self.refresh_all()

    # ---------------------------------------------------------- transactions
    def _build_transactions_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="Transactions")

        act = ttk.LabelFrame(tab, text="Borrow / return")
        act.pack(fill="x", padx=6, pady=4)
        ttk.Label(act, text="Member").grid(row=0, column=0, padx=4, pady=3)
        self.t_member = ttk.Combobox(act, width=28, state="readonly")
        self.t_member.grid(row=0, column=1, padx=4)
        ttk.Label(act, text="Book").grid(row=0, column=2, padx=4)
        self.t_book = ttk.Combobox(act, width=40, state="readonly")
        self.t_book.grid(row=0, column=3, padx=4)
        self.t_date = labeled_entry(act, "Date (YYYY-MM-DD)", 0, 4, 12, TODAY)
        ttk.Button(act, text="Borrow", command=self.borrow).grid(row=1, column=1, pady=4)
        ttk.Button(act, text="Return selected", command=self.return_selected).grid(row=1, column=2, pady=4)
        ttk.Button(act, text="Delete selected", command=self.delete_txn).grid(row=1, column=3, pady=4)

        flt = ttk.LabelFrame(tab, text="Search / filter")
        flt.pack(fill="x", padx=6, pady=4)
        self.f_member = ttk.Combobox(flt, width=26, state="readonly")
        self.f_member.grid(row=0, column=0, padx=4, pady=3)
        self.f_book = ttk.Combobox(flt, width=36, state="readonly")
        self.f_book.grid(row=0, column=1, padx=4)
        self.f_status = ttk.Combobox(flt, width=10, state="readonly", values=["All", "Borrowed", "Returned"])
        self.f_status.current(0)
        self.f_status.grid(row=0, column=2, padx=4)
        self.f_from = labeled_entry(flt, "From", 0, 3, 11)
        self.f_to = labeled_entry(flt, "To", 0, 5, 11)
        ttk.Button(flt, text="Apply", command=self.refresh_transactions).grid(row=0, column=7, padx=4)
        ttk.Button(flt, text="Reset", command=self.reset_filters).grid(row=0, column=8, padx=4)

        self.txn_cols = ["txn_id", "member", "title", "category", "borrow_date", "return_date", "status"]
        self.txn_tree = make_tree(tab, self.txn_cols, [60, 170, 280, 100, 100, 100, 80])

    def _refresh_combos(self):
        if not hasattr(self, "f_book"):
            return
        members = ["All"] + [f"{r.member_id} - {r.name}" for r in self.data.members.itertuples()]
        books = ["All"] + [f"{r.book_id} - {r.title}" for r in self.data.books.itertuples()]
        self.f_member["values"], self.f_book["values"] = members, books
        self.t_member["values"], self.t_book["values"] = members[1:], books[1:]
        for box in (self.f_member, self.f_book):
            if not box.get():
                box.current(0)

    @staticmethod
    def _id_of(combo):
        text = combo.get()
        return None if not text or text == "All" else text.split(" - ")[0]

    def reset_filters(self):
        self.f_member.current(0)
        self.f_book.current(0)
        self.f_status.current(0)
        self.f_from.set("")
        self.f_to.set("")
        self.refresh_transactions()

    def refresh_transactions(self):
        df = self.guard(lambda: self.data.search_transactions(
            self._id_of(self.f_member), self._id_of(self.f_book), self.f_status.get(),
            self.f_from.get(), self.f_to.get()))
        if df is not None:
            fill_tree(self.txn_tree, df, self.txn_cols)

    def borrow(self):
        mid, bid = self._id_of(self.t_member), self._id_of(self.t_book)
        if not mid or not bid:
            return messagebox.showinfo("Missing selection", "Choose both a member and a book.")
        if self.guard(self.data.borrow, mid, bid, self.t_date.get()):
            self.refresh_all()

    def return_selected(self):
        tid = self.selected_value(self.txn_tree)
        if tid is None:
            return messagebox.showinfo("Select a row", "Click a transaction first.")
        self.guard(self.data.return_book, int(tid), self.t_date.get())
        self.refresh_all()

    def delete_txn(self):
        tid = self.selected_value(self.txn_tree)
        if tid is not None and messagebox.askyesno("Delete", f"Delete transaction {tid}?"):
            self.guard(self.data.delete_transaction, int(tid))
            self.refresh_all()

    # ------------------------------------------------------------- analytics
    def _build_analytics_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="Analytics")
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.report = tk.Text(left, width=44, height=26, font=("Consolas", 9), state="disabled")
        self.report.pack(fill="y")

        ctl = ttk.LabelFrame(left, text="Chart")
        ctl.pack(fill="x", pady=6)
        self.chart_choice = ttk.Combobox(ctl, state="readonly", width=24,
                                         values=list(charts.CHARTS) + ["Compare two periods"])
        self.chart_choice.current(0)
        self.chart_choice.grid(row=0, column=0, columnspan=2, padx=4, pady=3)
        self.pa_s = labeled_entry(ctl, "A from", 1, 0, 11)
        self.pa_e = labeled_entry(ctl, "A to", 2, 0, 11)
        self.pb_s = labeled_entry(ctl, "B from", 3, 0, 11)
        self.pb_e = labeled_entry(ctl, "B to", 4, 0, 11)
        ttk.Button(ctl, text="Show chart", command=self.show_chart).grid(row=5, column=0, pady=4)
        ttk.Button(ctl, text="Save PNG", command=self.save_chart).grid(row=5, column=1, pady=4)

        self.chart_frame = ttk.Frame(tab)
        self.chart_frame.pack(side="right", fill="both", expand=True, padx=6, pady=6)
        self.current_fig = None
        self.canvas = None

    def refresh_analytics(self):
        df = self.data.transactions_view()
        text = an.build_report(df, total_members=len(self.data.members) or None)
        self.report.config(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.config(state="disabled")
        self.show_chart(quiet=True)

    def show_chart(self, quiet=False):
        df = self.data.transactions_view()
        choice = self.chart_choice.get()
        try:
            if choice == "Compare two periods":
                if not all(x.get().strip() for x in (self.pa_s, self.pa_e, self.pb_s, self.pb_e)):
                    if quiet:
                        return
                    raise v.ValidationError("Fill in all four dates for period A and period B.")
                a_s, a_e = v.parse_date(self.pa_s.get(), "A from"), v.parse_date(self.pa_e.get(), "A to")
                b_s, b_e = v.parse_date(self.pb_s.get(), "B from"), v.parse_date(self.pb_e.get(), "B to")
                v.validate_range(a_s, a_e, "Period A")
                v.validate_range(b_s, b_e, "Period B")
                comp = an.compare_periods(df, a_s, a_e, b_s, b_e)
                fig = charts.period_comparison_chart(
                    comp, f"A: {a_s:%Y-%m-%d} to {a_e:%Y-%m-%d}", f"B: {b_s:%Y-%m-%d} to {b_e:%Y-%m-%d}")
            else:
                fig = charts.CHARTS[choice](df)
        except v.ValidationError as exc:
            messagebox.showwarning("Check input", str(exc))
            return
        self.current_fig = fig
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def save_chart(self):
        if self.current_fig is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            self.guard(self.current_fig.savefig, path, dpi=150)


if __name__ == "__main__":
    LibraryApp().mainloop()
