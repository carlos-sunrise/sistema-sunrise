import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes
from datetime import datetime
import re

def render():
    st.header("📦 Módulo de Gestión de Despachos (Inter-Sedes)")
    conn = get_connection()
    lista_sedes = obtener_lista_sedes()

    # --- CONTROL DE PESTAÑAS INTERNAS ---
    if "pestana_despachos" not in st.session_state:
        st.session_state["pestana_despachos"] = "🟡 Por Despachar"

    c_tab1, c_tab2 = st.columns(2)
    if c_tab1.button("🟡 Por Despachar / En Galpón", use_container_width=True, type="primary" if st.session_state["pestana_despachos"] == "🟡 Por Despachar" else "secondary"):
        st.session_state["pestana_despachos"] = "🟡 Por Despachar"; st.rerun()
    if c_tab2.button("🟢 Despachado (Historial Cerrado)", use_container_width=True, type="primary" if st.session_state["pestana_despachos"] == "🟢 Despachado" else "secondary"):
        st.session_state["pestana_despachos"] = "🟢 Despachado"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ====================================================
    # LECTURA DE MOVIMIENTOS CON MARCA DE DESPACHO
    # ====================================================
    query_despachos = """
        SELECT m.id, m.producto_id, p.tipo, p.marca, p.modelo, 
               m.nota, m.asignacion as sede_destino, m.fecha
        FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE m.nota LIKE '%%Despacho:%%'
        ORDER BY m.fecha DESC
    """
    df_db = pd.read_sql(query_despachos, conn)

    listado_despachos = []
    if not df_db.empty:
        for _, r in df_db.iterrows():
            nota_c = r['nota']
            
            # 🎯 REGLA ESTRICTA DE ESTADO: Solo está 'Listo en Galpón' si fue RECIBIDO previamente
            if "Despacho: PENDIENTE" in nota_c:
                if " | RECIBIDO" in nota_c:
                    estado_desp = "Listo en Galpón"
                else:
                    estado_desp = "Por recibir"
            elif "Despacho: ENVIADO" in nota_c or "Despacho: RECIBIDO IN DESTINO" in nota_c or "Despacho: EN VIAJE" in nota_c:
                estado_desp = "Despachado"
            else:
                continue

            # Parseo seguro para extraer la cantidad
            match_cant = re.search(r'(?:F:|Cant:|Cantidad:)\s*(\d+)', nota_c, re.IGNORECASE)
            cant_val = int(match_cant.group(1)) if match_cant and int(match_cant.group(1)) != 0 else 1

            try:
                if "Compra Directa: " in nota_c:
                    detalle_origen = nota_c.split("Compra Directa: ")[1].split(" | ")[0]
                else:
                    detalle_origen = nota_c.split("Reserva: ")[1].split(" | ")[0]
            except:
                detalle_origen = "Reposición de Stock"

            listado_despachos.append({
                'id_mov_origen': r['id'],
                'producto_id': r['producto_id'],
                'equipo': f"{r['tipo']} {r['marca']} {r['modelo']}",
                'cantidad': cant_val,  
                'sede_destino': r['sede_destino'],
                'fecha_carga': r['fecha'],
                'estado': estado_desp,
                'detalle': detalle_origen,
                'nota_completa': nota_c
            })

    df_despachos = pd.DataFrame(listado_despachos) if listado_despachos else pd.DataFrame(columns=['id_mov_origen', 'producto_id', 'equipo', 'cantidad', 'sede_destino', 'fecha_carga', 'estado', 'detalle', 'nota_completa'])

    # ====================================================
    # 🟡 PESTAÑA 1: POR DESPACHAR (AGRUPADO POR CLIENTE / OBRA)
    # ====================================================
    if st.session_state["pestana_despachos"] == "🟡 Por Despachar":
        df_prep = df_despachos[df_despachos['estado'].isin(["Listo en Galpón", "Por recibir"])]
        
        if df_prep.empty:
            st.success("🎉 ¡No tenés mercadería pendiente de despacho para Formosa o Bolívar!")
        else:
            for cliente_desp in df_prep['detalle'].unique():
                df_cli_desp = df_prep[df_prep['detalle'] == cliente_desp]
                destino_cli = df_cli_desp.iloc[0]['sede_destino']
                
                with st.container(border=True):
                    st.markdown(f"#### 👤 Cliente / Obra: **{cliente_desp}** | 📍 Destino: :blue[**{destino_cli}**]")
                    st.write("---")
                    
                    for _, item in df_cli_desp.iterrows():
                        col1, col2, col3 = st.columns([2.5, 1.5, 1.3])
                        col1.markdown(f"📦 **{item['equipo']}**")
                        col1.write(f"📅 Carga: {item['fecha_carga']}")
                        
                        if item['estado'] == "Por recibir":
                            col2.markdown(f"🔢 Cantidad: **{item['cantidad']}** (⚠️ :orange[**Por recibir en Galpón**])")
                            boton_deshabilitado = True
                        else:
                            col2.markdown(f"🔢 Cantidad: **{item['cantidad']}** (✅ :green[**Listo en Galpón**])")
                            boton_deshabilitado = False
                            
                        if col3.button("🚀 Despachar", key=f"btn_go_{item['id_mov_origen']}", type="primary", use_container_width=True, disabled=boton_deshabilitado):
                            nueva_nota_origen = item['nota_completa'].replace("Despacho: PENDIENTE", "Despacho: ENVIADO") + f" | F.Despacho: {datetime.now().strftime('%Y-%m-%d')}"
                            cursor = conn.cursor()
                            cursor.execute("UPDATE movimientos SET nota = %s WHERE id = %s", (nueva_nota_origen, item['id_mov_origen']))
                            conn.commit()
                            cursor.close()
                            st.toast(f"¡Artículo despachado correctamente hacia {item['sede_destino']}!", icon="🚀")
                            st.rerun()

    # ====================================================
    # 🟢 PESTAÑA 2: DESPACHADO (HISTORIAL CERRADO)
    # ====================================================
    if st.session_state["pestana_despachos"] == "🟢 Despachado":
        df_enviados = df_despachos[df_despachos['estado'] == "Despachado"]
        
        if df_enviados.empty:
            st.info("No hay registros de despachos finalizados en el historial.")
        else:
            df_viz = df_enviados[['fecha_carga', 'equipo', 'cantidad', 'sede_destino', 'detalle']].copy()
            df_viz.columns = ["Fecha Carga", "Equipo / Modelo", "Cantidad", "Sede Destino", "Origen / Detalle"]
            st.dataframe(df_viz, hide_index=True, use_container_width=True)

    conn.close()