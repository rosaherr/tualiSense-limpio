from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import datetime
import os, json

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1505RMht'
app.config['MYSQL_DB'] = 'app_colaboradores'

mysql = MySQL(app)

@app.route('/')
def index():
    return redirect(url_for('menu'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM colaboradores WHERE correo = %s AND contraseña = %s', (correo, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['correo'] = correo
            session['nombre'] = user[1]
            return redirect(url_for('menu'))
        else:
            flash('Credenciales incorrectas. Intenta de nuevo.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'correo' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html', nombre=session['nombre'])

@app.route('/dashboard')
def ver_mapa():
    if 'correo' not in session:
        return redirect(url_for('login'))

    geojson_path = os.path.join(app.root_path, 'arca_data.geojson')
    with open(geojson_path) as f:
        geojson_data = json.load(f)

    # Obtener el NPS promedio más reciente para cada tienda
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_tienda, AVG(nps) as promedio FROM evaluaciones GROUP BY id_tienda")
    nps_data = {str(row[0]): round(float(row[1]), 1) for row in cur.fetchall()}
    cur.close()

    for f in geojson_data['features']:
        tienda_id = str(f['properties'].get('id'))
        if tienda_id in nps_data:
            f['properties']['nps'] = nps_data[tienda_id]

    return render_template('mapa.html', geojson=geojson_data)

@app.route('/formulario/<id_tienda>', methods=['GET', 'POST'])
def formulario(id_tienda):
    if 'correo' not in session:
        return redirect(url_for('login'))

    geojson_path = os.path.join(app.root_path, 'arca_data.geojson')
    with open(geojson_path) as f:
        geojson_data = json.load(f)
        tienda_info = next((f for f in geojson_data['features'] if str(f['properties'].get('id')) == str(id_tienda)), None)

    if request.method == 'POST':
        satisfaccion = request.form['satisfaccion']
        limpieza = request.form['limpieza']
        comentario = request.form['comentario']
        nps = request.form['nps']
        foto = request.files['foto']
        reagendar = request.form.get('reagendar')
        fecha = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        evidencia_dir = os.path.join(app.root_path, 'static', 'evidencias')
        os.makedirs(evidencia_dir, exist_ok=True)
        ruta_foto = os.path.join('static', 'evidencias', foto.filename)
        foto.save(os.path.join(app.root_path, ruta_foto))

        cur = mysql.connection.cursor()
        cur.execute(
            """
            INSERT INTO evaluaciones (id_tienda, correo_colaborador, satisfaccion, limpieza, comentario, ruta_foto, reagendar, fecha, nps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (id_tienda, session['correo'], satisfaccion, limpieza, comentario, ruta_foto, int(reagendar), fecha, nps)
        )
        mysql.connection.commit()
        cur.close()

        if reagendar == "1":
            return redirect(url_for('agendar_desde_formulario', id_tienda=id_tienda))
        else:
            flash("Formulario enviado con éxito")
            return redirect(url_for('menu'))

    return render_template('formulario.html', tienda=tienda_info, now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))

@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if 'correo' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre FROM tiendas")
    nombres_tiendas = [row[0] for row in cur.fetchall()]
    cur.close()

    if request.method == 'POST':
        nombre_tienda = request.form['nombre_tienda']
        fecha_hora = request.form['fecha_hora']
        fecha = fecha_hora.split('T')[0]
        hora = fecha_hora.split('T')[1]

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO agenda (nombre_tienda, fecha, hora) VALUES (%s, %s, %s)", (nombre_tienda, fecha, hora))
        mysql.connection.commit()
        cur.close()

        return redirect("https://calendar.google.com/calendar/u/0/r/eventedit?text=Visita%20a%20{}&dates={}T{}00Z/{}T{}00Z".format(nombre_tienda, fecha.replace('-', ''), hora.replace(':', ''), fecha.replace('-', ''), hora.replace(':', '')))

    return render_template('agendarVisita.html', tiendas=nombres_tiendas)

@app.route('/agendar/<id_tienda>', methods=['GET', 'POST'])
def agendar_desde_formulario(id_tienda):
    if 'correo' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre FROM tiendas WHERE id = %s", (id_tienda,))
    row = cur.fetchone()
    cur.close()

    nombre_tienda = row[0] if row else "Tienda desconocida"

    if request.method == 'POST':
        fecha_hora = request.form['fecha_hora']
        fecha = fecha_hora.split('T')[0]
        hora = fecha_hora.split('T')[1]

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO agenda (nombre_tienda, fecha, hora) VALUES (%s, %s, %s)", (nombre_tienda, fecha, hora))
        mysql.connection.commit()
        cur.close()

        return redirect("https://calendar.google.com/calendar/u/0/r/eventedit?text=Visita%20a%20{}&dates={}T{}00Z/{}T{}00Z".format(nombre_tienda, fecha.replace('-', ''), hora.replace(':', ''), fecha.replace('-', ''), hora.replace(':', '')))

    return render_template('agendarVisita.html', tiendas=[nombre_tienda])

@app.route('/historial')
def historial():
    if 'correo' not in session:
        return redirect(url_for('login'))

    hoy = datetime.datetime.now().date()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM agenda ORDER BY fecha DESC, hora DESC")
    visitas = cur.fetchall()
    cur.close()

    visitas_anteriores = [v for v in visitas if v[2] < hoy]
    visitas_futuras = [v for v in visitas if v[2] >= hoy]

    return render_template('historial.html', anteriores=visitas_anteriores, futuras=visitas_futuras)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)






