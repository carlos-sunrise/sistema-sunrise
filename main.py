import streamlit as st
from db_utils import inicializar_db, get_connection
import modulo_stock, modulo_ingreso, modulo_reservas, modulo_catalogo, modulo_ajustes
import modulo_compras  # ◄--- 1. IMPORTACIÓN DEL NUEVO MÓDULO
import modulo_despachos  # 📦 AGREGADO: Importación del módulo de despachos

# 1. Configuración de página
st.set_page_config(page_title="Sistema Sunrise", layout="wide")

# 2. Inicializar Base de Datos
inicializar_db()

# --- BARRA LATERAL ---
st.sidebar.title("☀️ Sistema Sunrise")
menu = st.sidebar.radio(
    "Menú de Navegación",
    [
        "📊 Tablero de Stock", 
        "📥 Ingreso/Recepción", 
        "📝 Reservas y Salidas", 
        "🛒 Gestión de Compras",  # ◄--- 2. AGREGADO AL MENÚ DE NAVEGACIÓN
        "📦 Gestión de Despachos",  # 📦 AGREGADO: Opción para Formosa / Bolívar
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
                # Usamos 'with' para asegurar que el COMMIT se haga sí o sí
                with get_connection() as conn:
                    conn.execute("DELETE FROM movimientos")
                    # Reinicia el contador de IDs
                    conn.execute("DELETE FROM sqlite_sequence WHERE name='movimientos'")
                st.success("✅ Historial de stock eliminado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar: {e}")
            
        # OPCIÓN B: Vaciar Catálogo + Stock
        if st.button("💀 RESET TOTAL (Catálogo + Stock)"):
            try:
                with get_connection() as conn:
                    conn.execute("DELETE FROM movimientos")
                    conn.execute("DELETE FROM productos")
                    conn.execute("DELETE FROM sqlite_sequence WHERE name='movimientos'")
                    conn.execute("DELETE FROM sqlite_sequence WHERE name='productos'")
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
elif menu == "🛒 Gestión de Compras":  # ◄--- 3. RENDERIZADO DE LA NUEVA PANTALLA
    modulo_compras.render()
elif menu == "📦 Gestión de Despachos":  # 📦 AGREGADO: Enrutamiento al render de despachos
    modulo_despachos.render()
elif menu == "📂 Catálogo":
    modulo_catalogo.render()
elif menu == "⚙️ Configuración":
    modulo_ajustes.render()