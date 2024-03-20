import psycopg2
import pandas as pd
import logging


class PsqlConnection:
    def __init__(self, db_params):
        self.connection = self._connect_to_db(db_params)

    def _connect_to_db(self, db_params):
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

    def execute_query(self, query: str):
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query)
                if cursor.description:  # Если запрос возвращает данные
                    # Создаем DataFrame из результатов запроса
                    columns = [desc[0] for desc in cursor.description]
                    result = pd.DataFrame(cursor.fetchall(), columns=columns)
                else:  # Для запросов, не возвращающих данные
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
