import streamlit as st
import pandas as pd
from db_utils import get_connection, obtener_lista_sedes, obtener_lista_proveedores, obtener_lista_tipos
from modulo_auth import crear_usuario, obtener_lista_usuarios, cambiar_estado_usuario  # 🔐 Importación de gestión de usuarios
import time

def render():
    st.header("⚙️ Gestión del Sistema y Auditoría")
    conn = get_connection()

    if "v_sedes" not in st.session_state: st.session_state["v_sedes"] = 0
    if "v_provs" not in st.session_state: st.session_state["v_provs"] = 0
    if "v_tipos" not in st.session_state: st.session_state["v_tipos"] = 0

    # 🔧 MODIFICACIÓN: Añadimos la pestaña de Usuarios al bloque principal
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
                    existe = conn.execute("SELECT nombre FROM sedes WHERE nombre = ?", (nueva_sede,)).fetchone()
                    if existe:
                        st.error(f"⚠️ La sede '{nueva_sede}' ya existe.")
                    else:
                        conn.execute("INSERT INTO sedes (nombre) VALUES (?)", (nueva_sede,))
                        conn.commit()
                        st.session_state["v_sedes"] += 1
                        st.success(f"✅ Sede '{nueva_sede}' añadida.")
                        time.sleep(1.2)
                        st.rerun()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_s = obtener_lista_sedes()
            st.dataframe(pd.DataFrame(lista_s, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_s = st.selectbox("Eliminar sede:", ["Seleccione..."] + lista_s, key=f"del_s_{st.session_state['v_sedes']}")
            if st.button("Eliminar Sede"):
                if sel_s != "Seleccione...":
                    conn.execute("DELETE FROM sedes WHERE nombre = ?", (sel_s,))
                    conn.commit()
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
                    existe_p = conn.execute("SELECT nombre FROM proveedores WHERE nombre = ?", (nuevo_p_val,)).fetchone()
                    if existe_p:
                        st.error(f"⚠️ El proveedor '{nuevo_p_val}' ya existe.")
                    else:
                        conn.execute("INSERT INTO proveedores (nombre) VALUES (?)", (nuevo_p_val,))
                        conn.commit()
                        st.session_state["v_provs"] += 1
                        st.success(f"✅ Proveedor '{nuevo_p_val}' añadido.")
                        time.sleep(1.2)
                        st.rerun()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_p = obtener_lista_proveedores()
            st.dataframe(pd.DataFrame(lista_p, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_p = st.selectbox("Eliminar proveedor:", ["Seleccione..."] + lista_p, key=f"del_p_{st.session_state['v_provs']}")
            if st.button("Eliminar Proveedor"):
                if sel_p != "Seleccione...":
                    conn.execute("DELETE FROM proveedores WHERE nombre = ?", (sel_p,))
                    conn.commit()
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
                    existe_t = conn.execute("SELECT nombre FROM tipos_equipo WHERE nombre = ?", (nuevo_t,)).fetchone()
                    if existe_t:
                        st.error(f"⚠️ El tipo '{nuevo_t}' ya existe.")
                    else:
                        conn.execute("INSERT INTO tipos_equipo (nombre) VALUES (?)", (nuevo_t,))
                        conn.commit()
                        st.session_state["v_tipos"] += 1
                        st.success(f"✅ Tipo '{nuevo_t}' añadido.")
                        time.sleep(1.2)
                        st.rerun()

        with c2:
            st.subheader("Lista Actual / Eliminar")
            lista_t = obtener_lista_tipos()
            st.dataframe(pd.DataFrame(lista_t, columns=["nombre"]), hide_index=True, use_container_width=True)
            sel_t = st.selectbox("Eliminar tipo:", ["Seleccione..."] + lista_t, key=f"del_t_{st.session_state['v_tipos']}")
            if st.button("Eliminar Tipo"):
                if sel_t != "Seleccione...":
                    conn.execute("DELETE FROM tipos_equipo WHERE nombre = ?", (sel_t,))
                    conn.commit()
                    st.session_state["v_tipos"] += 1
                    st.warning(f"Tipo '{sel_t}' eliminado.")
                    time.sleep(1.2)
                    st.rerun()

    # --- TAB: AUDITORÍA DE USUARIOS ---
    with tab_auditoria:
        st.subheader("📋 Registro de Actividad de Usuarios")
        st.write("Seguimiento en tiempo real de reservas, compras e ingresos físicos de mercadería.")
        
        # Bloque de Filtros Interactivos
        with st.container(border=True):
            cf1, cf2, cf3 = st.columns(3)
            
            try:
                df_usuarios_db = pd.read_sql("SELECT DISTINCT usuario FROM log_auditoria", conn)
                usuarios_disponibles = ["Todos"] + df_usuarios_db["usuario"].tolist()
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
            query_log += " AND usuario = ?"
            parametros.append(filtro_usuario)
            
        if filtro_accion != "Todas":
            query_log += " AND accion = ?"
            parametros.append(filtro_accion)
            
        if buscar_obra:
            query_log += " AND cliente LIKE ?"
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

    # --- 👥 TAB NUEVA: GESTIÓN DE USUARIOS ---
    with tab_usuarios:
        st.subheader("👥 Gestión de Usuarios del Sistema")
        
        usuario_actual = st.session_state.get('usuario', {})
        
        if usuario_actual.get('rol') != 'admin':
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
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        estado_icon = "🟢" if u['activo'] else "🔴"
                        st.write(f"{estado_icon} **{u['nombre']}** (`{u['username']}`) - Rol: *{u['rol']}*")
                    with col_btn:
                        if u['username'] != usuario_actual.get('username'):
                            btn_txt = "Desactivar" if u['activo'] else "Activar"
                            if st.button(btn_txt, key=f"btn_user_{u['id']}"):
                                cambiar_estado_usuario(u['id'], not u['activo'])
                                st.rerun()
                    st.divider()

    conn.close()