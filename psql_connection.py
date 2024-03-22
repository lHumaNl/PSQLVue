import os
from tkinter import messagebox

import psycopg2
import pandas as pd
import logging


class PsqlConnection:
    """
        Manages the connection to a PostgreSQL database, allowing for executing queries and fetching data.

        Attributes:
            __connection: A psycopg2 connection object to the database.
    """

    def __init__(self, db_params):
        """
                Initializes the database connection using provided parameters.

                Args:
                    db_params (dict): Database connection parameters including host, port, user, password, and dbname.
        """
        self.__connection = self.__connect_to_db(db_params)
        self.__cursor = self.__connection.cursor()

    @staticmethod
    def __connect_to_db(db_params):
        """
                Establishes a connection to the PostgreSQL database.

                Args:
                    db_params (dict): Database connection parameters.

                Returns:
                    A psycopg2 connection object.

                Raises:
                    Exception: If the connection to the database fails.
        """
        try:
            conn = psycopg2.connect(
                host=db_params['host'],
                port=db_params['port'],
                user=db_params['user'],
                password=db_params['password'],
                dbname=db_params['db']
            )
            logging.info("Successfully connected to the database")
            return conn
        except Exception as e:
            logging.error(f"Unable to connect to the database: {e}")
            raise

    def fetch_data(self, query: str, is_autocommit: bool = False, offset: int = None, limit: int = None,
                   all_data: bool = False, count_only: bool = False):
        """
                Executes a given SQL query and fetches the data.

                Args:
                    query (str): The SQL query to execute.
                    is_autocommit (bool): Whether to autocommit the transaction.
                    offset (int, optional): The offset from where to start fetching rows.
                    limit (int, optional): The maximum number of rows to fetch.
                    all_data (bool, optional): Fetch all data without pagination if True.
                    count_only (bool, optional): Only count the rows if True.

                Returns:
                    pandas.DataFrame: The fetched data as a DataFrame.
                    str: An error message if an error occurs.
        """
        if query.lower().startswith('show '):
            return self.__use_non_statement_mode_query(query)
        else:
            return self.__use_statement_mode_query(query, is_autocommit, offset, limit, all_data, count_only)

    def __use_non_statement_mode_query(self, query: str):
        try:
            if self.__connection.status == psycopg2.extensions.STATUS_BEGIN:
                proceed = messagebox.askokcancel("",
                                                 "You are attempting to execute a SHOW query in the database. "
                                                 "However, the current session has an uncommitted transaction. "
                                                 "Press Ok to COMMIT this transaction "
                                                 "or Cancel to perform its ROLLBACK.")
                if proceed:
                    self.__connection.commit()
                else:
                    self.__connection.rollback()

            self.__connection.autocommit = True
            self.__cursor.execute(query)
            self.__connection.autocommit = False

            columns = [desc[0] for desc in self.__cursor.description]
            result = pd.DataFrame(self.__cursor.fetchall(), columns=columns)
            rows = len(result)

            return rows, result
        except psycopg2.ProgrammingError as e:
            logging.error(f"Error: {os.linesep.join(arg for arg in e.args)}")
            self.__connection.rollback()
            return f'Error: {os.linesep.join(arg for arg in e.args)}'

        except psycopg2.Error as e:
            logging.error(f"Database error: {e.pgerror}")
            self.__connection.rollback()
            return f'Database error: {e.pgerror}'

        except Exception as e:
            logging.error(f"Error: {e}")
            self.__connection.rollback()
            return f'Error: {e}'

    def __use_statement_mode_query(self, query: str, is_autocommit: bool, offset: int,
                                   limit: int, all_data: bool, count_only: bool):
        if count_only:
            query = f"SELECT COUNT(*) FROM ({query}) AS subquery"

            try:
                self.__cursor.execute(query)
                return self.__cursor.fetchone()[0]
            except psycopg2.ProgrammingError as e:
                logging.error(f"Error: {os.linesep.join(arg for arg in e.args)}")
                self.__connection.rollback()
                return f'Error: {os.linesep.join(arg for arg in e.args)}'

            except psycopg2.Error as e:
                logging.error(f"Database error: {e.pgerror}")
                self.__connection.rollback()
                return f'Database error: {e.pgerror}'

            except Exception as e:
                logging.error(f"Error: {e}")
                self.__connection.rollback()
                return f'Error: {e}'

        else:
            if all_data:
                paginated_query = query
            elif offset is not None and limit is not None:
                paginated_query = f"{query} LIMIT {limit} OFFSET {offset}"
            elif offset is not None:
                paginated_query = f"{query} OFFSET {offset}"
            else:
                paginated_query = f"{query} LIMIT {limit}"

        try:
            self.__cursor.execute(paginated_query)
            if self.__cursor.description:
                columns = [desc[0] for desc in self.__cursor.description]
                result = pd.DataFrame(self.__cursor.fetchall(), columns=columns)

                if is_autocommit:
                    self.__connection.commit()
            else:
                if is_autocommit:
                    self.__connection.commit()
                result = None
            return result
        except psycopg2.ProgrammingError as e:
            logging.error(f"Error: {os.linesep.join(arg for arg in e.args)}")
            self.__connection.rollback()
            return f'Error: {os.linesep.join(arg for arg in e.args)}'

        except psycopg2.Error as e:
            logging.error(f"Database error: {e.pgerror}")
            self.__connection.rollback()
            return f'Database error: {e.pgerror}'

        except Exception as e:
            logging.error(f"Error: {e}")
            self.__connection.rollback()
            return f'Error: {e}'

    def close(self):
        if self.__connection:
            self.__connection.close()
            logging.info("Database connection closed")
