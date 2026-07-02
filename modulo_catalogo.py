import streamlit as st
import pandas as pd
from db_utils import get_connection
import time
import re

def render():
    st.header("📂 Catálogo de Productos")
    conn = get_connection()

    # Tabs: Solo Ver e Importar
    tab_ver, tab_importar = st.tabs(["🔍 Ver Catálogo", "📥 Importar / Actualizar Excel"])

    # --- TAB: VER CATÁLOGO ---
    with tab_ver:
        df_prod = pd.read_sql("SELECT id, tipo, marca, modelo, u, proveedor FROM productos", conn)
        if df_prod.empty:
            st.info("Catálogo vacío. Por favor, importa un archivo Excel para comenzar.")
        else:
            st.markdown("### 🔍 Buscador Flexible de Equipos")
            c_b1, c_b2 = st.columns([2, 1.5])
            
            # 🛡️ Aplicamos autocomplete="off" para eliminar el texto predictivo
            buscar_general = c_b1.text_input("📦 Buscar por Tipo, Marca o Modelo:", placeholder="Ej: Inversor, Growatt, 285w...", autocomplete="off")
            buscar_prov = c_b2.text_input("🏭 Buscar por Proveedor (Coincidencia parcial):", placeholder="Ej: Renoba, Multi...", autocomplete="off")

            df_filtrado = df_prod.copy()
            
            if buscar_general:
                condicion = (
                    df_filtrado['tipo'].str.contains(buscar_general, case=False, na=False) |
                    df_filtrado['marca'].str.contains(buscar_general, case=False, na=False) |
                    df_filtrado['modelo'].str.contains(buscar_general, case=False, na=False)
                )
                df_filtrado = df_filtrado[condicion]

            if buscar_prov:
                df_filtrado = df_filtrado[df_filtrado['proveedor'].str.contains(buscar_prov, case=False, na=False)]

            if df_filtrado.empty:
                st.warning("No se encontraron productos que coincidan con los términos ingresados.")
            else:
                df_mostrar = df_filtrado[['tipo', 'marca', 'modelo', 'u', 'proveedor']].copy()
                df_mostrar.columns = ["Tipo", "Marca", "Modelo", "Unidad", "Proveedores Habilitados"]
                
                st.markdown(f"**📋 Mostrando {len(df_mostrar)} productos encontrados:**")
                st.dataframe(df_mostrar, hide_index=True, use_container_width=True)

    # --- TAB: IMPORTAR / ACTUALIZAR EXCEL ---
    with tab_importar:
        st.markdown("""
        ### 📥 Subir Catálogo unificado desde Excel
        Subí tu archivo de Excel para poblar o actualizar el catálogo de forma inteligente. 
        
        ⚠️ **Regla de Unificación Avanzada:** El sistema auto-limpiará cualquier residuo o duplicación previa en la base de datos, garantizando que los proveedores se agrupen de forma única y estética separados por una sola barra (`/`).
        """)

        archivo_subido = st.file_uploader("Selecciona el archivo Excel (.xlsx)", type=["xlsx"])
        
        if archivo_subido is not None:
            try:
                df_excel = pd.read_excel(archivo_subido, usecols="A:E")
                
                # Normalizamos nombres de columnas 
                df_excel.columns = [str(c).strip().lower() for c in df_excel.columns]
                
                columnas_requeridas = ['tipo', 'marca', 'modelo', 'u', 'proveedor']
                columnas_validas = all(col in df_excel.columns for col in columnas_requeridas)
                
                if not columnas_validas:
                    st.error(f"❌ El archivo no cuenta con las primeras 5 columnas requeridas: {columnas_requeridas}")
                else:
                    df_clean = df_excel[columnas_requeridas].dropna(subset=['tipo', 'modelo']).copy()
                    
                    st.success("¡Estructura de Excel válida detectada!")
                    st.dataframe(df_clean.head(5), hide_index=True)
                    
                    if st.button("🚀 Procesar e Importar Inventario", type="primary", use_container_width=True):
                        registros_nuevos = 0
                        registros_actualizados = 0
                        
                        df_db_actual = pd.read_sql("SELECT id, modelo, proveedor FROM productos", conn)
                        
                        def normalizar_modelo(t):
                            return re.sub(r'\s+', '', str(t)).lower().strip()

                        def limpiar_y_unificar_proveedores(*cadenas):
                            lista_elementos = []
                            for cadena in cadenas:
                                if pd.notna(cadena) and str(cadena).strip():
                                    partes = re.split(r'[/,]', str(cadena))
                                    for p in partes:
                                        p_limpio = p.strip()
                                        if p_limpio and p_limpio.lower() not in [item.lower() for item in lista_elementos]:
                                            lista_elementos.append(p_limpio)
                            return " / ".join(lista_elementos)

                        for _, row in df_clean.iterrows():
                            tipo_val = str(row['tipo']).strip()
                            marca_val = str(row['marca']).strip()
                            modelo_val = str(row['modelo']).strip()
                            u_val = str(row['u']).strip() if pd.notna(row['u']) else "un"
                            prov_excel = str(row['proveedor']).strip() if pd.notna(row['proveedor']) else ""
                            
                            modelo_norm = normalizar_modelo(modelo_val)
                            
                            match_id = None
                            prov_actual_db = ""
                            
                            if not df_db_actual.empty:
                                for _, db_row in df_db_actual.iterrows():
                                    if normalizar_modelo(db_row['modelo']) == modelo_norm:
                                        match_id = db_row['id']
                                        prov_actual_db = db_row['proveedor'] if db_row['proveedor'] else ""
                                        break
                            
                            if match_id is None:
                                prov_final_nuevo = limpiar_y_unificar_proveedores(prov_excel)
                                conn.execute("""
                                    INSERT INTO productos (tipo, marca, modelo, u, proveedor) 
                                    VALUES (?, ?, ?, ?, ?)
                                """, (tipo_val, marca_val, modelo_val, u_val, prov_final_nuevo))
                                registros_nuevos += 1
                            else:
                                prov_final = limpiar_y_unificar_proveedores(prov_actual_db, prov_excel)
                                conn.execute("""
                                    UPDATE productos SET tipo=?, marca=?, u=?, proveedor=? WHERE id=?
                                """, (tipo_val, marca_val, u_val, prov_final, int(match_id)))
                                registros_actualizados += 1
                        
                        conn.commit()
                        st.success(f"✅ ¡Catálogo Saneado! Proceso completado: {registros_nuevos} nuevos, {registros_actualizados} actualizados y unificados sin repeticiones.")
                        time.sleep(1.5)
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ Error crítico al procesar el archivo Excel: {e}")

    conn.close()