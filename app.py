from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_cleansight_2026'

# --- KONEKSI MONGODB ---
try:
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client['cleansight_db'] 
    client.server_info() 
    print("Koneksi MongoDB Berhasil!")
except Exception as e:
    print(f"Gagal Koneksi MongoDB: {e}")

# --- ROUTES DASHBOARD ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    total_users = db.users.count_documents({})
    total_trx = db.transactions.count_documents({})
    
    pipeline = [{"$group": {"_id": None, "total_kg": {"$sum": "$weight_kg"}}}]
    result = list(db.transactions.aggregate(pipeline))
    total_kg = result[0]['total_kg'] if result else 0

    top_users = list(db.users.find().sort("total_points", -1).limit(5))

    return render_template('dashboard.html', 
                           t_users=total_users, 
                           t_trx=total_trx, 
                           t_kg=round(total_kg, 1),
                           leaderboard=top_users)

# --- FITUR REGISTER ---

@app.route('/register')
def halaman_register():
    return render_template('register.html')

# Menambahkan rute alias /register_user agar tidak 404 saat diakses manual/form
@app.route('/proses_register', methods=['POST'])
@app.route('/register_user', methods=['POST']) 
def proses_register():
    if request.method == 'POST':
        try:
            user_baru = {
                "name": request.form['nama'],
                "email": request.form['email'],
                "location": request.form['lokasi'],
                "total_points": 0,
                "created_at": datetime.now()
            }
            db.users.insert_one(user_baru)
            flash("Pendaftaran berhasil!", "success")
            return redirect(url_for('daftar_user'))
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for('halaman_register'))

# --- FITUR DAFTAR USER (Sesuai dengan HTML Anda) ---

@app.route('/daftar_user')
def daftar_user():
    users = list(db.users.find().sort("name", 1))
    total = db.users.count_documents({})
    # Variabel 'leaderboard' dan 't_users' harus sama dengan di HTML
    return render_template('daftar_user.html', leaderboard=users, t_users=total)

@app.route('/edit_user/<id>', methods=['GET', 'POST'])
def edit_user(id):
    user = db.users.find_one({"_id": ObjectId(id)})
    if request.method == 'POST':
        db.users.update_one({"_id": ObjectId(id)}, {"$set": {
            "name": request.form['nama'],
            "email": request.form['email'],
            "location": request.form['lokasi']
        }})
        flash("Data berhasil diperbarui!", "success")
        return redirect(url_for('daftar_user'))
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<id>')
def delete_user(id):
    db.users.delete_one({"_id": ObjectId(id)})
    flash("Pengguna dihapus!", "success")
    return redirect(url_for('daftar_user'))

# --- FITUR TRANSAKSI & DATA SAMPAH ---

@app.route('/transaksi')
def transaksi_form():
    users = list(db.users.find())
    waste_types = list(db.waste_types.find())
    drop_points = list(db.drop_points.find())
    return render_template('transaksi.html', users=users, wastes=waste_types, drops=drop_points)

@app.route('/simpan_transaksi', methods=['POST'])
def simpan_transaksi():
    try:
        user_id = request.form['user_id']
        weight_kg = float(request.form['weight_kg'])
        waste = db.waste_types.find_one({"_id": ObjectId(request.form['waste_id'])})
        user = db.users.find_one({"_id": ObjectId(user_id)})

        points = int(weight_kg * waste['point_value'])
        
        db.transactions.insert_one({
            "user_id": ObjectId(user_id),
            "user_name": user['name'],
            "weight_kg": weight_kg,
            "points_earned": points,
            "trx_date": datetime.now()
        })
        db.users.update_one({"_id": ObjectId(user_id)}, {"$inc": {"total_points": points}})

        flash("Transaksi berhasil!", "success")
        return redirect(url_for('riwayat'))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for('transaksi_form'))

@app.route('/data_sampah')
def data_sampah():
    transactions = list(db.transactions.find().sort("trx_date", -1))
    pipeline = [{"$group": {"_id": None, "total_kg": {"$sum": "$weight_kg"}}}]
    result = list(db.transactions.aggregate(pipeline))
    total_kg = result[0]['total_kg'] if result else 0
    # Pastikan return render_template selalu ada
    return render_template('data_sampah.html', transactions=transactions, t_kg=round(total_kg, 1))

@app.route('/riwayat')
def riwayat():
    transactions = list(db.transactions.find().sort("trx_date", -1))
    return render_template('riwayat.html', transactions=transactions)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)