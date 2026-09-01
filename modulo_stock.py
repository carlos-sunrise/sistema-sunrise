import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes

def render():
    st.header("📊 Inventario Detallado")
    conn = get_connection()

    # --- 1. CONSULTA SQL CON TRAZABILIDAD POR PROVEEDOR DE INGRESO ---
    # Extraemos el proveedor real indicado en el remito/compra desde m.nota
    query_stock = """
        SELECT 
            p.tipo, 
            p.marca, 
            p.modelo, 
            CASE 
                WHEN m.nota LIKE '%%Prov: %%' THEN 
                    CASE 
                        WHEN INSTR(SUBSTR(m.nota, INSTR(m.nota, 'Prov: ') + 6), ' |') > 0 THEN
                            SUBSTR(SUBSTR(m.nota, INSTR(m.nota, 'Prov: ') + 6), 1, INSTR(SUBSTR(m.nota, INSTR(m.nota, 'Prov: ') + 6), ' |') - 1)
                        ELSE 
                            SUBSTR(m.nota, INSTR(m.nota, 'Prov: ') + 6)
                    END
                ELSE p.proveedor 
            END as proveedor_real,
            m.asignacion as sede_real, 
            SUM(m.cantidad) as saldo_neto,
            p.u
        FROM productos p 
        INNER JOIN movimientos m ON p.id = m.producto_id 
        GROUP BY p.id, p.tipo, p.marca, p.modelo, m.asignacion, p.u, proveedor_real
        HAVING saldo_neto > 0
        ORDER BY p.tipo, p.marca, p.modelo, proveedor_real
    """
    
    try:
        df_tablero = pd.read_sql(query_stock, conn)

        if df_tablero.empty:
            st.info("No hay stock disponible registrado actualmente.")
        else:
            # --- 2. PREPARACIÓN DE SEDES ---
            sedes_maestras = obtener_lista_sedes()
            sedes_con_stock = df_tablero['sede_real'].unique().tolist()
            sedes_finales = [s for s in sedes_maestras if s in sedes_con_stock]

            # --- 3. RENDERIZADO CON EXPANDERS ---
            for sede in sedes_finales:
                df_sede = df_tablero[df_tablero['sede_real'] == sede].copy()
                
                if not df_sede.empty:
                    es_bsas = "Bs. As." in sede or "Buenos Aires" in sede
                    
                    with st.expander(f"📍 Ubicación: {sede}", expanded=es_bsas):
                        df_viz = df_sede[['tipo', 'marca', 'modelo', 'proveedor_real', 'saldo_neto', 'u']]
                        df_viz.columns = ["Tipo", "Marca", "Modelo", "Proveedor Real", "Cantidad Disponible", "Unidad"]
                        
                        st.dataframe(
                            df_viz, 
                            hide_index=True, 
                            use_container_width=True
                        )
                        
    except Exception as e:
        st.error(f"❌ Error al consultar el inventario: {e}")
        
    finally:
        conn.close()