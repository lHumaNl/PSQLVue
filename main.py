import argparse
from psql_connection import PsqlConnection
from web_interface import app as flask_app
import threading
import tkinter as tk
from gui_interface import PsqlGuiApp


def main():
    parser = argparse.ArgumentParser(description="PSQLVue Executor Utility")
    parser.add_argument("-H", "--host", default='localhost', help="Database host")
    parser.add_argument("-p", "--port", default=5432, type=int, help="Database port")
    parser.add_argument("-u", "--user", required=True, help="Database user")
    parser.add_argument("-P", "--password", default='', help="Database password")
    parser.add_argument("-d", "--db", required=True, help="Database name")
    parser.add_argument("-i", "--interface", choices=['gui', 'http'], required=True,
                        help="Interface mode (GUI or HTTP)")

    args = parser.parse_args()

    db_params = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "password": args.password,
        "db": args.db
    }

    psql_connection = PsqlConnection(db_params)

    if args.interface == 'http':
        threading.Thread(target=start_web_app, args=(psql_connection,)).start()
    elif args.interface == 'gui':
        start_gui_app(psql_connection)


def start_web_app(psql_connection):
    flask_app.config['psql_connection'] = psql_connection
    flask_app.run(debug=True)


def start_gui_app(psql_connection):
    root = tk.Tk()
    app = PsqlGuiApp(root, psql_connection)
    root.mainloop()


if __name__ == "__main__":
    main()
