"""Τρέξε ένα SQL query στη βάση του .env και τύπωσε το αποτέλεσμα.

    python tools/sql.py "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES ORDER BY 1"
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine,text

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

query = sys.argv[1] if len(sys.argv) > 1 else "SELECT DB_NAME() AS db"
with engine.connect() as cn:
    result = cn.execute(text(query))
    if result.returns_rows:
        print(" | ".join(result.keys()))
        for row in result:
            print(" | ".join(str(i) for i in row))
    else:
        cn.commit()
        print("OK")