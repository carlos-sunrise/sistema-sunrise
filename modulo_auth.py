import streamlit as st
import hashlib
from db_utils import get_connection

def hash_password(password):
    """Encripta la contraseña con SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def verificar_credenciales(username, password):
    """Verifica el usuario y la clave en MySQL."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        pwd_hash = hash_password(password)
        
        query = "SELECT * FROM usuarios WHERE username = %s AND password_hash = %s AND activo = TRUE"
        cursor.execute(query, (username, pwd_hash))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if usuario:
            return True, usuario
        return False, None
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return False, None

def crear_usuario_inicial():
    """Crea el usuario 'admin' la primera vez si la tabla está vacía."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Crea usuario por defecto: admin / sunrise123
            pwd_hash = hash_password("sunrise123")
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (%s, %s, %s, %s)",
                ('admin', pwd_hash, 'Administrador Sunrise', 'admin')
            )
            conn.commit()
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error al verificar/crear usuario inicial: {e}")

def render_login():
    """Dibuja la pantalla de login."""
    crear_usuario_inicial() # Asegura que exista al menos el usuario admin
    
    st.markdown("<h2 style='text-align: center;'>🌅 Sistema Sunrise</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Inicio de Sesión</h4>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.warning("Por favor complete todos los campos.")
                else:
                    es_valido, usuario = verificar_credenciales(username, password)
                    if es_valido:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = usuario
                        st.success(f"Bienvenido {usuario['nombre']}")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")