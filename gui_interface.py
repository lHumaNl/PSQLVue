import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
from pandas import DataFrame


class PsqlGuiApp:
    """
        A GUI application for executing SQL queries against a PostgreSQL database and managing the results.
    """

    def __init__(self, root, psql_connection):
        """
                Initializes the application's GUI components and sets up the database connection.

                Args:
                    root: The root Tkinter widget.
                    psql_connection (PsqlConnection): An instance of PsqlConnection to interact with the database.
        """
        self.__row_limit = None
        self.__current_query = None
        self.__root = root
        self.__psql_connection = psql_connection
        self.__current_page = 0
        self.__rows_per_page = 100
        self.__total_rows = 0
        self.__loaded_rows = 0
        self.__result_df = None

        self.__root.title("PSQLVue UI Executor")
        self.__context_menu = tk.Menu(root, tearoff=0)
        self.__query_input = tk.Text(self.__root, height=10, undo=True)
        self.__autocommit_var = tk.BooleanVar(value=False)
        self.__autocommit_checkbox = tk.Checkbutton(self.__root, text="Autocommit", variable=self.__autocommit_var)
        self.__execute_button = tk.Button(self.__root, text="Execute", command=self.__execute_query)
        self.__export_button = tk.Button(self.__root, text="Export Data", command=self.__export_data)
        self.__all_data_var = tk.BooleanVar(value=False)
        self.__all_data_checkbox = tk.Checkbutton(self.__root, text="Export all data", variable=self.__all_data_var)
        self.__tree_frame = tk.Frame(self.__root)
        self.__tree_scroll = tk.Scrollbar(self.__tree_frame)
        self.__info_label = tk.Label(self.__root, text="Loaded rows: 0")
        self.__descr_buffer_label = tk.Label(self.__root,
                                             text="* If data from the clipboard does not paste into the SQL query "
                                                  "input field, try changing the keyboard layout and "
                                                  "try pasting the data again.")
        self.__result_tree = ttk.Treeview(self.__tree_frame, yscrollcommand=self.__tree_scroll.set,
                                          selectmode="extended")

        self.__setup_ui()

    @staticmethod
    def __show_context_menu(event, menu):
        """
            Displays a context menu at the position of the mouse event.

            Args:
                event: The event object containing details about the mouse event.
                menu: The menu object to be displayed as a context menu.
        """
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def __copy_selected_result(self):
        """
            Copies the selected rows from the results table to the clipboard.
        """
        selected_items = self.__result_tree.selection()
        result_text = ""
        for item in selected_items:
            item_text = self.__result_tree.item(item, 'values')
            result_text += ", ".join(item_text) + "\n"
        self.__root.clipboard_clear()
        self.__root.clipboard_append(result_text)

    def __setup_ui(self):
        """
            Sets up the user interface components and their layout within the main application window.
        """
        query_input_context_menu = tk.Menu(self.__root, tearoff=0)
        query_input_context_menu.add_command(label="Copy",
                                             command=lambda: self.__query_input.event_generate('<<Copy>>'))
        query_input_context_menu.add_command(label="Cut", command=lambda: self.__query_input.event_generate('<<Cut>>'))
        query_input_context_menu.add_command(label="Paste",
                                             command=lambda: self.__query_input.event_generate('<<Paste>>'))

        result_tree_context_menu = tk.Menu(self.__root, tearoff=0)
        result_tree_context_menu.add_command(label="Copy", command=self.__copy_selected_result)

        self.__query_input.bind("<Button-3>", lambda event: self.__show_context_menu(event, query_input_context_menu))
        self.__result_tree.bind("<Button-3>", lambda event: self.__show_context_menu(event, result_tree_context_menu))

        self.__root.bind_all("<Control-z>", lambda event: self.__query_input.edit_undo())
        self.__root.bind_all("<Control-y>", lambda event: self.__query_input.edit_redo())
        self.__root.bind_all("<Control-c>", lambda event: self.__query_input.event_generate('<<Copy>>'))
        self.__root.bind_all("<Control-x>", lambda event: self.__query_input.event_generate('<<Cut>>'))

        self.__query_input.pack(fill=tk.X, padx=5, pady=5)
        self.__descr_buffer_label.pack(anchor='w', padx=3)
        self.__execute_button.pack(pady=5)
        self.__autocommit_checkbox.pack(pady=5)
        self.__export_button.pack(pady=5)
        self.__all_data_checkbox.pack(pady=5)

        self.__tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.__tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.__info_label.pack(padx=5, pady=5)

        self.__tree_scroll.config(command=self.__result_tree.yview)
        self.__result_tree.pack(fill=tk.BOTH, expand=True)

        self.__root.grid_rowconfigure(0, weight=1)
        self.__root.grid_columnconfigure(0, weight=1)

        self.__result_tree.bind('<MouseWheel>', self.__on_motion)

    def __on_motion(self, event):
        """
            Handles mouse wheel motion to load more data when the end of the scrollbar is reached.

            Args:
                event: The event object containing details about the mouse wheel motion.
        """
        if self.__result_tree.yview()[1] == 1.0:
            self.__next_page()

    def __next_page(self):
        """
            Fetches the next page of data based on the current query, pagination settings, and updates the UI accordingly.
        """
        if self.__loaded_rows < self.__total_rows:
            new_data = self.__psql_connection.fetch_data(
                self.__current_query,
                is_autocommit=self.__autocommit_var.get(),
                offset=self.__loaded_rows,
                limit=self.__rows_per_page
            )

            if isinstance(new_data, pd.DataFrame) and not new_data.empty:
                self.__result_df = pd.concat([self.__result_df, new_data], ignore_index=True)
                self.__update_table(self.__rows_per_page, load_more=True)

    def __execute_query(self):
        """
                Executes the SQL query specified in the query input box and displays the results.
        """
        query = self.__query_input.get("1.0", tk.END).strip()
        if not query:
            messagebox.showinfo("Info", "Please enter a query to execute.")
            return

        self.__current_query = query

        self.__total_rows = self.__psql_connection.fetch_data(query, count_only=True)

        if isinstance(self.__total_rows, str):
            messagebox.showerror("Error", self.__total_rows)
            return
        elif isinstance(self.__total_rows, tuple):
            result = self.__total_rows[1]
            self.__total_rows = self.__total_rows[0]
            total_rows = self.__total_rows
        else:
            self.__loaded_rows = 0
            result = self.__psql_connection.fetch_data(query, is_autocommit=self.__autocommit_var.get(), limit=100,
                                                       offset=0)
            total_rows = self.__rows_per_page

        if isinstance(result, pd.DataFrame):
            self.__result_df = result
            self.__current_page = 0
            self.__loaded_rows = 0
            self.__result_tree.yview_moveto(0)
            for i in self.__result_tree.get_children():
                self.__result_tree.delete(i)
            self.__update_table(loaded_rows=total_rows)
        elif isinstance(result, str):
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Result", "The query executed successfully but returned no data.")

    def __update_table(self, loaded_rows: int, load_more=False):
        if self.__result_df is not None and not self.__result_df.empty:
            if not load_more:
                for i in self.__result_tree.get_children():
                    self.__result_tree.delete(i)

            start = self.__loaded_rows
            end = start + loaded_rows
            page_df = self.__result_df.iloc[start:end]
            page_df = page_df.reset_index()

            if not load_more or start == 0:
                self.__result_tree["columns"] = list(page_df.columns)
                self.__result_tree["show"] = "headings"
                for column in self.__result_tree["columns"]:
                    self.__result_tree.heading(column, text=column)
                    self.__result_tree.column(column, width=100)

            for row in page_df.itertuples(index=False):
                self.__result_tree.insert("", "end", values=row)
                self.__loaded_rows += 1

            self.__info_label.config(text=f"Loaded rows: {self.__loaded_rows}/{self.__total_rows}")

    def __export_data(self):
        """
            Initiates the export process for the currently loaded data or all data based on user selection.
        """
        if self.__result_df is None or self.__result_df.empty:
            messagebox.showerror("Error", "Nothing to export!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", '*.csv')],
            title="Save data as"
        )

        if not file_path:
            return

        if self.__all_data_var.get():
            dialog = _ExportDialog(self.__root, "Export Parameters")
            if not hasattr(dialog, 'result'):
                messagebox.showerror("Export", "Export config is not set.")
                return

            file_size, file_rows, row_limit, row_offset = dialog.result
            download_all_data = row_limit is None and row_offset is None

            all_data = self.__psql_connection.fetch_data(self.__current_query, is_autocommit=self.__autocommit_var,
                                                         offset=row_offset, limit=row_limit, all_data=download_all_data)
        else:
            if self.__result_df.empty:
                messagebox.showerror("Export", "No data to export.")
                return
            else:
                self.__result_df.to_csv(file_path, index=False)
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
        """
            Splits and exports the data into multiple CSV files based on the specified number of rows per file.

            Args:
                all_data (DataFrame): The DataFrame containing all the data to be exported.
                file_rows (int): The maximum number of rows per file.
                file_path (str): The base file path for the exported CSV files.
        """
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
        """
            Splits and exports the data into multiple CSV files based on the specified maximum file size.

            Args:
                all_data (DataFrame): The DataFrame containing all the data to be exported.
                file_size (float): The maximum file size in megabytes.
                file_path (str): The base file path for the exported CSV files.
        """
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
    """
        A dialog window for configuring the parameters of the data export process.

        Inherits from simpledialog.Dialog, providing a modal dialog with input fields for export configuration.
    """

    def body(self, master):
        """
                Creates the dialog body, including input fields for file size limit, number of rows per file, total rows to fetch, and row offset.

                Args:
                    master: The parent window for this dialog.
        """
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
        """
                Toggles the state of the input fields based on the selected export option (by file size or by number of rows).
        """
        if self.__export_choice_var.get() == "size":
            self.__file_size_entry.config(state='normal')
            self.__file_rows_entry.config(state='disabled')
        else:
            self.__file_size_entry.config(state='disabled')
            self.__file_rows_entry.config(state='normal')

    def apply(self):
        """
                Processes the input from the dialog fields and sets the result attribute with the export parameters.
        """
        file_size = self.__file_size_var.get() if self.__export_choice_var.get() == "size" else None
        file_rows = self.__file_rows_var.get() if self.__export_choice_var.get() == "rows" else None
        row_limit = self.__row_limit_var.get() if self.__row_limit_var.get() != 0 else None
        row_offset = self.__row_offset_var.get() if self.__row_offset_var.get() != 0 else None
        self.result = (file_size, file_rows, row_limit, row_offset)
