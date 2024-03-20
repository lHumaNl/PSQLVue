import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import pandas as pd


class PsqlGuiApp:
    def __init__(self, root, psql_connection):
        self.root = root
        self.psql_connection = psql_connection
        self.root.title("PSQLVue Query Executor")

        self.query_input = tk.Text(root, height=10)
        self.query_input.pack()

        self.execute_button = tk.Button(root, text="Execute", command=self.execute_query)
        self.execute_button.pack()

        # Создание фрейма для Treeview и скроллбара
        self.tree_frame = tk.Frame(root)
        self.tree_frame.pack()

        self.tree_scroll = tk.Scrollbar(self.tree_frame)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.result_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set, selectmode="extended")
        self.tree_scroll.config(command=self.result_tree.yview)
        self.result_tree.pack()

    def execute_query(self):
        query = self.query_input.get("1.0", tk.END)
        result = self.psql_connection.execute_query(query)
        if isinstance(result, pd.DataFrame):
            if not result.empty:
                self.display_result_in_treeview(result)
            else:
                messagebox.showinfo("Result", "The query executed successfully but returned no data.")
        elif isinstance(result, str):
            # Ошибка из БД или пустой результат представлен строкой
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Result", "The query executed successfully but returned no data.")

    def display_result_in_treeview(self, df):
        # Очистка предыдущих данных
        self.result_tree.delete(*self.result_tree.get_children())

        # Создание новых столбцов
        self.result_tree["column"] = list(df.columns)
        self.result_tree["show"] = "headings"

        # Форматирование наших столбцов
        for column in self.result_tree["column"]:
            self.result_tree.heading(column, text=column)

        # Добавление данных в таблицу
        df_rows = df.to_numpy().tolist()
        for row in df_rows:
            self.result_tree.insert("", "end", values=row)

        # Авто-ресайз колонок
        for col in self.result_tree["column"]:
            self.result_tree.column(col, width=tk.AUTO, stretch=tk.NO)
