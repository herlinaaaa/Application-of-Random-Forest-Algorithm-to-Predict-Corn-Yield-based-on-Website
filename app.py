from flask import Flask, render_template, request, session, redirect, url_for
import os
import secrets
import numpy as np
import re
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import mysql.connector


app = Flask(__name__)

# Generate a secret key
secret_key = secrets.token_hex(16)  # Generates a 32-character hexadecimal string

# Set the secret key in the Flask app configuration
app.config['SECRET_KEY'] = secret_key

def create_db_connection():
    conn=mysql.connector.connect(
        host = 'localhost',
        user = 'root',
        password = '',
        database = 'ta02_rf'
    )
    return conn

# Load your data
df = pd.read_csv("datasetTugasAkhir.csv")

# Separate features and target
X = df.drop(columns=['hasil_panen', 'obat_nutrisil_campuran'])
y = df['hasil_panen']

# Standardize features
standardScaler = StandardScaler()
columns_to_scale = ['luas_panen', 'bibit', 'pupuk_npk', 'pupuk_urea', 'obat_insectisida']
X[columns_to_scale] = standardScaler.fit_transform(X[columns_to_scale])

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, test_size=0.2)

# Define and train RandomForestRegressor model
# best_params = {'max_depth': 4, 'max_features': 'sqrt', 'n_estimators': 10, 'min_samples_split': 2, 'min_samples_leaf': 1, 'bootstrap': False}
# rf_best = RandomForestRegressor(**best_params)
rf_model = RandomForestRegressor(max_depth=5,
                                min_samples_leaf=1,
                                min_samples_split=8,
                                n_estimators=88,
                                random_state=42)
rf_model.fit(X_train, y_train)

@app.route("/", methods=['GET', 'POST'])
def index():
    errors = None
    input_values = None
    if request.method == 'GET':
        return render_template('index.html', errors=errors, input_values=input_values)
    
    errors = {}
    input_values = {}
    if request.method == 'POST':
        input_values['luas_panen'] = request.form.get('luas_panen', '')
        input_values['bibit'] = request.form.get('bibit', '')
        input_values['pupuk_npk'] = request.form.get('pupuk_npk', '')
        input_values['pupuk_urea'] = request.form.get('pupuk_urea', '')
        input_values['obat_insectisida'] = request.form.get('obat_insectisida', '')
        
        luas_panen = bibit = pupuk_npk = pupuk_urea = obat_insectisida = None

        try:
            luas_panen = float(request.form['luas_panen'])
        except ValueError:
            errors['luas_panen'] = "Masukkan harus berupa angka."

        try:
            bibit = float(request.form['bibit'])
        except ValueError:
            errors['bibit'] = "Masukkan harus berupa angka."

        try:
            pupuk_npk = float(request.form['pupuk_npk'])
        except ValueError:
            errors['pupuk_npk'] = "Masukkan harus berupa angka."

        try:
            pupuk_urea = float(request.form['pupuk_urea'])
        except ValueError:
            errors['pupuk_urea'] = "Masukkan harus berupa angka."

        try:
            obat_insectisida = float(request.form['obat_insectisida'])
        except ValueError:
            errors['obat_insectisida'] = "Masukkan harus berupa angka."

        scaled_input = None
        prediction = None

        if not errors:
            scaled_input = standardScaler.transform([[luas_panen, bibit, pupuk_npk, pupuk_urea, obat_insectisida]])
            prediction = rf_model.predict(scaled_input)[0]
            
            # Simpan prediksi dan input ke dalam database
            conn = create_db_connection()
            cursor = conn.cursor()
            
            insert_query = "INSERT INTO prediksi (luas_panen, bibit, pupuk_npk, pupuk_urea, obat_insectisida, hasil_panen) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (str(luas_panen), str(bibit), str(pupuk_npk), str(pupuk_urea), str(obat_insectisida), str(prediction)))
            conn.commit()

            cursor.close()
            conn.close()
    return render_template('index.html', errors=errors, input_values=input_values, prediction=prediction)

@app.route("/history")
def history():
    conn = create_db_connection()
    cursor = conn.cursor()

    select_query = "SELECT luas_panen, bibit, pupuk_npk, pupuk_urea, obat_insectisida, hasil_panen FROM prediksi"
    cursor.execute(select_query)
    records = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('history.html', records=records)


@app.route("/login", methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'GET':
        return render_template('login.html', msg = msg)
    elif request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        conn = create_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        users = cursor.fetchone()
        if users:
            session['loggedin'] = True
            session['id'] = users['id']
            session['username'] = users['username']
            msg = 'Berhasil Login'
            return redirect(url_for('index'))
        else:
            msg = 'Username dan Password salah'
    return render_template('login.html', msg = msg)

@app.route("/register", methods=['GET', 'POST'])
def register():
    msg = ''
    msg_success = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        # Simpan prediksi dan input ke dalam database
        conn = create_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s OR password = %s', (username, password))
        users = cursor.fetchone()
        if users:
            msg = 'Akun Sudah Ada'
        elif not re.match(r'[A-Za-z0-9]+', username) or not re.match(r'[A-Za-z0-9]+', password):
            msg = 'Username dan password harus berupa huruf dan angka'
        elif not username or not password:
            msg = 'Formulir harus diisi'
        else:
            insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(insert_query, (username, password))
            conn.commit()
            msg_success = 'Registrasi Berhasil, Silahkan Login'
        cursor.close()
        conn.close()
    elif request.method == 'POST':
        msg = 'Formulir harus diisi'
    return render_template('register.html', msg = msg, msg_success = msg_success)


if __name__ == '__main__':
    app.run(debug=True)