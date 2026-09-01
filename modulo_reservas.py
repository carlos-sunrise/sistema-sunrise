import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes, registrar_accion  # 📜 Importamos la función de auditoría
from datetime import datetime, timedelta
import re
import io

def render():
    st.header("📑 Gestión de Reservas e Instalaciones")
    conn = get_connection()

    # --- 1. ESTADOS ---
    if 'mostrar_form_nueva' not in st.session_state: st.session_state.mostrar_form_nueva = False
    if 'mostrar_historico' not in st.session_state: st.session_state.mostrar_historico = False
    if 'mostrar_activas' not in st.session_state: st.session_state.mostrar_activas = True
    
    if 'usuario_actual' not in st.session_state: 
        st.session_state['usuario_actual'] = "Carlos (Administrador)"
    
    if 'etiquetas_impresas' not in st.session_state: st.session_state['etiquetas_impresas'] = set()

    sedes_db = obtener_lista_sedes()
    sedes = sedes_db 

    # --- 2. BOTONES SUPERIORES ---
    col_btn1, col_btn2, col_btn3 = st.columns([1.2, 1, 1])
    
    if col_btn1.button("➕ NUEVA RESERVA", use_container_width=True, type="primary"):
        st.session_state.mostrar_form_nueva = not st.session_state.mostrar_form_nueva
        st.session_state.mostrar_activas = False
        st.session_state.mostrar_historico = False
        
    if col_btn2.button("📋 RESERVAS ACTIVAS", use_container_width=True):
        st.session_state.mostrar_activas = not st.session_state.mostrar_activas
        st.session_state.mostrar_form_nueva = False
        st.session_state.mostrar_historico = False

    if col_btn3.button("📜 VER HISTÓRICO", use_container_width=True):
        st.session_state.mostrar_historico = not st.session_state.mostrar_historico
        st.session_state.mostrar_form_nueva = False
        st.session_state.mostrar_activas = False

    # --- 3. FORMULARIO DE RESERVA ---
    if st.session_state.mostrar_form_nueva:
        with st.container(border=True):
            st.subheader("📝 Selección de Equipos")
            c1, c2 = st.columns(2)
            f_cliente = c1.text_input("👤 Cliente / Obra:", placeholder="Escribí el nombre del cliente...", autocomplete="off")
            f_asignado = c2.selectbox("📍 Asignado a:", sedes_db)
            
            if f_cliente:
                selecciones_totales = []
                for sede_nom in sedes:
                    es_bsas = "Buenos Aires" in sede_nom or "Bs. As." in sede_nom
                    with st.expander(f"📍 Stock en {sede_nom.upper()}", expanded=es_bsas):
                        query_f = """
                            SELECT p.id, p.tipo, p.marca, p.modelo, p.proveedor,
                                   SUM(m.cantidad) as disponible
                            FROM productos p
                            JOIN movimientos m ON p.id = m.producto_id
                            WHERE m.asignacion = %s
                            GROUP BY p.id, p.tipo, p.marca, p.modelo, p.proveedor
                            HAVING disponible > 0
                            ORDER BY p.tipo ASC
                        """
                        df_s = pd.read_sql(query_f, conn, params=(sede_nom,))
                        
                        if not df_s.empty:
                            df_s["Sel"] = False
                            df_s["Cant"] = 0
                            df_ed = st.data_editor(
                                df_s,
                                column_config={
                                    "id": None,
                                    "disponible": st.column_config.NumberColumn("Disponible", disabled=True),
                                    "Sel": st.column_config.CheckboxColumn("¿Saca?"),
                                    "Cant": st.column_config.NumberColumn("Cantidad", min_value=0)
                                },
                                disabled=["tipo", "marca", "modelo", "proveedor", "disponible"],
                                hide_index=True, use_container_width=True, key=f"grid_res_{sede_nom}"
                            )
                            items_sede = df_ed[(df_ed["Sel"] == True) & (df_ed["Cant"] > 0)]
                            for _, row in items_sede.iterrows():
                                selecciones_totales.append({
                                    'id': row['id'], 'sede': sede_nom,
                                    'pedida': int(row['Cant']), 'stock': int(row['disponible']),
                                    'prov': row['proveedor'], 'tipo': row['tipo'], 'marca': row['marca'], 'modelo': row['modelo']
                                })

                st.markdown("---")
                st.markdown("### 🚨 Agregar Faltantes (Sin Stock)")
                with st.container(border=True):
                    df_all = pd.read_sql("SELECT DISTINCT id, tipo, marca, modelo FROM productos", conn)

                    cf1, cf2, cf3 = st.columns([1, 2, 1])
                    
                    lista_tipos = sorted(df_all['tipo'].unique().tolist()) if not df_all.empty else []
                    tipo_f = cf1.selectbox("Tipo:", ["Seleccione..."] + lista_tipos)
                    
                    models_filtrados = ["Seleccione..."]
                    if tipo_f != "Seleccione..." and not df_all.empty:
                        df_mod = df_all[df_all['tipo'] == tipo_f]
                        models_filtrados += (df_mod['marca'] + " " + df_mod['modelo']).tolist()
                    
                    prod_f = cf2.selectbox("Producto / Modelo:", models_filtrados)
                    cant_f = cf3.number_input("Cant:", min_value=1, step=1, key="cant_f_gen")
                    
                    if st.button("➕ Añadir este faltante al pedido", use_container_width=True):
                        if tipo_f != "Seleccione..." and prod_f != "Seleccione...":
                            m_parts = prod_f.split(" ")
                            marca_m = m_parts[0]
                            modelo_m = " ".join(m_parts[1:])
                            id_gen_row = pd.read_sql("SELECT id FROM productos WHERE tipo=%s AND marca=%s AND modelo=%s LIMIT 1",
                                                   conn, params=(tipo_f, marca_m, modelo_m))
                            
                            if not id_gen_row.empty:
                                id_gen = id_gen_row.iloc[0]['id']
                                
                                if "Buenos Aires" in f_asignado or "Bs. As." in f_asignado:
                                    nota_f = f"Reserva: {f_cliente} ({f_asignado}) | F: {int(cant_f)}"
                                else:
                                    nota_f = f"Reserva: {f_cliente} ({f_asignado}) | F: {int(cant_f)} | Despacho: PENDIENTE | Cantidad: {int(cant_f)}"
                                
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) VALUES (%s, 0, %s, %s, %s)",
                                             (int(id_gen), datetime.now().strftime("%Y-%m-%d"), f_asignado, nota_f))
                                
                                registrar_accion(
                                    conn=conn,
                                    usuario=st.session_state['usuario_actual'],
                                    accion="FALTANTE_SOLICITADO",
                                    detalles=f"Cargó faltante de {int(cant_f)} un. de {tipo_f} {marca_m} {modelo_m} asignado a {f_asignado}",
                                    producto_id=int(id_gen),
                                    cliente=f_cliente
                                )
                                conn.commit()
                                cursor.close()
                                st.rerun()

                df_faltantes_temp = pd.read_sql("""
                    SELECT p.tipo, p.marca, p.modelo, m.nota FROM movimientos m
                    JOIN productos p ON m.producto_id = p.id
                    WHERE m.nota LIKE %s AND m.cantidad = 0
                """, conn, params=(f"Reserva: {f_cliente} ({f_asignado}) | F:%",))

                if selecciones_totales or not df_faltantes_temp.empty:
                    st.markdown("---")
                    st.markdown("### 🧐 Vista Previa")
                    with st.container(border=True):
                        for s in selecciones_totales: st.write(f"• {s['pedida']} un. - {s['tipo']} {s['marca']} {s['modelo']} (Stock)")
                        for _, f in df_faltantes_temp.iterrows():
                            cant_f_val = f['nota'].split("| F: ")[1].split(" | ")[0]
                            st.write(f"• {cant_f_val} un. - {f['tipo']} {f['marca']} {f['modelo']} 🚩")

                if st.button("💾 CONFIRMAR TODA LA RESERVA", type="primary", use_container_width=True):
                    if selecciones_totales:
                        cursor = conn.cursor()
                        for item in selecciones_totales:
                            reserva = min(item['pedida'], item['stock'])
                            falta = max(0, item['pedida'] - item['stock'])
                            
                            # 🎯 SI SE SACA DE BS. AS. PARA OTRA SEDE (FORMOSA/BOLIVAR), GENERA MARCA DE DESPACHO DIRECTO LISTO EN GALPÓN
                            es_provincia = f_asignado in ["Formosa", "Bolivar"]
                            es_origen_bsas = "Buenos Aires" in item['sede'] or "Bs. As." in item['sede']
                            
                            tag_despacho = ""
                            if es_provincia and es_origen_bsas and reserva > 0:
                                tag_despacho = f" | Despacho: PENDIENTE | Cantidad: {int(reserva)} | RECIBIDO"
                            elif es_provincia and falta > 0:
                                tag_despacho = f" | Despacho: PENDIENTE | Cantidad: {int(falta)}"

                            nota_res = f"Reserva: {f_cliente} ({f_asignado}) | F: {int(falta)}{tag_despacho}"
                                    
                            cursor.execute("INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) VALUES (%s, %s, %s, %s, %s)",
                                         (item['id'], -int(reserva), datetime.now().strftime("%Y-%m-%d"), item['sede'], nota_res))
                            
                            registrar_accion(
                                conn=conn,
                                usuario=st.session_state['usuario_actual'],
                                accion="CREAR_RESERVA",
                                detalles=f"Reservó {int(reserva)} un. de stock real de {item['tipo']} {item['marca']} {item['modelo']} (Sede: {item['sede']}) para {f_cliente}",
                                producto_id=item['id'],
                                cliente=f_cliente
                            )
                        conn.commit()
                        cursor.close()
                        
                    st.session_state["mensaje_exito"] = f"🎉 ¡Reserva para '{f_cliente}' creada con éxito!"
                    st.session_state.mostrar_form_nueva = False
                    st.session_state.mostrar_activas = True
                    st.rerun()

    # --- 4. RESERVAS ACTIVAS ---
    if st.session_state.mostrar_activas:
        st.subheader("📋 Reservas Activas")
        
        if "mensaje_exito" in st.session_state and st.session_state["mensaje_exito"]:
            st.success(st.session_state["mensaje_exito"])
            st.toast(st.session_state["mensaje_exito"], icon="✅")
            st.session_state["mensaje_exito"] = None
        
        col_f1, col_f2 = st.columns([2, 1.5])
        buscar_nombre = col_f1.text_input("🔍 Buscar por Nombre de Cliente:", placeholder="Escribí para filtrar...", autocomplete="off")
        filtro_sede = col_f2.selectbox("📍 Filtrar por Sede asignada:", ["Todas"] + sedes_db)

        df_m = pd.read_sql("""
            SELECT m.id, m.producto_id, p.proveedor, p.tipo, p.marca, p.modelo,
                   m.cantidad as cant_real, ABS(m.cantidad) as res, m.nota, m.asignacion as sede, m.fecha
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.nota LIKE 'Reserva: %%'
        """, conn)

        if not df_m.empty:
            df_m['cliente_completo'] = df_m['nota'].apply(lambda x: x.split(" | F:")[0].replace("Reserva: ", ""))
            df_m['falta'] = df_m['nota'].apply(lambda x: int(x.split("| F: ")[1].split(" | ")[0]) if "| F: " in x else 0)

            if buscar_nombre:
                df_m = df_m[df_m['cliente_completo'].str.contains(buscar_nombre, case=False, na=False)]

            if filtro_sede != "Todas":
                df_m = df_m[df_m['cliente_completo'].str.contains(f"\\({filtro_sede}\\)", case=False, na=False)]

            if df_m.empty:
                st.info("No se encontraron reservas con los filtros aplicados.")

            for cli in df_m['cliente_completo'].unique():
                df_cli = df_m[df_m['cliente_completo'] == cli]
                total_f = df_cli['falta'].sum()
                sede_cli_default = re.search(r'\((.*?)\)', cli).group(1) if '(' in cli else sedes_db[0]
                
                with st.container(border=True):
                    head_col1, head_col2 = st.columns([3, 1])
                    head_col1.markdown(f"#### 👤 Cliente: {cli}")
                    
                    with head_col2.popover("➕ Agregar Equipo", use_container_width=True):
                        st.markdown("##### ➕ Añadir a esta Reserva")
                        
                        tab_stk, tab_compras = st.tabs(["📦 De Stock", "🚨 Solicitar Compra"])
                        
                        with tab_stk:
                            sede_sel_stk = st.selectbox("Sede Origen:", sedes_db, index=sedes_db.index(sede_cli_default) if sede_cli_default in sedes_db else 0, key=f"s_stk_{cli}")
                            
                            q_stk_dispo = """
                                SELECT p.id, p.tipo, p.marca, p.modelo, SUM(m.cantidad) as disponible
                                FROM productos p
                                JOIN movimientos m ON p.id = m.producto_id
                                WHERE m.asignacion = %s
                                GROUP BY p.id, p.tipo, p.marca, p.modelo
                                HAVING disponible > 0
                                ORDER BY p.tipo, p.marca, p.modelo
                            """
                            df_stk_avail = pd.read_sql(q_stk_dispo, conn, params=(sede_sel_stk,))
                            
                            if df_stk_avail.empty:
                                st.warning(f"⚠️ No hay stock disponible en {sede_sel_stk}.")
                            else:
                                prods_stk_opts = {f"{r['tipo']} - {r['marca']} {r['modelo']} (Disp: {int(r['disponible'])})": (r['id'], int(r['disponible'])) for _, r in df_stk_avail.iterrows()}
                                p_stk_label = st.selectbox("Seleccionar Producto:", list(prods_stk_opts.keys()), key=f"p_stk_{cli}")
                                p_stk_id, max_disp = prods_stk_opts[p_stk_label]
                                
                                c_stk_cant = st.number_input("Cantidad a reservar:", min_value=1, max_value=max_disp, value=1, key=f"c_stk_{cli}")
                                
                                if st.button("Confirmar Reserva de Stock", key=f"btn_stk_conf_{cli}", type="primary", use_container_width=True):
                                    cursor = conn.cursor()
                                    
                                    # 🎯 MARCA AUTOMÁTICA DE DESPACHO SI SE SACA DE BS AS A PROVINCIA
                                    tag_desp_stk = ""
                                    if sede_cli_default in ["Formosa", "Bolivar"] and ("Buenos Aires" in sede_sel_stk or "Bs. As." in sede_sel_stk):
                                        tag_desp_stk = f" | Despacho: PENDIENTE | Cantidad: {int(c_stk_cant)} | RECIBIDO"

                                    nota_stk_nueva = f"Reserva: {cli} | F: 0{tag_desp_stk}"
                                    cursor.execute(
                                        "INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) VALUES (%s, %s, %s, %s, %s)",
                                        (p_stk_id, -int(c_stk_cant), datetime.now().strftime("%Y-%m-%d"), sede_sel_stk, nota_stk_nueva)
                                    )
                                    registrar_accion(
                                        conn=conn,
                                        usuario=st.session_state['usuario_actual'],
                                        accion="CREAR_RESERVA",
                                        detalles=f"Agregó {int(c_stk_cant)} un. de stock a la reserva activa del cliente: {cli} (Sede: {sede_sel_stk})",
                                        producto_id=p_stk_id,
                                        cliente=cli
                                    )
                                    conn.commit()
                                    cursor.close()
                                    st.success("¡Stock reservado!")
                                    st.rerun()

                        with tab_compras:
                            df_prods_all = pd.read_sql("SELECT id, tipo, marca, modelo FROM productos ORDER BY tipo, marca, modelo", conn)
                            tipos_all = sorted(df_prods_all['tipo'].unique().tolist()) if not df_prods_all.empty else []
                            
                            t_cmp_sel = st.selectbox("Tipo:", ["Seleccione..."] + tipos_all, key=f"t_cmp_{cli}")
                            prods_cmp_list = ["Seleccione..."]
                            if t_cmp_sel != "Seleccione...":
                                df_cmp_filt = df_prods_all[df_prods_all['tipo'] == t_cmp_sel]
                                prods_cmp_list += (df_cmp_filt['marca'] + " " + df_cmp_filt['modelo']).tolist()
                                
                            p_cmp_sel = st.selectbox("Producto:", prods_cmp_list, key=f"p_cmp_{cli}")
                            c_cmp_cant = st.number_input("Cantidad a solicitar:", min_value=1, value=1, step=1, key=f"c_cmp_{cli}")
                            
                            if st.button("Confirmar Solicitud de Compra", key=f"btn_cmp_conf_{cli}", type="primary", use_container_width=True):
                                if t_cmp_sel != "Seleccione..." and p_cmp_sel != "Seleccione...":
                                    m_cmp_parts = p_cmp_sel.split(" ")
                                    marca_cmp = m_cmp_parts[0]
                                    modelo_cmp = " ".join(m_cmp_parts[1:])
                                    
                                    row_cmp = df_prods_all[(df_prods_all['tipo'] == t_cmp_sel) & (df_prods_all['marca'] == marca_cmp) & (df_prods_all['modelo'] == modelo_cmp)]
                                    
                                    if not row_cmp.empty:
                                        prod_cmp_id = int(row_cmp.iloc[0]['id'])
                                        cursor = conn.cursor()
                                        
                                        row_existente = df_cli[(df_cli['producto_id'] == prod_cmp_id) & (df_cli['cant_real'] == 0)]
                                        
                                        if not row_existente.empty:
                                            id_mov_exist = int(row_existente.iloc[0]['id'])
                                            falta_actual = int(row_existente.iloc[0]['falta'])
                                            nueva_falta = falta_actual + int(c_cmp_cant)
                                            
                                            nota_orig_ex = str(row_existente.iloc[0]['nota'])
                                            nota_actualizada = re.sub(r'\| F: \d+', f'| F: {nueva_falta}', nota_orig_ex)
                                            
                                            cursor.execute("UPDATE movimientos SET nota = %s WHERE id = %s", (nota_actualizada, id_mov_exist))
                                            detalles_log = f"Sumó {int(c_cmp_cant)} un. al faltante existente de {t_cmp_sel} {marca_cmp} {modelo_cmp} para {cli}. Total pendiente: {nueva_falta} un."
                                        else:
                                            marker_desp_cmp = " | Despacho: PENDIENTE" if sede_cli_default in ["Formosa", "Bolivar"] else ""
                                            nota_cmp_nueva = f"Reserva: {cli} | F: {int(c_cmp_cant)}{marker_desp_cmp}"
                                            cursor.execute(
                                                "INSERT INTO movimientos (producto_id, cantidad, fecha, asignacion, nota) VALUES (%s, 0, %s, %s, %s)",
                                                (prod_cmp_id, datetime.now().strftime("%Y-%m-%d"), sede_cli_default, nota_cmp_nueva)
                                            )
                                            detalles_log = f"Solicitó nuevo faltante de compras ({int(c_cmp_cant)} un.) de {t_cmp_sel} {marca_cmp} {modelo_cmp} para {cli}."
                                        
                                        registrar_accion(
                                            conn=conn,
                                            usuario=st.session_state['usuario_actual'],
                                            accion="FALTANTE_SOLICITADO",
                                            detalles=detalles_log,
                                            producto_id=prod_cmp_id,
                                            cliente=cli
                                        )
                                        conn.commit()
                                        cursor.close()
                                        st.success("¡Solicitud enviada a Compras!")
                                        st.rerun()

                    if total_f > 0: st.warning("Pendiente de Compras")
                    for s_ref in df_cli['sede'].unique():
                        df_cs = df_cli[df_cli['sede'] == s_ref]
                        for _, r in df_cs.iterrows():
                            col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 0.9, 0.7, 0.7, 1.4, 1.1, 1.1])
                            col1.write(f"{r['tipo']} {r['marca']} {r['modelo']}")
                            col2.write(r['proveedor'] if r['res'] > 0 or r['falta'] == 0 else "*-*")
                            
                            stock_mostrar = r['res'] if r['cant_real'] < 0 else 0
                            col3.write(f"Stock: {stock_mostrar}")
                            
                            if r['falta'] > 0:
                                col4.markdown(f":red[**Falta: {r['falta']}**]")
                                col5.markdown("🛒 *Compras*")
                            else:
                                col4.write("-")
                                col5.write("✅")
                            
                            ya_impreso = r['id'] in st.session_state['etiquetas_impresas']
                            label_boton = "🖨️ Etiqueta ✅" if ya_impreso else "🖨️ Etiqueta"
                            tipo_boton = "secondary" if ya_impreso else "primary"
                            
                            with col6.popover(label_boton, type=tipo_boton, use_container_width=True):
                                st.markdown("### 📋 Formato de Impresión Térmica (100x50mm)")
                                identificador_unico = f"ticket_{r['id']}"
                                html_etiqueta = f"""
                                <style>
                                    @media print {{
                                        body * {{ visibility: hidden; }}
                                        #{identificador_unico}, #{identificador_unico} * {{ visibility: visible; }}
                                        #{identificador_unico} {{ position: absolute; left: 0; top: 0; width: 100mm !important; height: 50mm !important; margin: 0 !important; padding: 10px !important; border: none !important; }}
                                        .no-print-btn {{ display: none !important; }}
                                    }}
                                </style>
                                <div id="{identificador_unico}" style="border: 2px solid #000; padding: 12px; font-family: 'Courier New', Courier, monospace; background-color: #fff; color: #000; width: 320px; border-radius: 2px;">
                                    <div style="text-align: center; font-weight: bold; font-size: 13px; border-bottom: 2px solid #000; padding-bottom: 4px; letter-spacing: 1px;">⚙️ SUNRISE SOLAR SYSTEM</div>
                                    <p style="margin: 6px 0 2px 0; font-size: 10px; font-weight: bold; color: #444;">👤 CLIENTE / OBRA:</p>
                                    <div style="font-size: 15px; font-weight: bold; background-color: #e8e8e8; padding: 4px; border: 1px solid #000; text-transform: uppercase;">{cli}</div>
                                    <p style="margin: 6px 0 2px 0; font-size: 10px; font-weight: bold; color: #444;">📦 MATERIAL RESERVADO:</p>
                                    <div style="font-size: 12px; font-weight: bold; line-height: 1.2;">{r['tipo'].upper()} - {r['marca']}</div>
                                    <div style="font-size: 11px; font-weight: normal; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">MOD: {r['modelo']}</div>
                                    <table style="width: 100%; margin-top: 6px; font-size: 11px; border-top: 1px dashed #000; padding-top: 4px; font-weight: bold;">
                                        <tr>
                                            <td>🔢 CANT: {r['res']} un</td>
                                            <td style="text-align: right;">📍 SEDE: {r['sede'].upper()}</td>
                                        </tr>
                                    </table>
                                    <div style="text-align: center; font-size: 8px; color: #555; margin-top: 4px; font-family: sans-serif;">||||| | |||| ||| | ||||| | ||||<br>Ref: {r['id']}-{datetime.now().strftime('%d%m%y')}</div>
                                </div>
                                """
                                st.components.v1.html(html_etiqueta + f'<br><button class="no-print" onclick="window.print()" style="width:100%; padding: 8px; background-color: #1a73e8; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">⚡ IMPRIMIR ETIQUETA DIRECTA</button>', height=260)
                                
                                if st.button("🟠 Marcar como Impreso", key=f"print_mark_{r['id']}", use_container_width=True):
                                    st.session_state['etiquetas_impresas'].add(r['id'])
                                    st.rerun()
                            
                            if r['cant_real'] < 0:
                                with col7.popover("🔄 Devolver"):
                                    tipo_dev = st.radio("Devolver:", ["Toda", "Parte"], key=f"t_dev_{r['id']}", horizontal=True)
                                    cant_dev = r['res']
                                    if tipo_dev == "Parte":
                                        cant_dev = st.number_input("Cantidad:", min_value=1, max_value=int(r['res']), value=1, step=1, key=f"c_dev_{r['id']}")
                                    
                                    if st.button("Confirmar Devolución", key=f"btn_dev_{r['id']}", use_container_width=True):
                                        cursor = conn.cursor()
                                        if tipo_dev == "Toda" or cant_dev == r['res']:
                                            cursor.execute("DELETE FROM movimientos WHERE id = %s", (r['id'],))
                                            st.session_state['etiquetas_impresas'].discard(r['id'])
                                            detalles_devolucion = f"Devolvió la totalidad de {r['tipo']} {r['marca']} {r['modelo']} (Cant: {r['res']}) al stock."
                                        else:
                                            nueva_cant = -(r['res'] - cant_dev)
                                            cursor.execute("UPDATE movimientos SET cantidad = %s WHERE id = %s", (nueva_cant, r['id']))
                                            detalles_devolucion = f"Devolvió parte de la reserva ({cant_dev} un.) de {r['tipo']} {r['marca']} {r['modelo']}. Quedan {r['res'] - cant_dev} un. reservados."
                                        
                                        registrar_accion(
                                            conn=conn,
                                            usuario=st.session_state['usuario_actual'],
                                            accion="DEVOLUCION",
                                            detalles=detalles_devolucion,
                                            producto_id=r['producto_id'],
                                            cliente=cli
                                        )
                                        conn.commit()
                                        cursor.close()
                                        st.success("Devuelto al stock.")
                                        st.rerun()
                            else:
                                col7.write("-")
                                
                    b1, b2 = st.columns(2)
                    if b1.button("🗑️ Cancelar Todo", key=f"del_cli_{cli}", use_container_width=True):
                        cursor = conn.cursor()
                        for item_id in df_cli['id'].tolist():
                            st.session_state['etiquetas_impresas'].discard(item_id)
                        cursor.execute("DELETE FROM movimientos WHERE nota LIKE %s", (f"Reserva: {cli}%%",))
                        
                        registrar_accion(
                            conn=conn,
                            usuario=st.session_state['usuario_actual'],
                            accion="CANCELAR_RESERVA_TOTAL",
                            detalles=f"Canceló la totalidad de la reserva y liberó los materiales del cliente: {cli}",
                            cliente=cli
                        )
                        conn.commit()
                        cursor.close()
                        st.rerun()
                        
                    if b2.button("✅ Instalar", key=f"inst_cli_{cli}", type="primary", use_container_width=True):
                        if total_f > 0: 
                            st.error("Faltan equipos.")
                        else: 
                            cursor = conn.cursor()
                            cursor.execute("UPDATE movimientos SET nota=%s WHERE nota LIKE %s", (f"Instalado: {cli} - {datetime.now().strftime('%Y-%m-%d')}", f"Reserva: {cli}%%"))
                            
                            registrar_accion(
                                conn=conn,
                                usuario=st.session_state['usuario_actual'],
                                accion="INSTALAR_OBRA",
                                detalles=f"Cerró la reserva y pasó a estado 'Instalado' la obra completa del cliente: {cli}",
                                cliente=cli
                            )
                            conn.commit()
                            cursor.close()
                            st.rerun()

    # --- 5. HISTORIAL ---
    if st.session_state.mostrar_historico:
        st.subheader("📜 Historial de Obras")
        
        with st.container(border=True):
            st.markdown("🔍 **Filtros de Búsqueda y Reportes**")
            cf_1, cf_2, cf_3 = st.columns([1.5, 1.2, 1.5])
            
            h_buscar_cliente = cf_1.text_input("👤 Cliente:", placeholder="Escribí para buscar...", autocomplete="off")
            h_filtro_sede = cf_2.selectbox("📍 Sucursal / Sede:", ["Todas"] + sedes_db, key="hist_sede_sel")
            periodo = cf_3.selectbox("📅 Período de Tiempo:", ["Todo el Historial", "Último Mes", "Rango Personalizado"])
            
            fecha_inicio = None
            fecha_fin = None
            
            if periodo == "Último Mes":
                fecha_fin = datetime.now().date()
                fecha_inicio = fecha_fin - timedelta(days=30)
            elif periodo == "Rango Personalizado":
                c_fec1, c_fec2 = cf_3.columns(2)
                fecha_inicio = c_fec1.date_input("Desde:", datetime.now().date() - timedelta(days=30))
                fecha_fin = c_fec2.date_input("Hasta:", datetime.now().date())

        query_h = """
            SELECT p.proveedor, p.tipo, p.marca, p.modelo, ABS(m.cantidad) as cant_mov, m.nota, m.fecha
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.nota LIKE 'Instalado%%'
            ORDER BY m.fecha DESC
        """
        df_hist = pd.read_sql(query_h, conn)
        
        if not df_hist.empty:
            df_hist['cli_full'] = df_hist['nota'].apply(lambda x: x.split(" - ")[0].replace("Instalado: ", "").strip())
            df_hist['nombre_cliente'] = df_hist['cli_full'].apply(lambda x: re.sub(r'\(.*?\)', '', x).strip())
            df_hist['sucursal'] = df_hist['cli_full'].apply(lambda x: re.search(r'\((.*?)\)', x).group(1) if '(' in x else "Sin Sede")
            
            if h_buscar_cliente:
                df_hist = df_hist[df_hist['nombre_cliente'].str.contains(h_buscar_cliente, case=False, na=False)]
            if h_filtro_sede != "Todas":
                df_hist = df_hist[df_hist['sucursal'].str.contains(h_filtro_sede, case=False, na=False)]
                
            if fecha_inicio and fecha_fin:
                df_hist['fecha_dt'] = pd.to_datetime(df_hist['fecha']).dt.date
                df_hist = df_hist[(df_hist['fecha_dt'] >= fecha_inicio) & (df_hist['fecha_dt'] <= fecha_fin)]

            if not df_hist.empty:
                df_excel = df_hist[['fecha', 'nombre_cliente', 'sucursal', 'tipo', 'marca', 'modelo', 'proveedor', 'cant_mov']].copy()
                df_excel.columns = ['Fecha', 'Cliente / Obra', 'Sede Asignada', 'Tipo Equipo', 'Marca', 'Modelo', 'Proveedor', 'Cantidad']
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_excel.to_excel(writer, index=False, sheet_name='Historial_Obras')
                buffer.seek(0)
                
                st.download_button(
                    label="📥 EXPORTAR ESTA VISTA A EXCEL",
                    data=buffer,
                    file_name=f"Reporte_Obras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.markdown("---")
            else:
                st.info("No hay datos que coincidan con los filtros y fechas seleccionadas.")

            for cli_f in df_hist['cli_full'].unique():
                df_sub = df_hist[df_hist['cli_full'] == cli_f]
                df_final = df_sub.groupby(['proveedor', 'tipo', 'marca', 'modelo', 'fecha', 'nombre_cliente', 'sucursal']).agg({'cant_mov': 'sum'}).reset_index()
                
                with st.expander(f"✅ {df_final.iloc[0]['nombre_cliente']} | 📍 {df_final.iloc[0]['sucursal']} | 📅 {df_final.iloc[0]['fecha']}"):
                    st.table(df_final[['proveedor', 'tipo', 'marca', 'modelo', 'cant_mov']].rename(columns={'cant_mov': 'cant'}))
                    
    conn.close()