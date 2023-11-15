import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv
import csv

load_dotenv()

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    
    tabla_users = text("""CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        userbro TEXT NOT NULL,
        password TEXT NOT NULL
        );
        """)
    
    db.execute(text("DROP TABLE IF EXISTS users"))
    db.execute(tabla_users)

    tabla_books = text("""CREATE TABLE IF NOT EXISTS books(
    isbn TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    autor TEXT NOT NULL,
    year INTEGER NOT NULL
    );""")

    db.execute(text("DROP TABLE IF EXISTS books"))
    db.execute(tabla_books)

    tabla_comentarios= text("""CREATE TABLE IF NOT EXISTS comentarios(
        id SERIAL PRIMARY KEY,
        comentario TEXT NOT NULL,
        rating INTEGER NOT NULL,
        fecha TEXT,
        userId INTEGER,
        bookId TEXT,
        FOREIGN KEY (bookId) REFERENCES books(isbn),
        FOREIGN KEY (userId) REFERENCES users(id)
    );""")

    db.execute(text("DROP TABLE IF EXISTS comentarios"))
    db.execute(tabla_comentarios)
    
    
    f= open("books.csv")
    reader = csv.reader(f)
    i = 0

    try:
        for row in reader:
            print(f"{i} - {row}")
            i+=1
            insert = text("INSERT INTO books (isbn, title, autor, year) VALUES(:isbn, :title, :autor, :year);")
            db.execute(insert, {'isbn': row[0], 'title': row[1], 'autor': row[2], 'year': row[3]})
    except:
        db.rollback()
    
    db.commit() 

    
if __name__ == "__main__":
    main()