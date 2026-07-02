import sqlite3
import mysql.connector

# 🎛️ CREDENCIALES REALES DE TU BASE DE DATOS EN LA NUBE (CLEVER CLOUD)
MYSQL_CONFIG = {
    "host": "bl2wob5vcaauhtanv43m-mysql.services.clever-cloud.com",
    "user": "uojdd5bwojumkqin",
    "password": "MxdIvtqroa0v7PfaeXL5",
    "database": "bl2wob5vcaauhtanv43m",
    "port": 3306
}

def migrar_todo():
    print("🚀 Conectando a las bases de datos para iniciar la migración...")
    
    # 1. Abrimos las conexiones a ambas bases de datos
    try:
        conn_sqlite = sqlite3.connect("sistema_sunrise.db")
        cursor_sqlite = conn_sqlite.cursor()
        
        conn_mysql = mysql.connector.connect(**MYSQL_CONFIG)
        cursor_mysql = conn_mysql.cursor()
    except Exception as e:
        print(f"❌ Error al conectar con las bases de datos: {e}")
        return

    # 2. Forzamos a MySQL a que cree las tablas en blanco de forma correcta antes de migrar
    print("🛠️ Inicializando estructura de tablas en MySQL...")
    try:
        import db_utils
        db_utils.inicializar_db()
        print("   ✅ Estructura de tablas validada.")
    except Exception as e:
        print(f"❌ Error al inicializar las tablas en MySQL desde db_utils: {e}")
        return
    
    # Listado de tus tablas en el orden correcto para respetar claves foráneas
    tablas = ["sedes", "proveedores", "tipos_equipo", "productos", "movimientos", "historial_remitos", "log_auditoria"]
    
    print("\n📦 Iniciando traspaso de datos...")
    
    for tabla in tablas:
        print(f"⏳ Procesando tabla: '{tabla}'...")
        
        try:
            # A. Leer los datos desde tu SQLite local
            cursor_sqlite.execute(f"SELECT * FROM {tabla}")
            filas = cursor_sqlite.fetchall()
            
            if not filas:
                print(f"   ℹ️ La tabla '{tabla}' no contiene registros en tu máquina local. Saltando...")
                continue
                
            # B. Limpiar la tabla en MySQL por seguridad (por si hiciste pruebas previas)
            cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor_mysql.execute(f"TRUNCATE TABLE {tabla};")
            cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 1;")
            
            # C. Armar la consulta dinámica basada en la cantidad de columnas de la tabla
            num_columnas = len(filas[0])
            marcadores = ", ".join(["%s"] * num_columnas)
            query_insert = f"INSERT INTO {tabla} VALUES ({marcadores})"
            
            # D. Inyectar todos los registros de golpe (Masivo)
            cursor_mysql.executemany(query_insert, filas)
            conn_mysql.commit()
            print(f"   ✅ ¡Éxito! Se subieron {len(filas)} registros a la nube.")
            
        except Exception as e:
            print(f"   ❌ Error crítico al migrar la tabla '{tabla}': {e}")
            
    # 3. Cerrar los accesos de forma ordenada
    cursor_sqlite.close()
    conn_sqlite.close()
    cursor_mysql.close()
    conn_mysql.close()
    
    print("\n🏁 🎉 ¡MIGRACIÓN COMPLETADA CON ÉXITO!")
    print("Ya podés ejecutar tu comando habitual: streamlit run main.py")

if __name__ == "__main__":
    migrar_todo()