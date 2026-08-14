import streamlit as st
from db_utils import inicializar_db, get_connection
from modulo_auth import render_login  # 🔐 Importación del módulo de login
import modulo_stock, modulo_ingreso, modulo_reservas, modulo_catalogo, modulo_ajustes
import modulo_compras 
import modulo_despachos 

# 1. Configuración de página
st.set_page_config(page_title="Sistema Sunrise", layout="wide")

# 2. Inicializar Base de Datos (Crea la tabla de usuarios si no existe)
inicializar_db()

# 3. Control de Estado de Autenticación
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['autenticado']:
    render_login()
else:
    # --- SISTEMA COMPLETO (Solo visible si inició sesión) ---
    
    # --- BARRA LATERAL ---
    st.sidebar.title("☀️ Sistema Sunrise")
    
    # Muestra el nombre del usuario logueado y botón para salir
    st.sidebar.write(f"👤 **{st.session_state['usuario']['nombre']}**")
    if st.sidebar.button("🔒 Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.session_state['usuario'] = None
        st.rerun()
        
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "Menú de Navegación",
        [
            "📊 Tablero de Stock", 
            "📥 Ingreso/Recepción", 
            "📝 Reservas y Salidas", 
            "🛒 Gestión de Compras", 
            "📦 Gestión de Despachos", 
            "📂 Catálogo", 
            "⚙️ Configuración"
        ]
    )

    st.sidebar.divider()

    # --- ZONA DE PELIGRO (Acciones de Limpieza con Guardado Forzado) ---
    with st.sidebar.expander("⚠️ Zona de Peligro"):
        st.write("Escribí **CONFIRMAR** para habilitar el borrado masivo.")
        clave = st.text_input("Clave de validación:", key="input_peligro")
        
        if clave == "CONFIRMAR":
            st.error("❗ ACCIONES CRÍTICAS")
            
            # OPCIÓN A: Vaciar el Stock (Movimientos)
            if st.button("🔥 VACIAR TODO EL STOCK"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM movimientos")
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("✅ Historial de stock eliminado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al borrar: {e}")
                
            # OPCIÓN B: Vaciar Catálogo + Stock
            if st.button("💀 RESET TOTAL (Catálogo + Stock)"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM movimientos")
                    cursor.execute("DELETE FROM productos")
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success("✅ Sistema reseteado por completo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al resetear: {e}")
        else:
            st.info("Escribí CONFIRMAR para ver opciones de borrado.")

    # --- ENRUTAMIENTO ---
    if menu == "📊 Tablero de Stock":
        modulo_stock.render()
    elif menu == "📥 Ingreso/Recepción":
        modulo_ingreso.render()
    elif menu == "📝 Reservas y Salidas":
        modulo_reservas.render()
    elif menu == "🛒 Gestión de Compras": 
        modulo_compras.render()
    elif menu == "📦 Gestión de Despachos": 
        modulo_despachos.render()
    elif menu == "📂 Catálogo":
        modulo_catalogo.render()
    elif menu == "⚙️ Configuración":
        modulo_ajustes.render()