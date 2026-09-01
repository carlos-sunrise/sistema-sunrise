import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes, obtener_lista_proveedores, obtener_lista_tipos, registrar_accion
from datetime import datetime

def render():
    st.header("📥 Recepción de Mercadería")
    
    # --- 1. CARGA DE DATOS DINÁMICOS Y ESTADO ---
    lista_provs = obtener_lista_proveedores()
    sedes = obtener_lista_sedes()

    if 'lista_remito_temporal' not in st.session_state:
        st.session_state['lista_remito_temporal'] = []
    if 'ingreso_tipo' not in st.session_state: st.session_state['ingreso_tipo'] = "Seleccione..."
    if 'ingreso_prod' not in st.session_state: st.session_state['ingreso_prod'] = "Seleccione..."
    if 'ingreso_cant' not in st.session_state: st.session_state['ingreso_cant'] = 1
    if 'remito_fijo' not in st.session_state: st.session_state['remito_fijo'] = ""
    if 'proveedor_fijo' not in st.session_state: st.session_state['proveedor_fijo'] = "Seleccione..."
    
    if 'usuario_actual' not in st.session_state: 
        st.session_state['usuario_actual'] = "Carlos (Administrador)"

    # Cargamos el catálogo
    conn_view = get_connection()
    prods_db = pd.read_sql("SELECT id, tipo, marca, modelo, proveedor FROM productos", conn_view)
    conn_view.close()

    # Sanitizamos cadenas de texto limpiando espacios vacíos
    prods_db['proveedor'] = prods_db['proveedor'].fillna('').astype(str).str.strip()
    prods_db['tipo'] = prods_db['tipo'].fillna('').astype(str).str.strip()
    prods_db['marca'] = prods_db['marca'].fillna('').astype(str).str.strip()
    prods_db['modelo'] = prods_db['modelo'].fillna('').astype(str).str.strip()

    prov_busqueda = st.session_state.proveedor_fijo.strip()

    # --- CALLBACKS ---
    def callback_agregar():
        if st.session_state.ingreso_prod != "Seleccione..." and st.session_state.remito_fijo != "":
            filt = prods_db[
                (prods_db['tipo'] == st.session_state.ingreso_tipo) & 
                (prods_db['proveedor'].str.lower().str.contains(prov_busqueda.lower(), regex=False))
            ]
            opciones = {f"{r['marca']} {r['modelo']}": r['id'] for _, r in filt.iterrows()}
            p_id = opciones.get(st.session_state.ingreso_prod)

            st.session_state['lista_remito_temporal'].append({
                'id': p_id,
                'Articulo': st.session_state.ingreso_prod,
                'Cantidad': st.session_state.ingreso_cant,
                'Destino': st.session_state.ingreso_dest
            })
            
            st.session_state.ingreso_tipo = "Seleccione..."
            st.session_state.ingreso_prod = "Seleccione..."
            st.session_state.ingreso_cant = 1
        else:
            st.error("Complete el remito y seleccione un producto.")

    def callback_confirmar_total():
        if not st.session_state['lista_remito_temporal']: return
        conn_save = get_connection()
        cursor = conn_save.cursor()
        
        fecha_seleccionada = st.session_state.fecha_remito_manual.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            for item in st.session_state['lista_remito_temporal']:
                info_nota = f"Remito: {st.session_state.remito_fijo} | Prov: {st.session_state.proveedor_fijo}"
                
                cursor.execute("""
                    INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (item['id'], item['Cantidad'], fecha_seleccionada, item['Destino'], info_nota))
                
                registrar_accion(
                    conn=conn_save,
                    usuario=st.session_state['usuario_actual'],
                    accion="INGRESO_REMITO",
                    detalles=f"Ingresó {item['Cantidad']} un. de {item['Articulo']} por Remito {st.session_state.remito_fijo} (Proveedor: {st.session_state.proveedor_fijo} -> Destino: {item['Destino']})",
                    producto_id=item['id'],
                    cliente=st.session_state.remito_fijo
                )
            
            cursor.execute("""
                INSERT INTO historial_remitos (nro_remito, proveedor, fecha, cantidad_items) 
                VALUES (%s, %s, %s, %s)
            """, (st.session_state.remito_fijo, st.session_state.proveedor_fijo, fecha_seleccionada, len(st.session_state['lista_remito_temporal'])))
            
            conn_save.commit()
            st.session_state['lista_remito_temporal'] = []
            st.session_state.remito_fijo = ""
            st.session_state.proveedor_fijo = "Seleccione..."
            st.success("Ingreso realizado con éxito en el stock local de la sede.")
        except Exception as e: 
            st.error(f"Error: {e}")
        finally: 
            cursor.close()
            conn_save.close()

    # --- INTERFAZ ---
    tab_ingreso, tab_historial = st.tabs(["🆕 Cargar Ingreso", "📜 Historial de Remitos"])

    with tab_ingreso:
        col_h1, col_h2, col_h3 = st.columns([1.5, 1.5, 1])
        with col_h1: 
            st.text_input("📄 Detalle General del Remito:", key="remito_fijo", autocomplete="off")
        with col_h2: 
            st.selectbox("🏭 Proveedor del Envío:", ["Seleccione..."] + lista_provs, key="proveedor_fijo")
        with col_h3:
            st.date_input("📅 Fecha de Ingreso:", value=datetime.now(), key="fecha_remito_manual")

        with st.container(border=True):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if prov_busqueda != "Seleccione...":
                    # Filtrado flexible sin importar mayúsculas/minúsculas ni espacios
                    df_prov_filtrado = prods_db[prods_db['proveedor'].str.lower().str.contains(prov_busqueda.lower(), regex=False)]
                    tipos_filtrados = sorted(df_prov_filtrado['tipo'].unique().tolist())
                    
                    if tipos_filtrados:
                        st.selectbox("Seleccionar Tipo:", ["Seleccione..."] + tipos_filtrados, key="ingreso_tipo")
                    else:
                        st.warning("⚠️ Sin productos asignados a este proveedor en el catálogo.")
                        st.selectbox("Seleccionar Tipo:", ["Seleccione..."], disabled=True, key="ingreso_tipo_dis")
                else: 
                    st.selectbox("Seleccionar Tipo:", ["Seleccione..."], disabled=True, key="ingreso_tipo_dis")
            
            with col_t2:
                if st.session_state.ingreso_tipo != "Seleccione..." and prov_busqueda != "Seleccione...":
                    filt = prods_db[
                        (prods_db['tipo'] == st.session_state.ingreso_tipo) & 
                        (prods_db['proveedor'].str.lower().str.contains(prov_busqueda.lower(), regex=False))
                    ]
                    opciones_prod = sorted([f"{r['marca']} {r['modelo']}" for _, r in filt.iterrows()])
                    st.selectbox("Seleccionar Producto:", ["Seleccione..."] + opciones_prod, key="ingreso_prod")
                else: 
                    st.selectbox("Seleccionar Producto:", ["Seleccione..."], disabled=True, key="ingreso_prod_dis")

            col_c1, col_c2 = st.columns(2)
            with col_c1: st.number_input("Cantidad:", min_value=1, key="ingreso_cant")
            with col_c2: st.selectbox("Destino:", sedes, index=0, key="ingreso_dest")
            st.button("➕ AGREGAR", on_click=callback_agregar)

        if st.session_state['lista_remito_temporal']:
            st.write("---")
            df_temp = pd.DataFrame(st.session_state['lista_remito_temporal'])
            st.dataframe(df_temp[['Articulo', 'Cantidad', 'Destino']], use_container_width=True, hide_index=True)
            
            c_fin1, c_fin2 = st.columns(2)
            c_fin1.button("💾 CONFIRMAR INGRESO TOTAL", on_click=callback_confirmar_total)
            if c_fin2.button("🗑️ Cancelar Todo"):
                st.session_state['lista_remito_temporal'] = []
                st.rerun()

    with tab_historial:
        st.subheader("Registros de Mercadería Recibida")
        conn_hist = get_connection()
        try:
            df_historial = pd.read_sql("SELECT fecha, nro_remito, proveedor, cantidad_items FROM historial_remitos ORDER BY fecha DESC", conn_hist)
            
            if not df_historial.empty:
                df_historial['fecha_dt'] = pd.to_datetime(df_historial['fecha'])
                df_historial['fecha'] = df_historial['fecha_dt'].dt.strftime('%d/%m/%y')

                detalle_placeholder = st.container()

                st.write("### Lista de Remitos")
                seleccion = st.dataframe(
                    df_historial[['fecha', 'nro_remito', 'proveedor', 'cantidad_items']], 
                    use_container_width=True, 
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )

                if len(seleccion.selection.rows) > 0:
                    idx = seleccion.selection.rows[0]
                    remito_sel = df_historial.iloc[idx]['nro_remito']
                    proveedor_sel = df_historial.iloc[idx]['proveedor']
                    
                    with detalle_placeholder:
                        with st.container(border=True):
                            st.markdown(f"### 📦 DETALLE DESPLEGADO: Remito `{remito_sel}`")
                            
                            query_detalle = """
                                SELECT m.cantidad, m.asignacion as destino, CONCAT(p.marca, ' ', p.modelo) as articulo
                                FROM movimientos m
                                JOIN productos p ON m.producto_id = p.id
                                WHERE m.nota LIKE %s
                            """
                            df_detalle = pd.read_sql(query_detalle, conn_hist, params=(f"Remito: {remito_sel} | %%",))
                            st.dataframe(df_detalle, use_container_width=True, hide_index=True)
                            
                            col_act1, col_act2, col_act3 = st.columns([2, 1.2, 1])
                            
                            with col_act2.popover("⚙️ Editar Encabezado"):
                                nuevo_nro = st.text_input("Nro Remito:", value=str(remito_sel))
                                nuevo_prov = st.selectbox("Proveedor:", lista_provs, index=lista_provs.index(proveedor_sel) if proveedor_sel in lista_provs else 0)
                                if st.button("Guardar Cambios", key=f"save_rem_{remito_sel}", type="primary", use_container_width=True):
                                    cursor_hist = conn_hist.cursor()
                                    cursor_hist.execute("UPDATE historial_remitos SET nro_remito = %s, proveedor = %s WHERE nro_remito = %s", (nuevo_nro, nuevo_prov, str(remito_sel)))
                                    nueva_nota_mov = f"Remito: {nuevo_nro} | Prov: {nuevo_prov}"
                                    cursor_hist.execute("UPDATE movimientos SET nota = %s WHERE nota LIKE %s", (nueva_nota_mov, f"Remito: {remito_sel} | %%"))
                                    
                                    registrar_accion(
                                        conn=conn_hist,
                                        usuario=st.session_state['usuario_actual'],
                                        accion="EDITAR_REMITO",
                                        detalles=f"Modificó el encabezado del Remito: {remito_sel} -> Nuevo Nro: {nuevo_nro} | Nuevo Prov: {nuevo_prov}",
                                        cliente=str(nuevo_nro)
                                    )
                                    
                                    conn_hist.commit()
                                    cursor_hist.close()
                                    st.success("Cambios aplicados.")
                                    st.rerun()

                            if col_act3.button("🗑️ Anular", key=f"del_rem_{remito_sel}", type="secondary", use_container_width=True):
                                cursor_hist = conn_hist.cursor()
                                cursor_hist.execute("DELETE FROM movimientos WHERE nota LIKE %s", (f"Remito: {remito_sel} | %%",))
                                cursor_hist.execute("DELETE FROM historial_remitos WHERE nro_remito = %s", (str(remito_sel),))
                                
                                registrar_accion(
                                    conn=conn_hist,
                                    usuario=st.session_state['usuario_actual'],
                                    accion="ANULAR_REMITO",
                                    detalles=f"Anuló por completo el Remito Nro: {remito_sel} eliminando sus registros del inventario local.",
                                    cliente=str(remito_sel)
                                )
                                
                                conn_hist.commit()
                                cursor_hist.close()
                                st.error(f"Remito {remito_sel} anulado.")
                                st.rerun()
                                
                            st.info("Para cerrar este detalle y seguir viendo la lista, deselecciona la fila o abre otro remito.")
            else:
                st.info("No hay remitos registrados.")
                
        except Exception as e: st.error(f"Error: {e}")
        finally: conn_hist.close()