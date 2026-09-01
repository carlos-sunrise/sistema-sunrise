import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_proveedores, obtener_lista_sedes, registrar_accion  # 📜 Importamos la función de auditoría
from datetime import datetime
import re

def render():
    st.header("🛒 Módulo de Gestión de Compras")
    conn = get_connection()
    lista_proveedores_gral = obtener_lista_proveedores()
    lista_sedes = obtener_lista_sedes()

    # --- INICIALIZACIÓN DEL CARRITO TEMPORAL DE CARGA MÚLTIPLE ---
    if "carrito_compras" not in st.session_state:
        st.session_state["carrito_compras"] = []
        
    # --- MANEJO DE LLAVES DINÁMICAS PARA LIMPIEZA AUTOMÁTICA DEL FORMULARIO ---
    if "form_version" not in st.session_state:
        st.session_state["form_version"] = 0
    
    version = st.session_state["form_version"]

    # --- CONTROL RESERVADO DE PESTAÑA FIJA CONTRA REBOOTS ---
    if "pestana_compras_fija" not in st.session_state:
        st.session_state["pestana_compras_fija"] = "🟡 Comprados"
        
    # 👤 PASO PREVIO MULTIUSUARIO: Resguardo de sesión administrativa
    if 'usuario_actual' not in st.session_state: 
        st.session_state['usuario_actual'] = "Carlos (Administrador)"

    # ====================================================
    # 🔄 SECCIÓN DE CARGA: FILTRADO DESDE EL PROVEEDOR
    # ====================================================
    with st.expander("➕ Cargar Nueva Compra Realizada (Carga Múltiple - En Camino)", expanded=False):
        with st.container():
            col_add1, col_add2 = st.columns(2)
            
            prov_compra_dir = col_add1.selectbox(
                "🏢 Seleccionar Proveedor donde se compró:", 
                ["Seleccione..."] + lista_proveedores_gral, 
                key=f"prov_form_{version}"
            )
            
            id_prod_sel = None
            prod_label = ""
            
            if prov_compra_dir != "Seleccione...":
                df_tipos_filtrados = pd.read_sql("""
                    SELECT DISTINCT tipo 
                    FROM productos 
                    WHERE proveedor LIKE %s 
                    ORDER BY tipo ASC
                """, conn, params=(f"%{prov_compra_dir}%",))
                
                if df_tipos_filtrados.empty:
                    col_add1.warning(f"⚠️ No hay productos asociados a {prov_compra_dir} en el catálogo.")
                    tipo_sel = "Seleccione..."
                else:
                    tipo_sel = col_add1.selectbox(
                        "🔍 Filtrar por Tipo de Equipo:", 
                        ["Seleccione..."] + df_tipos_filtrados['tipo'].tolist(),
                        key=f"tipo_sel_form_{version}"
                    )
                
                if prov_compra_dir != "Seleccione..." and tipo_sel != "Seleccione...":
                    df_prods_drop = pd.read_sql("""
                        SELECT id, CONCAT(tipo, ' ', marca, ' ', modelo) as eq 
                        FROM productos 
                        WHERE proveedor LIKE %s AND tipo = %s
                        ORDER BY marca, modelo ASC
                    """, conn, params=(f"%{prov_compra_dir}%", tipo_sel))
                else:
                    df_prods_drop = pd.DataFrame(columns=['id', 'eq'])

                if not df_prods_drop.empty:
                    prod_label = col_add1.selectbox("📦 Seleccionar Modelo:", df_prods_drop['eq'], key=f"prod_sel_form_{version}")
                    id_prod_sel = df_prods_drop[df_prods_drop['eq'] == prod_label].iloc[0]['id']
                elif tipo_sel != "Seleccione...":
                    st.info("No hay modelos disponibles para esta selección.")
            else:
                col_add1.info("💡 Seleccioná un proveedor para ver sus rubros y equipos disponibles.")
                tipo_sel = "Seleccione..."
                
            sede_destino = col_add2.selectbox("📍 Destino / Sede:", lista_sedes, key=f"sede_sel_form_{version}")
            cant_compra = col_add2.number_input("🔢 Cantidad comprada:", min_value=1, step=1, key=f"cant_form_{version}")
            num_pedido = col_add2.text_input("📦 N° de Pedido / Orden:", placeholder="Ej: Pedido #1042", key=f"numped_form_{version}", autocomplete="off")
            detalle_dir = col_add2.text_input("📝 Detalle / Nota extra:", placeholder="Ej: Compra según Excel de Lucas", key=f"nota_form_{version}", autocomplete="off")
            
            st.write("")
            col_btn1, col_btn2 = st.columns(2)
            
            if col_btn1.button("➕ Añadir Producto a la Lista", use_container_width=True):
                if prov_compra_dir == "Seleccione...":
                    st.error("Por favor, selecciona primero un Proveedor.")
                elif tipo_sel == "Seleccione...":
                    st.error("Por favor, selecciona un Tipo de equipo.")
                elif id_prod_sel is None:
                    st.error("Por favor, selecciona un Modelo válido.")
                else:
                    st.session_state["carrito_compras"].append({
                        "producto_id": int(id_prod_sel),
                        "equipo": prod_label,
                        "cantidad": int(cant_compra),
                        "num_pedido": num_pedido.strip() if num_pedido.strip() else "-",
                        "sede": sede_destino,
                        "proveedor": prov_compra_dir,
                        "detalle": detalle_dir if detalle_dir else "Reposición Stock"
                    })
                    st.toast(f"¡{prod_label} añadido a la lista!")
                    st.session_state["form_version"] += 1
                    st.session_state["pestana_compras_fija"] = "🟡 Comprados"
                    st.rerun()

            if st.session_state["carrito_compras"]:
                if col_btn2.button("🗑 Vaciar Lista Temporal", type="secondary", use_container_width=True):
                    st.session_state["carrito_compras"] = []
                    st.session_state["form_version"] += 1
                    st.rerun()

        if st.session_state["carrito_compras"]:
            st.markdown("##### 📝 Productos listos para procesar:")
            df_temp = pd.DataFrame(st.session_state["carrito_compras"])
            df_mostrar = df_temp[["equipo", "cantidad", "proveedor", "num_pedido", "sede", "detalle"]].copy()
            df_mostrar.columns = ["Equipo", "Cant.", "Proveedor", "N° Pedido", "Sede Destino", "Nota"]
            st.dataframe(df_mostrar, hide_index=True, use_container_width=True)
            
            if st.button("🚀 CONFIRMAR COMPRA Y ENVIAR TODO EN CAMINO", type="primary", use_container_width=True):
                cursor = conn.cursor()
                for item in st.session_state["carrito_compras"]:
                    if item['sede'] in ["Formosa", "Bolivar"]:
                        tag_despacho = " | Despacho: PENDIENTE"
                    else:
                        tag_despacho = ""
                        
                    ped_str = f" | Pedido: {item['num_pedido']}" if item['num_pedido'] != "-" else ""
                    nota_directa = f"Compra Directa: {item['detalle']}{ped_str} | F: {item['cantidad']} | Prov: {item['proveedor']}{tag_despacho}"
                    
                    cursor.execute("""
                        INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) 
                        VALUES (%s, 0, %s, %s, %s)
                    """, (item['producto_id'], datetime.now().strftime("%Y-%m-%d"), item['sede'], nota_directa))
                    
                    registrar_accion(
                        conn=conn,
                        usuario=st.session_state['usuario_actual'],
                        accion="COMPRA_EN_CAMINO",
                        detalles=f"Registrió orden de compra directa en camino (Ped: {item['num_pedido']}): {item['cantidad']} un. de {item['equipo']} (Prov: {item['proveedor']} | Destino: {item['sede']})",
                        producto_id=item['producto_id'],
                        cliente=item['detalle']
                    )
                
                conn.commit()
                cursor.close()
                st.session_state["carrito_compras"] = []
                st.session_state["form_version"] += 1
                st.session_state["pestana_compras_fija"] = "🟡 Comprados"
                st.success("¡Excelente! Todos los productos se registraron en 'Comprados'.")
                st.rerun()

    st.markdown("---")

    # ====================================================
    # LECTURA Y PROCESAMIENTO DE LAS PESTAÑAS
    # ====================================================
    query_compras = """
        SELECT m.id, m.producto_id, p.tipo, p.marca, p.modelo, p.proveedor as prov_original,
               m.nota, m.asignacion as sede, m.fecha
        FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE (m.nota LIKE 'Reserva: %%' OR m.nota LIKE 'Compra Directa: %%' OR m.nota LIKE 'Reserva Inter-Sede:%%')
        ORDER BY m.fecha DESC
    """
    df_c = pd.read_sql(query_compras, conn)

    listado = []
    if not df_c.empty:
        for _, r in df_c.iterrows():
            nota_orig = r['nota']
            es_directa = "Compra Directa: " in nota_orig
            
            if es_directa:
                separador = "Compra Directa: "
            elif "Reserva Inter-Sede:" in nota_orig:
                separador = "Reserva Inter-Sede: "
            else:
                separador = "Reserva: "
            
            try:
                partes_f = nota_orig.split(" | F: ")
                cant_faltante = int(partes_f[1].split(" | ")[0]) if len(partes_f) > 1 else 0
                origen_full = partes_f[0].replace(separador, "")
            except:
                cant_faltante = 0
                origen_full = "Desconocido"

            if " | Pedido: " in nota_orig:
                num_pedido_db = nota_orig.split(" | Pedido: ")[1].split(" | ")[0]
            else:
                num_pedido_db = "-"
            
            if " | RECIBIDO" in nota_orig:
                estado = "🟢 Recibido"
                if " | Prov: " in nota_orig:
                    prov_compra = nota_orig.split(" | Prov: ")[1].split(" | ")[0]
                elif " | COMPRADO: " in nota_orig:
                    prov_compra = nota_orig.split(" | COMPRADO: ")[1].split(" | ")[0]
                else:
                    prov_compra = r['prov_original']
            elif " | Prov: " in nota_orig:
                estado = "🟡 Comprado"
                prov_compra = nota_orig.split(" | Prov: ")[1].split(" | ")[0]
            elif " | COMPRADO: " in nota_orig:
                estado = "🟡 Comprado"
                prov_compra = nota_orig.split(" | COMPRADO: ")[1].split(" | ")[0]
            else:
                estado = "🔴 Pendiente de compra"
                prov_compra = "Sin asignar"
                
            if estado == "🔴 Pendiente de compra" and cant_faltante == 0:
                continue

            listado.append({
                'id_mov': r['id'],
                'prod_id': r['producto_id'],
                'equipo': f"{r['tipo']} {r['marca']} {r['modelo']}",
                'origen': origen_full,
                'es_manual': es_directa,
                'sede': r['sede'],
                'cantidad': cant_faltante,
                'estado': estado,
                'prov_compra': prov_compra,
                'prov_catalogo': r['prov_original'],
                'num_pedido': num_pedido_db,
                'nota_completa': nota_orig
            })
        
    df_listado = pd.DataFrame(listado) if listado else pd.DataFrame(columns=['id_mov', 'prod_id', 'equipo', 'origen', 'es_manual', 'sede', 'cantidad', 'estado', 'prov_compra', 'prov_catalogo', 'num_pedido', 'nota_completa'])

    cant_p = len(df_listado[df_listado['estado'] == "🔴 Pendiente de compra"]['origen'].unique()) if not df_listado.empty else 0
    cant_c = len(df_listado[df_listado['estado'] == "🟡 Comprado"])
    cant_r = len(df_listado[df_listado['estado'] == "🟢 Recibido"])

    c_tab1, c_tab2, c_tab3 = st.columns(3)
    if c_tab1.button(f"🔴 Pendientes de Compra ({cant_p})", use_container_width=True, type="secondary" if st.session_state["pestana_compras_fija"] != "🔴 Pendientes" else "primary"):
        st.session_state["pestana_compras_fija"] = "🔴 Pendientes"; st.rerun()
    if c_tab2.button(f"🟡 Comprados / En Camino ({cant_c})", use_container_width=True, type="secondary" if st.session_state["pestana_compras_fija"] != "🟡 Comprados" else "primary"):
        st.session_state["pestana_compras_fija"] = "🟡 Comprados"; st.rerun()
    if c_tab3.button(f"🟢 Historial Recibidos ({cant_r})", use_container_width=True, type="secondary" if st.session_state["pestana_compras_fija"] != "🟢 Recibidos" else "primary"):
        st.session_state["pestana_compras_fija"] = "🟢 Recibidos"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state["pestana_compras_fija"] == "🔴 Pendientes":
        df_p = df_listado[df_listado['estado'] == "🔴 Pendiente de compra"]
        if df_p.empty: 
            st.success("No hay materiales pendientes de compra.")
        else:
            for origen_cli in df_p['origen'].unique():
                df_cli_items = df_p[df_p['origen'] == origen_cli]
                sede_cli = df_cli_items.iloc[0]['sede']
                
                with st.container(border=True):
                    st.markdown(f"#### 👤 Cliente / Obra: **{origen_cli}** | 📍 Sede: **{sede_cli}**")
                    st.write("---")
                    
                    for _, item in df_cli_items.iterrows():
                        col1, col2, col3 = st.columns([2.2, 1.2, 1.8])
                        col1.markdown(f"📦 **{item['equipo']}**")
                        col2.markdown(f"🔢 Cantidad: **{item['cantidad']}**")
                        
                        c_comprar, c_mod, c_del = col3.columns([1.2, 1, 0.8])
                        
                        with c_comprar.popover("🤝 Comprado"):
                            prov_raw = str(item['prov_catalogo']) if pd.notna(item['prov_catalogo']) else ""
                            provs_hab = [p.strip() for p in re.split(r'[/,]', prov_raw) if p.strip()]
                            opciones_prov = provs_hab if provs_hab else lista_proveedores_gral
                            
                            st.markdown(f"**Proveedor habilitado:**")
                            prov_sel = st.selectbox("Seleccionar:", opciones_prov, key=f"p_sel_{item['id_mov']}")
                            num_ped_sel = st.text_input("N° de Pedido / Orden (opcional):", key=f"p_ped_{item['id_mov']}", autocomplete="off")
                            
                            if st.button("✔ Ok", key=f"btn_comp_{item['id_mov']}", type="primary"):
                                ped_tag = f" | Pedido: {num_ped_sel.strip()}" if num_ped_sel.strip() else ""
                                nueva_nota = f"{item['nota_completa']}{ped_tag} | Prov: {prov_sel}"
                                cursor = conn.cursor()
                                cursor.execute("UPDATE movimientos SET nota = %s WHERE id = %s", (nueva_nota, item['id_mov']))
                                
                                registrar_accion(
                                    conn=conn,
                                    usuario=st.session_state['usuario_actual'],
                                    accion="MARCAR_COMPRADO",
                                    detalles=f"Marcó como comprado (Ped: {num_ped_sel.strip() if num_ped_sel.strip() else '-'}) {item['cantidad']} un. de {item['equipo']} para el cliente '{item['origen']}' al Proveedor: {prov_sel}",
                                    producto_id=item['prod_id'],
                                    cliente=item['origen']
                                )
                                conn.commit()
                                cursor.close()
                                st.rerun()
                                
                        with c_mod.popover("⚙ Editar"):
                            nueva_cant = st.number_input("Nueva Cantidad:", min_value=1, value=max(1, int(item['cantidad'])), key=f"ed_cant_{item['id_mov']}")
                            nueva_sede = st.selectbox("Nueva Sede:", lista_sedes, index=lista_sedes.index(item['sede']) if item['sede'] in lista_sedes else 0, key=f"ed_sede_{item['id_mov']}")
                            if st.button("Guardar Cambios", key=f"btn_save_{item['id_mov']}"):
                                nueva_nota_clean = f"Reserva: {item['origen']} | F: {int(nueva_cant)}"
                                cursor = conn.cursor()
                                cursor.execute("UPDATE movimientos SET nota = %s, asignacion = %s WHERE id = %s", (nueva_nota_clean, nueva_sede, item['id_mov']))
                                conn.commit()
                                cursor.close()
                                st.rerun()
                                
                        if c_del.button("🗑", key=f"btn_del_{item['id_mov']}"):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM movimientos WHERE id = %s", (item['id_mov'],))
                            conn.commit()
                            cursor.close()
                            st.rerun()

    if st.session_state["pestana_compras_fija"] == "🟡 Comprados":
        df_c_tab = df_listado[df_listado['estado'] == "🟡 Comprado"]
        if df_c_tab.empty: st.info("No hay órdenes marcadas como compradas en viaje.")
        else:
            st.warning("⚠️ Recordatorio: Al recibir material para las provincias, se alojará directamente en el Módulo de Despachos sin alterar stock local.")
            for _, item in df_c_tab.iterrows():
                tipo_origen = "🏢 Stock Directo (Lucas)" if item['es_manual'] else f"👤 Cliente: {item['origen']}"
                str_pedido = f" | 📦 Pedido: **{item['num_pedido']}**" if item['num_pedido'] != "-" else ""
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2.2, 1.5, 1.3])
                    col1.markdown(f"**📦 {item['equipo']}**")
                    col1.write(f"{tipo_origen} | 🏢 Prov: **{item['prov_compra']}**{str_pedido}")
                    col2.markdown(f"🔢 Cant: **{item['cantidad']}** | 📍 {item['sede']}")
                    c_rec, c_ed_dir, c_del_dir = col3.columns([1.2, 0.9, 0.7])
                    
                    # --- BOTÓN RECIBIR UNIFICADO: CONSUME STOCK EN TODAS LAS SEDES (INCLUIDAS PROVINCIAS) ---
                    if c_rec.button("📥 Recibir", key=f"btn_rec_{item['id_mov']}", type="primary"):
                        nota_limpia_f = item['nota_completa'].split(" | F: ")[0]
                        nota_limpia_f = nota_limpia_f.split(" | Prov: ")[0].split(" | COMPRADO: ")[0]
                        
                        suffix_despacho = " | Despacho: PENDIENTE" if ("Despacho: PENDIENTE" in item['nota_completa'] or item['sede'] in ["Formosa", "Bolivar"]) else ""
                        ped_tag_rec = f" | Pedido: {item['num_pedido']}" if item['num_pedido'] != "-" else ""
                        nota_final = f"{nota_limpia_f}{ped_tag_rec} | F: 0 | Prov: {item['prov_compra']} | RECIBIDO{suffix_despacho}"
                        
                        cant_movimiento = int(item['cantidad']) if int(item['cantidad']) > 0 else 1
                        cursor = conn.cursor()
                        
                        # 🎯 CONSUME SIEMPRE EL STOCK PARA COMPENSAR EL INGRESO PREVIO POR REMITO
                        cursor.execute("UPDATE movimientos SET cantidad = %s, nota = %s WHERE id = %s", (-cant_movimiento, nota_final, item['id_mov']))
                        detalles_rec = f"Confirmó recepción de compra para cliente ({item['origen']}). Asignó {cant_movimiento} un. de {item['equipo']} a la obra y equilibró el stock de {item['sede']}."
                        
                        registrar_accion(
                            conn=conn,
                            usuario=st.session_state['usuario_actual'],
                            accion="RECIBIR_COMPRA",
                            detalles=detalles_rec,
                            producto_id=item['prod_id'],
                            cliente=item['origen']
                        )
                        
                        conn.commit()
                        cursor.close()
                        st.success("¡Recepción confirmada y stock equilibrado con éxito!")
                        st.rerun()
                        
                    with c_ed_dir.popover("⚙"):
                        nueva_cant_dir = st.number_input("Cantidad:", min_value=1, value=max(1, int(item['cantidad'])), key=f"ed_cant_c_{item['id_mov']}")
                        nueva_sede_dir = st.selectbox("Sede:", lista_sedes, index=lista_sedes.index(item['sede']) if item['sede'] in lista_sedes else 0, key=f"ed_sede_c_{item['id_mov']}")
                        nuevo_ped_dir = st.text_input("N° Pedido:", value=item['num_pedido'] if item['num_pedido'] != "-" else "", key=f"ed_ped_c_{item['id_mov']}")
                        if st.button("Guardar", key=f"btn_save_c_{item['id_mov']}"):
                            marker = " | Despacho: PENDIENTE" if nueva_sede_dir in ["Formosa", "Bolivar"] else ""
                            ped_edit_str = f" | Pedido: {nuevo_ped_dir.strip()}" if nuevo_ped_dir.strip() else ""
                            if item['es_manual']: nueva_nota_dir = f"Compra Directa: {item['origen']}{ped_edit_str} | F: {int(nueva_cant_dir)} | Prov: {item['prov_compra']}{marker}"
                            else: nueva_nota_dir = f"Reserva: {item['origen']}{ped_edit_str} | F: {int(nueva_cant_dir)} | Prov: {item['prov_compra']}{marker}"
                            cursor = conn.cursor()
                            cursor.execute("UPDATE movimientos SET nota = %s, asignacion = %s WHERE id = %s", (nueva_nota_dir, nueva_sede_dir, item['id_mov']))
                            conn.commit()
                            cursor.close()
                            st.rerun()
                    if c_del_dir.button("🗑", key=f"btn_del_c_{item['id_mov']}"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM movimientos WHERE id = %s", (item['id_mov'],))
                        conn.commit()
                        cursor.close()
                        st.rerun()

    if st.session_state["pestana_compras_fija"] == "🟢 Recibidos":
        df_rec_hist = df_listado[df_listado['estado'] == "🟢 Recibido"]
        if df_rec_hist.empty: st.info("No se registran transacciones cerradas por esta pestaña todavía.")
        else:
            df_mostrar_rec = df_rec_hist[['origen', 'sede', 'equipo', 'prov_compra', 'num_pedido']].copy()
            df_mostrar_rec.columns = ['Origen / Cliente', 'Sede Destino', 'Equipo', 'Proveedor', 'N° Pedido']
            st.dataframe(df_mostrar_rec, hide_index=True, use_container_width=True)

    conn.close()