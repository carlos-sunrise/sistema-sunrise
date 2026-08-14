import mysql.connector
from datetime import datetime

# 🎛️ CONFIGURACIÓN DE ACCESO EN LA NUBE (CLEVER CLOUD)
MYSQL_CONFIG = {
    "host": "bl2wob5vcaauhtanv43m-mysql.services.clever-cloud.com",
    "user": "uojdd5bwojumkqin",
    "password": "MxdIvtqroa0v7PfaeXL5",
    "database": "bl2wob5vcaauhtanv43m",
    "port": 3306
}

def get_connection():
    # Conexión a la base de datos en la nube (MySQL)
    return mysql.connector.connect(**MYSQL_CONFIG)

def inicializar_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    charset_config = "DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    
    # 1. Crear tablas maestras para los desplegables dinámicos
    cursor.execute(f"CREATE TABLE IF NOT EXISTS sedes (nombre VARCHAR(100) PRIMARY KEY) {charset_config}")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS proveedores (nombre VARCHAR(100) PRIMARY KEY) {charset_config}")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS tipos_equipo (nombre VARCHAR(100) PRIMARY KEY) {charset_config}")
    
    # 2. Crear tabla de productos (Catálogo)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS productos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tipo VARCHAR(100),
            marca VARCHAR(100),
            modelo VARCHAR(100),
            u TEXT,
            proveedor VARCHAR(255)
        ) {charset_config}
    """)
    
    # --- LÓGICA DE ACTUALIZACIÓN DE TABLA ---
    try:
        cursor.execute("ALTER TABLE productos MODIFY COLUMN u TEXT")
    except mysql.connector.Error:
        # Si ya existe la columna en MySQL, ignoramos el error de duplicado
        pass

    # 3. Crear tabla de movimientos (Stock y Reservas)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            producto_id INT,
            cantidad INT,
            fecha VARCHAR(50),
            asignacion VARCHAR(100),
            nota VARCHAR(500),
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        ) {charset_config}
    """)

    # 4. NUEVA: Crear tabla de historial de remitos (Registro de Recepción)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS historial_remitos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nro_remito VARCHAR(100),
            proveedor VARCHAR(100),
            fecha VARCHAR(50),
            cantidad_items INT
        ) {charset_config}
    """)
    
    # 5. NUEVA: Tabla de Auditoría para el Historial de Acciones de Usuarios
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha_hora VARCHAR(50),
            usuario VARCHAR(100),
            accion VARCHAR(100),
            detalles VARCHAR(1000),
            producto_id INT,
            cliente VARCHAR(150)
        ) {charset_config}
    """)
    # 6. NUEVA: Tabla de Usuarios para el Login
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            rol VARCHAR(20) DEFAULT 'usuario',
            activo BOOLEAN DEFAULT TRUE
        ) {charset_config}
    """)
    conn.commit()
    cursor.close()
    conn.close()

# --- FUNCIONES PARA DESPLEGABLES DINÁMICOS ---

def obtener_lista_sedes():
    """Retorna la lista de sedes con el orden de prioridad solicitado."""
    conn = get_connection()
    cursor = conn.cursor()
    orden_prioridad = ["Buenos Aires", "Formosa", "Bolivar", "Ruka"]
    
    # Obtenemos lo que hay en la base de datos
    cursor.execute("SELECT nombre FROM sedes")
    res = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    # Si la base de datos está vacía, devolvemos el orden base para no romper los selectores
    if not res:
        return orden_prioridad
    
    # Retornamos primero las prioritarias y luego las demás en orden alfabético
    prioritarias = [s for s in orden_prioridad if s in res]
    otras = sorted([s for s in res if s not in orden_prioridad])
    return prioritarias + otras

def obtener_lista_proveedores():
    """Retorna la lista de proveedores registrados en la base de datos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM proveedores ORDER BY nombre ASC")
    res = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return res

def obtener_lista_tipos():
    """Retorna la lista de tipos de equipo registrados en la base de datos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM tipos_equipo ORDER BY nombre ASC")
    res = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return res

# --- FUNCIÓN MAESTRA DE AUDITORÍA ---

def registrar_accion(conn, usuario, accion, detalles, producto_id=None, cliente=None):
    """Inserta de forma segura un registro de auditoría en la base de datos."""
    cursor = conn.cursor()
    query = """
        INSERT INTO log_auditoria (fecha_hora, usuario, accion, detalles, producto_id, cliente)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(query, (fecha_actual, usuario, accion, detalles, producto_id, cliente))
    cursor.close()