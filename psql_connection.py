import psycopg2
import pandas as pd
import logging


class PsqlConnection:
    """
        Manages the connection to a PostgreSQL database, allowing for executing queries and fetching data.

        Attributes:
            connection: A psycopg2 connection object to the database.
    """
    def __init__(self, db_params):
        """
                Initializes the database connection using provided parameters.

                Args:
                    db_params (dict): Database connection parameters including host, port, user, password, and dbname.
        """
        self.connection = self.__connect_to_db(db_params)

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

    def fetch_data(self, query: str, is_autocommit: bool, offset=None, limit=None, all_data=False, count_only=False):
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
        with self.connection.cursor() as cursor:
            if count_only:
                query = f"SELECT COUNT(*) FROM ({query}) AS subquery"

                try:
                    cursor.execute(query)
                    return cursor.fetchone()[0]
                except psycopg2.Error as e:
                    logging.error(f"Database error: {e.pgerror}")
                    self.connection.rollback()
                    return f'Error: {e.pgerror}'
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
                cursor.execute(paginated_query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    result = pd.DataFrame(cursor.fetchall(), columns=columns)
                else:
                    if is_autocommit:
                        self.connection.commit()
                    result = None
                return result
            except psycopg2.Error as e:
                logging.error(f"Database error: {e.pgerror}")
                self.connection.rollback()
                return f'Error: {e.pgerror}'

    def close(self):
        if self.connection:
            self.connection.close()
            logging.info("Database connection closed")
