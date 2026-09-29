import pyodbc

MASTER = (
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=master;"
    "Trusted_Connection=yes;TrustServerCertificate=yes"
)
NAME = "LamaplastCosting_Dev"

with pyodbc.connect(MASTER,autocommit=True) as cn:
    exists = cn.execute("SELECT 1 FROM sys.databases WHERE name = ?",NAME).fetchone()
    if exists:
        print("Database already exists")
    else:
        cn.execute(f"CREATE DATABASE {NAME} COLLATE Greek_CI_AS")
        print("Database created")