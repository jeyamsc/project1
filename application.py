import os
import datetime
import requests
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from psycopg2 import paramstyle
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp
from helpers import login_required

from fuzzywuzzy import *


app = Flask(__name__)
x = datetime.datetime.now()
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template('index.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get('usuario')
        password = request.form.get('contraseña')
        confirmacion = request.form.get('confirmacion')
        # print(usuario, contraseña, confirmacion)
        if not user:
            flash("Rellena el campo 'Usuario'")
            return redirect('register')
        if not password:
            flash("Rellena el campo 'Contraseña'")
            return redirect('register')
        if not confirmacion:
            flash("Rellena el campo 'Confirmar Contraseña'")
            return redirect('register')
        if password != confirmacion:
            flash("Rellena el campo 'La contraseña no es la misma")
            return redirect('register')
        query1 = text("SELECT * FROM users WHERE userbro = :usuario")
        userID = db.execute(query1, {"usuario": user}).rowcount
        print(userID)

        if userID == 1:
            flash("El nombre de usuario que usted ingreso ya existe")
            return render_template('register.html')
        hash = generate_password_hash(password)
        print(hash)
        insert = text(
            "INSERT INTO users (userbro, password) VALUES(:userbro,:hash);")
        db.execute(insert, {'userbro': user, 'hash': hash})
        db.commit()

        flash("USUARIO REGISTRADO!!!")
        IdUser = db.execute(
            query1, {"usuario": user}).fetchone()[0]
        session["user_id"] = IdUser
        return redirect("/")
    return render_template('register.html')


@app.route("/libros", methods=["POST"])
@login_required
def libros():
    busqueda = request.form.get('busqueda').lower()
    print(busqueda)
    if not busqueda:
        flash("No se ingresó ningún valor")
        return redirect('books')

   
    query = text(
        "SELECT * FROM books WHERE LOWER(isbn) LIKE :busqueda OR LOWER(title) LIKE :busqueda OR LOWER(autor) LIKE :busqueda")
    book = db.execute(query, {"busqueda": f'%{busqueda}%'}).fetchall()
    

    if not book:
        response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={busqueda}").json()

        if response['totalItems'] == 0:
            flash("No se encontraron resultados")
            return redirect('books')

    return render_template('libros.html', book=book)


@app.route("/libro", methods=["GET", "POST"])
@login_required
def libro():

    if request.method == "POST":
        comentario = request.form.get('comentario')
        rating = request.form.get('rating')
        id = request.args.get('isbn')

        fecha = x.strftime("%I") + ':' + x.strftime("%M") + \
            " " + x.strftime("%A")

        # check if user already commented
        query = text(
            "SELECT * FROM comentarios WHERE userId = :userId AND bookId = :bookId")
        user = db.execute(query, {"userId": session["user_id"], "bookId": id}).rowcount
        if user == 1:
            flash("Ya has comentado este libro")
            return redirect('libro?isbn='+id)
        if not comentario:
            flash("Por favor, agregue un comentario.")
            return redirect('libro?isbn='+id)
        if not rating:
            flash("Por favor, agregue una puntuación.")
            return redirect('libro?isbn='+id)


        insert = text(
            "INSERT INTO comentarios (comentario, fecha, userId, bookId, rating) VALUES (:comentario, :fecha, :userId, :bookId, :rating)")
        db.execute(insert, {'comentario':comentario, 'fecha':fecha, 'userId':session["user_id"], 'bookId':id, 'rating':rating})
        db.commit()
        flash("Comentario agregado")
        return redirect('libro?isbn='+id)


    id = request.args.get('isbn')
    #query book and comentarios
    
    query = text("SELECT * FROM books WHERE isbn = :isbn")
    book = db.execute(query, {"isbn": id}).fetchone()

    #query comentarios and join with users
    query = text("SELECT * FROM comentarios JOIN users ON comentarios.userId = users.id WHERE bookId = :isbn")
    comentarios = db.execute(query, {"isbn": id}).fetchall()

    response = requests.get("https://www.googleapis.com/books/v1/volumes?q=isbn:" + id).json()
    if response['totalItems'] == 0:
        flash("No se encontraron resultados")
        return redirect('index')

    query = text("SELECT COUNT(*), AVG(rating) FROM comentarios WHERE bookId = :isbn")
    res = db.execute(query, {"isbn": id}).fetchone()
    
    book = {
        'isbn': book[0],
        'title': book[1],
        'autor': book[2],
        'year': book[3],
        'image': response['items'][0]['volumeInfo']['imageLinks']['thumbnail'],
        'comentarios': comentarios,
        "review_count": res[0],
        "average_score": float(res[1]) if res[1] else 0
    }

    # get user id from each comment 
    return render_template('libro.html', book=book, iduser=session["user_id"])

@app.route("/eliminar_comentario", methods=["GET"])
def eliminar_comentario():
    comentarioId = request.args.get('id')
    isbn = request.args.get('isbn')
    query=text("DELETE FROM comentarios WHERE id = :id")
    db.execute(query, {"id": comentarioId})
    db.commit()
    print("comentario eliminado")
    flash("Comentario eliminado")
    return redirect(f'/libro?isbn={isbn}')

@app.route("/actualizar_comentario", methods=["POST"])
def actualizar_comentario():
    comentarioId = request.args.get('id')
    isbn = request.args.get('isbn')
    comentario = request.form.get('comentario')
    query = text("UPDATE comentarios SET comentario = :comentario WHERE id = :id")
    db.execute(query, {"id": comentarioId, "comentario": comentario})
    db.commit()
    print("comentario actualizado")
    flash("Comentario actualizado")
    return redirect(f'/libro?isbn={isbn}')


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        usuario = request.form.get('usuario')
        password = request.form.get('password1')
        # print(usuario, contraseña, confirmacion)
        if not usuario:
            flash("Rellena el campo 'Usuario'")
            return redirect('login')
        if not password:
            flash("Rellena el campo 'Contraseña'")
            return redirect('login')
        query = text("SELECT * FROM users WHERE userbro = :usuario")
        row = db.execute(query, {"usuario": usuario}).fetchone()

        if row is None != 1 and not check_password_hash(password, password):
            flash("El usuario o la contraseña son invalidos")
            return render_template('login.html')
        session["user_id"] = row.id
        flash("Inicio sesion correctamente")
        return redirect("/")
    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/<isbn>")

def book_api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    if book is None:
        # fetch from google api
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes?q=isbn:"+isbn).json()
        if response['totalItems'] == 0:
            return jsonify({"error": "Invalid isbn"}), 404

        return jsonify({
            "title": response['items'][0]['volumeInfo']['title'],
            "author": response['items'][0]['volumeInfo']['authors'][0],
            "year": response['items'][0]['volumeInfo']['publishedDate'],
            "isbn": isbn,
            "review_count": response['items'][0]['volumeInfo']['ratingsCount'],
            "average_score": response['items'][0]['volumeInfo']['averageRating']
        })

    # fetch from database
    res = db.execute("SELECT COUNT(*), AVG(rating) FROM comentarios WHERE bookId = :isbn", {"isbn": isbn}).fetchone()
    print(res)
    return jsonify({
        "title": book.title,
        "author": book.autor,
        "year": book.year,
        "isbn": isbn,
        "review_count": res[0],
        "average_score": float(res[1]) if res[1] else 0
    })
