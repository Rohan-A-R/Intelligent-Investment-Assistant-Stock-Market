import psycopg2

DATABASE_URL = "postgres://admin1%40django-postgres-server:Rohan123@django-postgres-server.postgres.database.azure.com:5432/postgres?sslmode=require"

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.close()
    print("Database connection successful!")
except Exception as e:
    print("Failed to connect:", e)
