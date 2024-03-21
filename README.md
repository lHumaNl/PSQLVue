# PSQLVue UI Executor

PSQLVue UI Executor is a mini DBeaver-like application designed for executing PostgreSQL queries and managing the results in a user-friendly interface. It supports both GUI and HTTP interfaces, allowing users to execute queries, view results, and export data directly from their desktop or via a web browser.

## Features

- Execute SQL queries on a PostgreSQL database.
- Display query results in a paginated table view.
- Export query results to CSV files.
- Autocommit option for database transactions.
- Support for executing queries through a GUI or a web interface.

## Installation

Before installing PSQLVue UI Executor, ensure you have Python installed on your system. This application requires Python 3.6 or newer.

1. Clone this repository or download the source code.
2. Navigate to the project directory and create a virtual environment:
    ```
    python -m venv venv
    ```
3. Activate the virtual environment:
    - On Windows:
        ```
        .\venv\Scripts\activate
        ```
    - On Unix or MacOS:
        ```
        source venv/bin/activate
        ```
4. Install the required dependencies:
    ```
    pip install -r requirements.txt
    ```

## Usage

### Starting the Application

To start the application, you'll need to specify the interface mode (`gui` or `http`) and database connection parameters. Here is the basic command structure:

python main.py -u <user> -P <password> -d <database> -i <interface>


- `-H`, `--host`: Database host (default `localhost`)
- `-p`, `--port`: Database port (default `5432`)
- `-u`, `--user`: Database user (**required**)
- `-P`, `--password`: Database password (default `''`)
- `-d`, `--db`: Database name (**required**)
- `-i`, `--interface`: Interface mode (`gui` or `http`) (**required**)

### GUI Interface

The GUI interface provides a simple and intuitive way to execute queries and manage results. Features include a query input box, execute and export buttons, and a results table.

### HTTP Interface (TODO)

The HTTP interface allows you to execute queries via a web browser. Start the application in `http` mode, and navigate to `http://localhost:5000` to access the web interface.
