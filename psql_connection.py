import psycopg2
import pandas as pd
import logging


class PsqlConnection:
    def __init__(self, db_params):
        self.connection = self._connect_to_db(db_params)

    @staticmethod
    def _connect_to_db(db_params):
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

    def fetch_data(self, query: str, is_autocommit: bool, offset=None, limit=None, all_data=False):
        with self.connection.cursor() as cursor:
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
