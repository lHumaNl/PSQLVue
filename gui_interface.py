import io
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
from pandas import DataFrame


class PsqlGuiApp:
    result_df: DataFrame

    def __init__(self, root, psql_connection):
        self.row_limit = None
        self.current_query = None
        self.root = root
        self.psql_connection = psql_connection
        self.current_page = 0
        self.rows_per_page = 100
        self.total_rows = 0
        self.loaded_rows = 0

        self.root.title("PSQLVue UI Executor")
        self.query_input = tk.Text(self.root, height=10)
        self.autocommit_var = tk.BooleanVar(value=False)
        self.autocommit_checkbox = tk.Checkbutton(self.root, text="Autocommit", variable=self.autocommit_var)
        self.execute_button = tk.Button(self.root, text="Execute", command=self.execute_query)
        self.export_button = tk.Button(self.root, text="Export Data", command=self.export_data)
        self.all_data_var = tk.BooleanVar(value=False)
        self.all_data_checkbox = tk.Checkbutton(self.root, text="Export all data", variable=self.all_data_var)
        self.tree_frame = tk.Frame(self.root)
        self.tree_scroll = tk.Scrollbar(self.tree_frame)
        self.info_label = tk.Label(self.root, text="Loaded rows: 0")
        self.result_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set, selectmode="extended")

        self.setup_ui()

    def setup_ui(self):

        self.query_input.pack(fill=tk.X, padx=5, pady=5)
        self.autocommit_checkbox.pack(anchor='w', padx=5)
        self.execute_button.pack(pady=5)
        self.export_button.pack(pady=5)
        self.all_data_checkbox.pack(anchor='w', padx=5)

        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_label.pack(padx=5, pady=5)

        self.tree_scroll.config(command=self.result_tree.yview)
        self.result_tree.pack(fill=tk.BOTH, expand=True)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.result_tree.bind('<MouseWheel>', self.on_motion)

    def on_motion(self, event):
        if self.result_tree.yview()[1] == 1.0 and self.loaded_rows < self.total_rows:
            self.next_page()

    def execute_query(self):
        query = self.query_input.get("1.0", tk.END).strip()
        self.current_query = query
        if not query:
            messagebox.showinfo("Info", "Please enter a query to execute.")
            return

        is_autocommit = self.autocommit_var.get()
        result = self.psql_connection.fetch_data(query, is_autocommit=is_autocommit, limit=100, offset=0)

        if isinstance(result, pd.DataFrame):
            self.result_df = result
            self.total_rows = len(self.result_df)
            self.current_page = 0
            self.loaded_rows = 0
            self.result_tree.yview_moveto(0)
            for i in self.result_tree.get_children():
                self.result_tree.delete(i)
            self.update_table()
        elif isinstance(result, str):
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Result", "The query executed successfully but returned no data.")

    def update_table(self, load_more=False):
        if self.result_df is not None and not self.result_df.empty:
            if not load_more:
                for i in self.result_tree.get_children():
                    self.result_tree.delete(i)

            start = self.loaded_rows
            end = start + self.rows_per_page
            page_df = self.result_df.iloc[start:end]
            page_df = page_df.reset_index()

            if not load_more or start == 0:
                self.result_tree["columns"] = list(page_df.columns)
                self.result_tree["show"] = "headings"
                for column in self.result_tree["columns"]:
                    self.result_tree.heading(column, text=column)
                    self.result_tree.column(column, width=100)

            for row in page_df.itertuples(index=False):
                self.result_tree.insert("", "end", values=row)
                self.loaded_rows += 1

            self.info_label.config(text=f"Loaded rows: {self.loaded_rows} из {self.total_rows}")

    def next_page(self):
        if self.loaded_rows < self.total_rows:
            self.update_table(load_more=True)

    def export_data(self):
        dialog = ExportDialog(self.root, "Export Parameters")
        if not hasattr(dialog, 'result'):
            return

        max_size_mb, row_limit, row_offset = dialog.result

        if row_limit is not None or row_offset is not None:
            all_data = False
        else:
            all_data = True

        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", '*.csv')],
            title="Save data as"
        )

        if not file_path:
            return

        base_path, extension = os.path.splitext(file_path)

        if self.all_data_var.get():
            all_data = self.psql_connection.fetch_data(self.current_query, is_autocommit=False, row_limit=row_limit,
                                                       row_offset=row_offset, all_data=all_data)
        else:
            all_data = self.result_df if hasattr(self, 'result_df') else pd.DataFrame()

        if all_data.empty:
            messagebox.showinfo("Export", "No data to export.")
            return

        max_size_bytes = max_size_mb * 1024 * 1024
        bytes_accumulated = 0
        part_number = 0
        for start in range(0, len(all_data), self.rows_per_page):
            end = start + self.rows_per_page
            part_df = all_data.iloc[start:end]

            buffer = io.StringIO()
            part_df.to_csv(buffer, index=False)
            part_data = buffer.getvalue().encode('utf-8')

            if (((bytes_accumulated + len(part_data)) > max_size_bytes) and max_size_bytes > 0) or part_number == 0:
                part_number += 1
                part_file_path = f"{base_path}_part{part_number}{extension}" if part_number > 1 else file_path
                bytes_accumulated = 0
            else:
                part_file_path = file_path

            with open(part_file_path, 'wb') as file:
                file.write(part_data)
                bytes_accumulated += len(part_data)

        messagebox.showinfo("Export", f"Data successfully exported in {part_number} file(s).")


class ExportDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Max file size in MB (0 for unlimited):").grid(row=0)
        tk.Label(master, text="Number of rows to fetch (0 for no limit):").grid(row=1)
        tk.Label(master, text="Row offset (0 to start from the beginning):").grid(row=2)

        self.__max_size_var = tk.IntVar(value=0)
        self.__row_limit_var = tk.IntVar(value=0)
        self.__row_offset_var = tk.IntVar(value=0)

        tk.Entry(master, textvariable=self.__max_size_var).grid(row=0, column=1)
        tk.Entry(master, textvariable=self.__row_limit_var).grid(row=1, column=1)
        tk.Entry(master, textvariable=self.__row_offset_var).grid(row=2, column=1)

    def apply(self):
        if self.__row_limit_var.get() == 0 and self.__row_limit_var.get() is not None:
            row_limit = None
        else:
            row_limit = self.__row_limit_var.get()

        if self.__row_offset_var.get() == 0 and self.__row_offset_var.get() is not None:
            row_offset = None
        else:
            row_offset = self.__row_offset_var.get()

        if self.__max_size_var.get() == 0 and self.__max_size_var.get() is not None:
            max_size = 0
        else:
            max_size = self.__max_size_var.get()

        self.result = (max_size, row_limit, row_offset)
