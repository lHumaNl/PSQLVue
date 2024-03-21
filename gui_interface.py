import io
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
        self.context_menu = tk.Menu(root, tearoff=0)
        self.query_input = tk.Text(self.root, height=10)
        self.autocommit_var = tk.BooleanVar(value=False)
        self.autocommit_checkbox = tk.Checkbutton(self.root, text="Autocommit", variable=self.autocommit_var)
        self.execute_button = tk.Button(self.root, text="Execute", command=self.__execute_query)
        self.export_button = tk.Button(self.root, text="Export Data", command=self.__export_data)
        self.all_data_var = tk.BooleanVar(value=False)
        self.all_data_checkbox = tk.Checkbutton(self.root, text="Export all data", variable=self.all_data_var)
        self.tree_frame = tk.Frame(self.root)
        self.tree_scroll = tk.Scrollbar(self.tree_frame)
        self.info_label = tk.Label(self.root, text="Loaded rows: 0")
        self.descr_buffer_label = tk.Label(self.root,
                                           text="* If data from the clipboard does not paste into the SQL query "
                                                "input field, try changing the keyboard layout and "
                                                "try pasting the data again.")
        self.result_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set, selectmode="extended")

        self.__setup_ui()

    @staticmethod
    def __show_context_menu(event, menu):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def __copy_selected_result(self):
        selected_items = self.result_tree.selection()
        result_text = ""
        for item in selected_items:
            item_text = self.result_tree.item(item, 'values')
            result_text += ", ".join(item_text) + "\n"
        self.root.clipboard_clear()
        self.root.clipboard_append(result_text)

    def __setup_ui(self):
        query_input_context_menu = tk.Menu(self.root, tearoff=0)
        query_input_context_menu.add_command(label="Copy", command=lambda: self.query_input.event_generate('<<Copy>>'))
        query_input_context_menu.add_command(label="Cut", command=lambda: self.query_input.event_generate('<<Cut>>'))
        query_input_context_menu.add_command(label="Paste",
                                             command=lambda: self.query_input.event_generate('<<Paste>>'))

        result_tree_context_menu = tk.Menu(self.root, tearoff=0)
        result_tree_context_menu.add_command(label="Copy", command=self.__copy_selected_result)

        self.query_input.bind("<Button-3>", lambda event: self.__show_context_menu(event, query_input_context_menu))
        self.result_tree.bind("<Button-3>", lambda event: self.__show_context_menu(event, result_tree_context_menu))

        self.query_input.pack(fill=tk.X, padx=5, pady=5)
        self.descr_buffer_label.pack(anchor='w', padx=3)
        self.execute_button.pack(pady=5)
        self.autocommit_checkbox.pack(pady=5)
        self.export_button.pack(pady=5)
        self.all_data_checkbox.pack(pady=5)

        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_label.pack(padx=5, pady=5)

        self.tree_scroll.config(command=self.result_tree.yview)
        self.result_tree.pack(fill=tk.BOTH, expand=True)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.result_tree.bind('<MouseWheel>', self.__on_motion)

    def __on_motion(self, event):
        if self.result_tree.yview()[1] == 1.0:
            self.__next_page()

    def __next_page(self):
        if self.loaded_rows < self.total_rows:
            new_data = self.psql_connection.fetch_data(
                self.current_query,
                is_autocommit=self.autocommit_var.get(),
                offset=self.loaded_rows,
                limit=self.rows_per_page
            )

            if isinstance(new_data, pd.DataFrame) and not new_data.empty:
                self.result_df = pd.concat([self.result_df, new_data], ignore_index=True)
                self.__update_table(load_more=True)

    def __execute_query(self):
        query = self.query_input.get("1.0", tk.END).strip()
        if not query:
            messagebox.showinfo("Info", "Please enter a query to execute.")
            return

        self.current_query = query
        is_autocommit = self.autocommit_var.get()

        self.total_rows = self.psql_connection.fetch_data(query, is_autocommit=is_autocommit, count_only=True)
        if isinstance(self.total_rows, str):
            messagebox.showerror("Error", self.total_rows)
            return

        self.loaded_rows = 0

        result = self.psql_connection.fetch_data(query, is_autocommit=is_autocommit, limit=100, offset=0)

        if isinstance(result, pd.DataFrame):
            self.result_df = result
            self.current_page = 0
            self.loaded_rows = 0
            self.result_tree.yview_moveto(0)
            for i in self.result_tree.get_children():
                self.result_tree.delete(i)
            self.__update_table()
        elif isinstance(result, str):
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Result", "The query executed successfully but returned no data.")

    def __update_table(self, load_more=False):
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

            self.info_label.config(text=f"Loaded rows: {self.loaded_rows}/{self.total_rows}")

    def __export_data(self):
        if not hasattr(self, 'result_df') or self.result_df is None or self.result_df.empty:
            messagebox.showerror("Error", "Nothing to export!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", '*.csv')],
            title="Save data as"
        )

        if not file_path:
            return

        if self.all_data_var.get():
            dialog = _ExportDialog(self.root, "Export Parameters")
            if not hasattr(dialog, 'result'):
                messagebox.showerror("Export", "Export config is not set.")
                return

            file_size, file_rows, row_limit, row_offset = dialog.result
            download_all_data = row_limit is None and row_offset is None

            all_data = self.psql_connection.fetch_data(self.current_query, is_autocommit=False, offset=row_offset,
                                                       limit=row_limit, all_data=download_all_data)
        else:
            if self.result_df.empty:
                messagebox.showerror("Export", "No data to export.")
                return
            else:
                self.result_df.to_csv(file_path, index=False)
                messagebox.showinfo("Export", f"Data successfully exported.")
                return

        if all_data.empty:
            messagebox.showerror("Export", "No data to export.")
            return

        if file_size is None and file_rows is None:
            all_data.to_csv(file_path, index=False)
            messagebox.showinfo("Export", "Data successfully exported.")
            return
        elif file_size is not None:
            self.__export_by_file_size(all_data, file_size, file_path)
        else:
            self.__export_by_file_rows(all_data, file_rows, file_path)

    @staticmethod
    def __export_by_file_rows(all_data: DataFrame, file_rows: int, file_path: str):
        total_rows = len(all_data)
        estimated_file_count = int(total_rows // file_rows + (1 if total_rows % file_rows else 0))

        if estimated_file_count > 1:
            proceed = messagebox.askokcancel("Export Confirmation",
                                             f"Will be created {estimated_file_count} files. Proceed?")
            if not proceed:
                return

        part_number = 1
        for start in range(0, total_rows, file_rows):
            end = min(start + file_rows, total_rows)
            part_df = all_data.iloc[start:end]

            part_file_path = f"{file_path.rsplit('.', 1)[0]}_part{part_number}.csv" if part_number > 1 else file_path
            part_df.to_csv(part_file_path, index=False)

            part_number += 1

        messagebox.showinfo("Export", f"Data successfully exported." + (
            f" Created {part_number - 1} file(s)." if part_number > 1 else ""))

    @staticmethod
    def __export_by_file_size(all_data: DataFrame, file_size: float, file_path: str):
        header = all_data.iloc[:0].to_csv(index=False)

        max_size_bytes = file_size * 1024 * 1024
        part_number = 1

        buffer = io.StringIO()
        all_data.to_csv(buffer, index=False)
        total_data_size = buffer.tell()
        buffer.seek(0)
        current_size = 0

        estimated_file_count = int(total_data_size // max_size_bytes + (1 if total_data_size % max_size_bytes else 0))

        if estimated_file_count > 1:
            proceed = messagebox.askokcancel("Export Confirmation",
                                             f"Will be created {estimated_file_count} files. Proceed?")
            if not proceed:
                return

        part_file_path = file_path

        is_first_line = False
        for line in buffer:
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > max_size_bytes and max_size_bytes > 0:
                is_first_line = True
                part_number += 1
                part_file_path = f"{file_path.rsplit('.', 1)[0]}_part{part_number}.csv"
                current_size = 0

            with open(part_file_path, 'a', encoding='utf-8', newline='') as file:
                if is_first_line:
                    file.write(header + line)
                else:
                    file.write(line)

                is_first_line = False
                current_size += line_size

        messagebox.showinfo("Export", f"Data successfully exported." + (
            f" Created {part_number} file(s)." if part_number > 1 else ""))


class _ExportDialog(simpledialog.Dialog):
    def body(self, master):
        self.resizable(width=False, height=False)

        self.__file_size_var = tk.DoubleVar(value=0)
        self.__file_rows_var = tk.IntVar(value=0)
        self.__row_limit_var = tk.IntVar(value=0)
        self.__row_offset_var = tk.IntVar(value=0)

        self.__export_choice_var = tk.StringVar(value="size")

        tk.Radiobutton(master, variable=self.__export_choice_var, value="size",
                       command=self.__toggle_export_choice).grid(row=0, column=0, sticky='w')
        tk.Label(master, text="File size limit in MB (0 for unlimited):").grid(row=0, column=1, sticky='w')
        self.__file_size_entry = tk.Entry(master, textvariable=self.__file_size_var)
        self.__file_size_entry.grid(row=0, column=2, sticky='e')

        tk.Radiobutton(master, variable=self.__export_choice_var, value="rows",
                       command=self.__toggle_export_choice).grid(row=1, column=0, sticky='w')
        tk.Label(master, text="Number of rows per file (0 for unlimited):").grid(row=1, column=1, sticky='w')
        self.__file_rows_entry = tk.Entry(master, textvariable=self.__file_rows_var, state='disabled')
        self.__file_rows_entry.grid(row=1, column=2, sticky='e')

        tk.Label(master, text="Number of rows to fetch (0 for no limit):").grid(row=2, column=1, sticky='w')
        tk.Entry(master, textvariable=self.__row_limit_var).grid(row=2, column=2, sticky='e')

        tk.Label(master, text="Row offset (0 to start from the beginning):").grid(row=3, column=1, sticky='w')
        tk.Entry(master, textvariable=self.__row_offset_var).grid(row=3, column=2, sticky='e')

        self.__toggle_export_choice()

    def __toggle_export_choice(self):
        if self.__export_choice_var.get() == "size":
            self.__file_size_entry.config(state='normal')
            self.__file_rows_entry.config(state='disabled')
        else:
            self.__file_size_entry.config(state='disabled')
            self.__file_rows_entry.config(state='normal')

    def apply(self):
        file_size = self.__file_size_var.get() if self.__export_choice_var.get() == "size" else None
        file_rows = self.__file_rows_var.get() if self.__export_choice_var.get() == "rows" else None
        row_limit = self.__row_limit_var.get() if self.__row_limit_var.get() != 0 else None
        row_offset = self.__row_offset_var.get() if self.__row_offset_var.get() != 0 else None
        self.result = (file_size, file_rows, row_limit, row_offset)
