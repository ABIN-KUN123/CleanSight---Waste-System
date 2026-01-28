from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
# Gunakan secret key untuk fitur flash message
app.secret_key = 'kunci_rahasia_cleansight_2026'

# --- KONEKSI MONGODB ---
# Catatan: 'mongodb://localhost:27017/' hanya bekerja di laptop lokal.
# Jika sudah punya akun MongoDB Atlas, ganti URL di bawah ini.
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

    # Ambil 5 user teratas untuk leaderboard berdasarkan poin
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

@app.route('/proses_register', methods=['POST'])
def proses_register():
    if request.method == 'POST':
        user_baru = {
            "name": request.form['nama'],
            "email": request.form['email'],
            "location": request.form['lokasi'],
            "total_points": 0,
            "created_at": datetime.now()
        }
        db.users.insert_one(user_baru)
        flash("Pendaftaran berhasil! Selamat bergabung.", "success")
        return redirect(url_for('daftar_user'))

# --- FITUR DAFTAR USER ---

@app.route('/daftar_user')
def daftar_user():
    users = list(db.users.find().sort("name", 1))
    total = db.users.count_documents({})
    return render_template('daftar_user.html', leaderboard=users, t_users=total)

# --- FITUR TRANSAKSI ---

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
        waste_id = request.form['waste_id']
        drop_id = request.form['drop_id']
        weight_kg = float(request.form['weight_kg'])

        user = db.users.find_one({"_id": ObjectId(user_id)})
        waste = db.waste_types.find_one({"_id": ObjectId(waste_id)})
        drop = db.drop_points.find_one({"_id": ObjectId(drop_id)})

        point_per_kg = waste['point_value']
        points_earned = int(weight_kg * point_per_kg)

        trx_doc = {
            "user_id": ObjectId(user_id),
            "user_name": user['name'],
            "waste_category": waste['category_name'],
            "drop_point": drop['name'],
            "weight_kg": weight_kg,
            "points_earned": points_earned,
            "trx_date": datetime.now()
        }

        db.transactions.insert_one(trx_doc)
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"total_points": points_earned}}
        )

        flash(f"Setoran {weight_kg}kg dari {user['name']} berhasil disimpan!", "success")
        return redirect(url_for('riwayat'))

    except Exception as e:
        flash(f"Gagal simpan: {e}", "danger")
        return redirect(url_for('transaksi_form'))

@app.route('/data_sampah')
def data_sampah():
    transactions = list(db.transactions.find().sort("trx_date", -1))
    pipeline = [{"$group": {"_id": None, "total_kg": {"$sum": "$weight_kg"}}}]
    result = list(db.transactions.aggregate(pipeline))
    total_kg = result[0]['total_kg'] if result else 0
    return render_template('data_sampah.html', transactions=transactions, t_kg=round(total_kg, 1))

@app.route('/riwayat')
def riwayat():
    transactions = list(db.transactions.find().sort("trx_date", -1))
    return render_template('riwayat.html', transactions=transactions)

# --- RUN APP ---
# Konfigurasi ini memungkinkan aplikasi berjalan di lokal (Port 5000) 
# maupun di server hosting (Port dinamis).

if __name__ == '__main__':
    # Mengambil PORT dari server hosting, default ke 5000 untuk lokal
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' wajib agar bisa diakses secara publik di hosting
    app.run(host='0.0.0.0', port=port, debug=True)