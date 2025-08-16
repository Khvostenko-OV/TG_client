import psycopg2

from TG_client.settings import DATABASES

DB_HOST = DATABASES["default"]["HOST"]
DB_PORT = DATABASES["default"]["PORT"]
DB_USER = DATABASES["default"]["USER"]
DB_PASSWORD = DATABASES["default"]["PASSWORD"]
DB_NAME = DATABASES["default"]["NAME"]

if __name__ == "__main__":

    conn = psycopg2.connect(database="postgres", host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()
    conn.autocommit = True

    cur.execute(f"SELECT datname FROM pg_database WHERE datname = '{DB_NAME}';")
    res = cur.fetchone()
    if not res:
        print(f"--- Create database: {DB_NAME}")
        cur.execute(f"CREATE DATABASE {DB_NAME};")

    cur.close()
    conn.close()
