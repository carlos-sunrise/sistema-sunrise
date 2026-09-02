import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes, obtener_lista_proveedores, obtener_lista_tipos
from modulo_auth import crear_usuario, obtener_lista_usuarios, cambiar_estado_usuario
import time
import hashlib  # 🎯 Usamos hashlib nativo de Python para la contraseña en caso de edición

def hash_password(password: str) -> str:
    """Genera un hash seguro con la librería estándar de Python"""
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

def render():
    st.header("⚙️ Gestión del Sistema y Auditoría")
    conn = get_connection()

    if "v_sedes" not in st.session_state: st.session_state["v_sedes"] = 0
    if "v_provs" not in st.session_state: st.session_state["v_provs"] = 0
    if "v_tipos" not in st.session_state: st.session_state["v_tipos"] = 0

    tab_sedes, tab_provs, tab_tipos, tab_auditoria, tab_usuarios = st.tabs([
        "📍 Sedes", 
        "🏢 Proveedores", 
        "📦 Tipos de Equipo", 
        "🔍 Historial de Movimientos",
        "👥 Usuarios"
    ])

    # --- TAB: SEDES ---
    with tab_sedes:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Añadir Sede")
            nueva_sede = st.text_input("Nombre de la Sede:", key="add_sede", autocomplete="off")
            if st.button("Guardar Sede", type="primary"):
                if nueva_sede:
                    cursor = conn.cursor()
                    cursor.execute("SELECT nombre FROM sedes WHERE nombre = %s", (nueva_sede,))
                    existe = cursor.fetchone()
                    if existe:
                        st.error(f"⚠️ La sede '{nueva_sede}' ya existe.")
                    else:
                        cursor.execute("INSERT INTO sedes (nombre) VALUES (%s)", (nueva_sede,))
                        conn.commit()
                        st.session_state["v_sedes"] += 1
                        st.success(f"✅ Sede '{nueva_sede}' añadida.")
                        time.sleep(1.2)
                        cursor.close()
                        st.rerun()
                    cursor.close()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_s = obtener_lista_sedes()
            st.dataframe(pd.DataFrame(lista_s, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_s = st.selectbox("Eliminar sede:", ["Seleccione..."] + lista_s, key=f"del_s_{st.session_state['v_sedes']}")
            if st.button("Eliminar Sede"):
                if sel_s != "Seleccione...":
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM sedes WHERE nombre = %s", (sel_s,))
                    conn.commit()
                    cursor.close()
                    st.session_state["v_sedes"] += 1
                    st.warning(f"Sede '{sel_s}' eliminada.")
                    time.sleep(1.2)
                    st.rerun()

    # --- TAB: PROVEEDORES ---
    with tab_provs:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Añadir Proveedor")
            nuevo_p = st.text_input("Nombre del Proveedor:", key="add_p", autocomplete="off")
            if st.button("Guardar Proveedor", type="primary"):
                nuevo_p_val = st.session_state.get("add_p", "").strip()
                if nuevo_p_val:
                    cursor = conn.cursor()
                    cursor.execute("SELECT nombre FROM proveedores WHERE nombre = %s", (nuevo_p_val,))
                    existe_p = cursor.fetchone()
                    if existe_p:
                        st.error(f"⚠️ El proveedor '{nuevo_p_val}' ya existe.")
                    else:
                        cursor.execute("INSERT INTO proveedores (nombre) VALUES (%s)", (nuevo_p_val,))
                        conn.commit()
                        st.session_state["v_provs"] += 1
                        st.success(f"✅ Proveedor '{nuevo_p_val}' añadido.")
                        time.sleep(1.2)
                        cursor.close()
                        st.rerun()
                    cursor.close()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_p = obtener_lista_proveedores()
            st.dataframe(pd.DataFrame(lista_p, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_p = st.selectbox("Eliminar proveedor:", ["Seleccione..."] + lista_p, key=f"del_p_{st.session_state['v_provs']}")
            if st.button("Eliminar Proveedor"):
                if sel_p != "Seleccione...":
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM proveedores WHERE nombre = %s", (sel_p,))
                    conn.commit()
                    cursor.close()
                    st.session_state["v_provs"] += 1
                    st.warning(f"Proveedor '{sel_p}' eliminado.")
                    time.sleep(1.2)
                    st.rerun()

    # --- TAB: TIPOS ---
    with tab_tipos:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Añadir Tipo")
            nuevo_t = st.text_input("Nombre del Tipo:", key="add_t", autocomplete="off")
            if st.button("Guardar Tipo", type="primary"):
                if nuevo_t:
                    cursor = conn.cursor()
                    cursor.execute("SELECT nombre FROM tipos_equipo WHERE nombre = %s", (nuevo_t,))
                    existe_t = cursor.fetchone()
                    if existe_t:
                        st.error(f"⚠️ El tipo '{nuevo_t}' ya existe.")
                    else:
                        cursor.execute("INSERT INTO tipos_equipo (nombre) VALUES (%s)", (nuevo_t,))
                        conn.commit()
                        st.session_state["v_tipos"] += 1
                        st.success(f"✅ Tipo '{nuevo_t}' añadido.")
                        time.sleep(1.2)
                        cursor.close()
                        st.rerun()
                    cursor.close()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_t = obtener_lista_tipos()
            st.dataframe(pd.DataFrame(lista_t, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_t = st.selectbox("Eliminar tipo:", ["Seleccione..."] + lista_t, key=f"del_t_{st.session_state['v_tipos']}")
            if st.button("Eliminar Tipo"):
                if sel_t != "Seleccione...":
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM tipos_equipo WHERE nombre = %s", (sel_t,))
                    conn.commit()
                    cursor.close()
                    st.session_state["v_tipos"] += 1
                    st.warning(f"Tipo '{sel_t}' eliminado.")
                    time.sleep(1.2)
                    st.rerun()

    # --- TAB: AUDITORÍA DE USUARIOS ---
    with tab_auditoria:
        st.subheader("📋 Registro de Actividad de Usuarios")
        st.write("Seguimiento en tiempo real de reservas, compras e ingresos físicos de mercadería.")
        
        with st.container(border=True):
            cf1, cf2, cf3 = st.columns(3)
            
            try:
                df_usuarios_db = pd.read_sql("SELECT DISTINCT usuario FROM log_auditoria", conn)
                usuarios_disponibles = ["Todos"] + df_usuarios_db["usuario"].dropna().tolist()
            except:
                usuarios_disponibles = ["Todos"]
                
            filtro_usuario = cf1.selectbox("👤 Responsable:", usuarios_disponibles)
            filtro_accion = cf2.selectbox("⚡ Acción Realizada:", [
                "Todas", "CREAR_RESERVA", "DEVOLUCION", 
                "CANCELAR_RESERVA_TOTAL", "INSTALAR_OBRA", 
                "FALTANTE_SOLICITADO", "MARCAR_COMPRADO", 
                "RECIBIR_COMPRA", "INGRESO_REMITO"
            ])
            buscar_obra = cf3.text_input("🏢 Buscar Cliente / Remito:", placeholder="Escribí para buscar...", autocomplete="off")

        query_log = "SELECT fecha_hora, usuario, accion, detalles, cliente FROM log_auditoria WHERE 1=1"
        parametros = []
        
        if filtro_usuario != "Todos":
            query_log += " AND usuario = %s"
            parametros.append(filtro_usuario)
            
        if filtro_accion != "Todas":
            query_log += " AND accion = %s"
            parametros.append(filtro_accion)
            
        if buscar_obra:
            query_log += " AND (cliente LIKE %s OR detalles LIKE %s)"
            parametros.append(f"%{buscar_obra}%")
            parametros.append(f"%{buscar_obra}%")
            
        query_log += " ORDER BY id DESC"

        try:
            df_logs = pd.read_sql(query_log, conn, params=parametros)
            
            if df_logs.empty:
                st.info("No se registran movimientos que coincidan con los filtros aplicados.")
            else:
                df_logs.columns = ["Fecha / Hora", "Usuario", "Operación", "Detalle Detallado", "Referencia / Cliente"]
                
                st.dataframe(
                    df_logs,
                    column_config={
                        "Fecha / Hora": st.column_config.TextColumn("Fecha / Hora", width="medium"),
                        "Usuario": st.column_config.TextColumn("Usuario", width="small"),
                        "Operación": st.column_config.TextColumn("Operación", width="small"),
                        "Detalle Detallado": st.column_config.TextColumn("Detalle Detallado", width="large"),
                        "Referencia / Cliente": st.column_config.TextColumn("Referencia / Cliente", width="medium")
                    },
                    hide_index=True,
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"No se pudo cargar el historial de auditoría: {e}")

    # --- 👥 TAB: GESTIÓN DE USUARIOS (SIN BCRYPT) ---
    with tab_usuarios:
        st.subheader("👥 Gestión de Usuarios del Sistema")
        
        usuario_actual = st.session_state.get('usuario', {})
        es_admin = usuario_actual.get('rol') == 'admin' or 'usuario' not in st.session_state
        
        if not es_admin:
            st.warning("🔒 Solo los administradores pueden gestionar usuarios.")
        else:
            with st.expander("➕ Crear Nuevo Usuario", expanded=False):
                with st.form("form_nuevo_usuario"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_user = st.text_input("Usuario (Login)")
                        nuevo_nombre = st.text_input("Nombre Completo")
                    with col2:
                        nueva_pass = st.text_input("Contraseña", type="password")
                        nuevo_rol = st.selectbox("Rol", ["usuario", "admin"])
                    
                    btn_crear = st.form_submit_button("Guardar Usuario", use_container_width=True)
                    
                    if btn_crear:
                        if not nuevo_user or not nueva_pass or not nuevo_nombre:
                            st.warning("Por favor completa todos los campos.")
                        else:
                            exito, mensaje = crear_usuario(nuevo_user, nueva_pass, nuevo_nombre, nuevo_rol)
                            if exito:
                                st.success(mensaje)
                                time.sleep(1.2)
                                st.rerun()
                            else:
                                st.error(mensaje)

            st.write("#### Usuarios Registrados")
            lista = obtener_lista_usuarios()
            
            if lista:
                for u in lista:
                    col_info, col_act, col_edit, col_del = st.columns([2.5, 0.9, 0.8, 0.8])
                    
                    with col_info:
                        estado_icon = "🟢" if u['activo'] else "🔴"
                        st.write(f"{estado_icon} **{u['nombre']}** (`{u['username']}`) - Rol: *{u['rol']}*")
                    
                    with col_act:
                        if u['username'] != usuario_actual.get('username'):
                            btn_txt = "Desactivar" if u['activo'] else "Activar"
                            if st.button(btn_txt, key=f"btn_user_act_{u['id']}", use_container_width=True):
                                cambiar_estado_usuario(u['id'], not u['activo'])
                                st.rerun()
                        else:
                            st.caption("(En uso)")

                    with col_edit.popover("⚙️ Editar"):
                        st.markdown(f"##### ✏️ Editar `{u['username']}`")
                        ed_nombre = st.text_input("Nombre Completo:", value=u['nombre'], key=f"ed_nom_{u['id']}")
                        ed_rol = st.selectbox("Rol:", ["usuario", "admin"], index=0 if u['rol'] == 'usuario' else 1, key=f"ed_rol_{u['id']}")
                        ed_pass = st.text_input("Nueva Contraseña (opcional):", type="password", key=f"ed_pass_{u['id']}")
                        
                        if st.button("Guardar Cambios", key=f"btn_save_usr_{u['id']}", type="primary", use_container_width=True):
                            cursor = conn.cursor()
                            if ed_pass.strip():
                                hashed = hash_password(ed_pass.strip())
                                cursor.execute("UPDATE usuarios SET nombre = %s, rol = %s, password = %s WHERE id = %s", 
                                               (ed_nombre.strip(), ed_rol, hashed, u['id']))
                            else:
                                cursor.execute("UPDATE usuarios SET nombre = %s, rol = %s WHERE id = %s", 
                                               (ed_nombre.strip(), ed_rol, u['id']))
                            conn.commit()
                            cursor.close()
                            st.toast(f"¡Usuario {u['username']} actualizado correctamente!")
                            time.sleep(0.8)
                            st.rerun()

                    with col_del:
                        if u['username'] != usuario_actual.get('username'):
                            if st.button("🗑️", key=f"btn_del_usr_{u['id']}", type="secondary", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM usuarios WHERE id = %s", (u['id'],))
                                conn.commit()
                                cursor.close()
                                st.toast(f"Usuario {u['username']} eliminado.")
                                time.sleep(0.8)
                                st.rerun()
                        else:
                            st.caption("")

                    st.divider()

    conn.close()