import pandas as pd
import mysql.connector

# Leer CSV
df = pd.read_csv('arca_data.csv')

# Convertir columna geometry a latitud y longitud
def parse_geometry(geom):
    geom = geom.replace('POINT (', '').replace(')', '')
    lon, lat = geom.split()
    return float(lat), float(lon)

df[['latitud', 'longitud']] = df['geometry'].apply(lambda g: pd.Series(parse_geometry(g)))

# Conexión a MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='1505RMht',
    database='app_colaboradores'
)
cursor = conn.cursor()

# Limpiar tabla (opcional, para evitar duplicados)
cursor.execute("DELETE FROM tiendas")
conn.commit()

# Insertar los datos
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO tiendas (
            nombre, latitud, longitud, nps, fillfoundrate, 
            damage_rate, out_of_stock, complaint_resolution_time_hrs
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row['nombre'], row['latitud'], row['longitud'],
        row['nps'], row['fillfoundrate'],
        row['damage_rate'], row['out_of_stock'],
        row['complaint_resolution_time_hrs']
    ))

conn.commit()
cursor.close()
conn.close()

print("✅ Datos insertados correctamente.")
