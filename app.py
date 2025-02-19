from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import sqlite3
from flask_socketio import SocketIO
from functools import wraps
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app)

DATABASE = 'beers.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS beers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brewery TEXT NOT NULL,
                beer TEXT NOT NULL,
                style TEXT NOT NULL,
                abv TEXT NOT NULL,
                price_half TEXT NOT NULL,
                price_two_third TEXT NOT NULL,
                price_pint TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                category TEXT DEFAULT '',
                type TEXT DEFAULT 'Draft'
            )
        """)
        conn.commit()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM beers")
        count = cursor.fetchone()[0]
        if count == 0:
            with open('example.json', 'r') as f:
                sample_beers = json.load(f)
            for beer in sample_beers:
                cursor.execute("""
                    INSERT INTO beers (brewery, beer, style, abv, price_half, price_two_third, price_pint, active, display_order, category, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, beer)
            conn.commit()

# Add global variable for webhook messages.
latest_message = ""

def check_auth(username, password):
    return username == os.getenv('ADMIN_USER') and password == os.getenv('ADMIN_PASS')

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    # Show only active beers ordered by display_order.
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, brewery, beer, style, abv, price_half, price_two_third, price_pint, type
            FROM beers
            WHERE active = 1
            ORDER BY display_order, id
        """)
        beers = cursor.fetchall()
    return render_template('index.html', beers=beers)

@app.route('/admin')
@requires_auth
def admin():
    # Show all beers ordered by display_order.
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, brewery, beer, style, abv, price_half, price_pint, active, display_order, category
            FROM beers
            ORDER BY display_order, id
        """)
        beers = cursor.fetchall()
    return render_template('admin.html', beers=beers)

@app.route('/add', methods=['POST'])
def add():
    brewery    = request.form['brewery']
    beer_name  = request.form['beer']
    style      = request.form['style']
    abv        = request.form['abv']
    price_half = request.form['price_half']
    price_two_third = request.form['price_two_third']
    price_pint = request.form['price_pint']
    display_order = request.form.get('display_order', 0)
    category = request.form.get('category', '')
    beer_type = request.form.get('type', 'Draft')
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO beers (brewery, beer, style, abv, price_half, price_two_third, price_pint, active, display_order, category, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """, (brewery, beer_name, style, abv, price_half, price_two_third, price_pint, display_order, category, beer_type))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, brewery, beer, style, abv, price_half, price_two_third, price_pint, type FROM beers WHERE id = ?", (new_id,))
        new_beer = cursor.fetchone()
    socketio.emit('item_added', {'beer': new_beer})
    return redirect(url_for('admin'))

@app.route('/remove/<int:beer_id>', methods=['POST'])
def remove(beer_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE beers SET active = 0 WHERE id = ?", (beer_id,))
        conn.commit()
    socketio.emit('item_removed', {'beer_id': beer_id})
    return redirect(url_for('admin'))

@app.route('/restore/<int:beer_id>', methods=['POST'])
def restore(beer_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE beers SET active = 1 WHERE id = ?", (beer_id,))
        conn.commit()
    return redirect(url_for('admin'))

@app.route('/admin/search_removed')
@requires_auth
def search_removed():
    q = request.args.get('q', '')
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, brewery, beer, style, abv, price_half, price_pint, display_order, category
            FROM beers
            WHERE active = 0 AND (brewery LIKE ? OR beer LIKE ? OR style LIKE ?)
            ORDER BY display_order, id
        """, ('%'+q+'%', '%'+q+'%', '%'+q+'%'))
        removed_beers = cursor.fetchall()
    return render_template('search_removed.html', removed_beers=removed_beers, q=q)

# New API route for inline editing via AJAX.
@app.route('/api/edit/<int:beer_id>', methods=['POST'])
def api_edit(beer_id):
    data = request.get_json()
    if not data:
        return {"status": "error", "message": "No data provided"}, 400
    brewery = data.get('brewery')
    beer_name = data.get('beer')
    style = data.get('style')
    abv = data.get('abv')
    price_half = data.get('price_half')
    price_two_third = data.get('price_two_third')
    price_pint = data.get('price_pint')
    display_order = data.get('display_order', 0)
    category = data.get('category', '')
    beer_type = data.get('type', 'Draft')
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE beers
            SET brewery = ?, beer = ?, style = ?, abv = ?, price_half = ?, price_two_third = ?, price_pint = ?, display_order = ?, category = ?, type = ?
            WHERE id = ?
        """, (brewery, beer_name, style, abv, price_half, price_two_third, price_pint, display_order, category, beer_type, beer_id))
        conn.commit()
        cursor.execute("SELECT id, brewery, beer, style, abv, price_half, price_two_third, price_pint, type FROM beers WHERE id = ?", (beer_id,))
        updated_beer = cursor.fetchone()
    socketio.emit('item_updated', {'beer': updated_beer})
    return {"status": "success"}

# New API route to fetch the beer list.
@app.route('/api/beers', methods=['GET'])
def api_beers():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT brewery, beer, style, abv, price_half, price_two_third, price_pint, type
            FROM beers
            WHERE active = 1
            ORDER BY display_order, id
        """)
        beers = cursor.fetchall()
    return jsonify(beers)

# New webhook route for external beer list updates.
@app.route('/webhook', methods=['POST'])
def webhook():
    from flask import jsonify
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    action = data.get("action")
    if action == "removed":
        beer_id = data.get("beer_id")
        if not beer_id:
            return jsonify({"status": "error", "message": "No beer_id provided"}), 400
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM beers WHERE id = ?", (beer_id,))
            conn.commit()
        socketio.emit('item_removed', {'beer_id': beer_id})
        message = f"Beer {beer_id} removed."
        socketio.emit('update', {'message': message})
        return jsonify({"status": "success", "message": message})

    elif action == "added":
        brewery    = data.get("brewery")
        beer_name  = data.get("beer")
        style      = data.get("style")
        abv        = data.get("abv")
        price_half = data.get("price_half")
        price_two_third = data.get("price_two_third")
        price_pint = data.get("price_pint")
        display_order = data.get("display_order", 0)
        category   = data.get("category", '')
        beer_type  = data.get("type", 'Draft')
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO beers (brewery, beer, style, abv, price_half, price_two_third, price_pint, active, display_order, category, type)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (brewery, beer_name, style, abv, price_half, price_two_third, price_pint, display_order, category, beer_type))
            conn.commit()
            new_beer_id = cursor.lastrowid
            cursor.execute("SELECT id, brewery, beer, style, abv, price_half, price_two_third, price_pint, type FROM beers WHERE id = ?", (new_beer_id,))
            new_beer = cursor.fetchone()
        message = f"New beer added: {beer_name} from {brewery}"
        socketio.emit('item_added', {'beer': new_beer})
        socketio.emit('update', {'message': message})
        return jsonify({"status": "success", "message": message, "beer_id": new_beer_id})
    else:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
