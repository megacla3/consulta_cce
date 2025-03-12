import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta

# URL de la API de SECOP
datos_secop_api = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
# URL de la API de Procesos de Contratación
datos_procesos_api = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

def consultar_secop_por_proveedor(proveedor):
    """Consulta contratos en SECOP filtrando por proveedor."""
    try:
        response = requests.get(datos_secop_api, params={"$where": f"upper(proveedor_adjudicado) like '%{proveedor.upper()}%' OR documento_proveedor = '{proveedor}'"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error en la consulta: {e}")
        return []

def consultar_procesos_por_proveedor(proveedor):
    """Consulta procesos de contratación filtrando por proveedor."""
    try:
        response = requests.get(datos_procesos_api, params={"$where": f"upper(nombre_del_proveedor) like '%{proveedor.upper()}%' OR nit_del_proveedor_adjudicado = '{proveedor}'"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error en la consulta: {e}")
        return []

def convertir_df_a_excel(df):
    """Convierte un DataFrame a un archivo Excel en memoria."""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Datos')
    writer.close()
    output.seek(0)
    return output

# Interfaz gráfica con Streamlit
st.image("banner.jpg", use_column_width=True)  # Agrega esta línea para mostrar la imagen
st.title("🔍 Denuncia Bien - Consulta de Contratos y Procesos de Contratación")

# Menú de selección
opcion = st.selectbox("Seleccione el módulo de consulta", ["Contratos Electrónicos SECOP II", "Procesos de Contratación"])

if opcion == "Contratos Electrónicos SECOP II":
    st.header("Contratos Electrónicos SECOP II")
    proveedor = st.text_input("Ingrese el nombre o identificador del proveedor:")
    if st.button("Buscar"):
        if proveedor:
            datos = consultar_secop_por_proveedor(proveedor)
            if datos:
                df = pd.DataFrame(datos)
                
                if "proveedor_adjudicado" in df.columns and "documento_proveedor" in df.columns and "tipodocproveedor" in df.columns:
                    nombres_proveedores = df[["proveedor_adjudicado", "documento_proveedor", "tipodocproveedor"]].drop_duplicates()
                    
                    if len(nombres_proveedores) > 1:
                        st.warning("⚠️ Existen múltiples razones sociales asociadas a este número de documento.")
                    
                    proveedor_nombre = nombres_proveedores.iloc[0]["proveedor_adjudicado"].upper()
                    tipo_doc = nombres_proveedores.iloc[0]["tipodocproveedor"].upper()
                    documento = nombres_proveedores.iloc[0]["documento_proveedor"]
                    
                    st.markdown(f"""
                    <h2 style='color:#D7263D; font-weight:bold;'>📌 Nombre Proveedor:</h2>
                    <h3 style='color:#0077CC; font-weight:bold;'>{proveedor_nombre}</h3>
                    <p style='font-size:16px;'><b>{tipo_doc}</b> : <span style='font-weight:bold; text-decoration: underline;'>{documento}</span></p>
                    """, unsafe_allow_html=True)
                
                col_valor = "valor_total_adjudicado" if "valor_total_adjudicado" in df.columns else "valor_del_contrato"
                if col_valor in df.columns:
                    df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce')
                    total_valor = df[col_valor].sum()
                    df[col_valor] = df[col_valor].apply(lambda x: f"${x:,.2f} COP" if pd.notna(x) else "N/A")
                else:
                    total_valor = 0
                    st.warning("No se encontró la columna de valor adjudicado en los datos.")
                
                num_contratos = len(df)
                num_entidades = df["nombre_entidad"].nunique() if "nombre_entidad" in df.columns else 0
                
                num_simultaneos = 0
                if "fecha_de_firma" in df.columns:
                    df["fecha_de_firma"] = pd.to_datetime(df["fecha_de_firma"], errors='coerce')
                    df = df.dropna(subset=["fecha_de_firma"])
                    df = df.sort_values("fecha_de_firma")
                    
                    if "fecha_fin" in df.columns:
                        df["fecha_fin"] = pd.to_datetime(df["fecha_fin"], errors='coerce')
                    else:
                        df["fecha_fin"] = df["fecha_de_firma"] + pd.DateOffset(months=6)
                    
                    fecha_actual = datetime.today()
                    contratos_en_ejecucion = df[(df["fecha_de_firma"] <= fecha_actual) & (df["fecha_fin"] >= fecha_actual)]
                    num_simultaneos = max(len(contratos_en_ejecucion) - 1, 0)
                
                st.markdown(f"""
                <div style="font-size:18px; font-weight:bold; margin-top:10px;">
                    💰 <b>Valor Total de Contratos:</b> ${total_valor:,.2f} COP
                </div>
                <div style="display:flex; gap:20px; margin-top:10px;">
                    <div>📜 <b>Número de Contratos:</b> {num_contratos}</div>
                    <div>🏢 <b>Total Entidades:</b> {num_entidades}</div>
                    <div>📆 <b>Contratos Simultáneos:</b> {num_simultaneos}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.divider()
                
                if "fecha_de_firma" in df.columns:
                    df["año_contrato"] = df["fecha_de_firma"].dt.year
                    contratos_por_año = df.groupby("año_contrato").size().reset_index(name="Cantidad de Contratos")
                    if not contratos_por_año.empty:
                        fig = px.bar(
                            contratos_por_año,
                            x="año_contrato",
                            y="Cantidad de Contratos",
                            title="📊 Contratos por Año",
                            text="Cantidad de Contratos",
                            labels={"año_contrato": "Año del Contrato", "Cantidad de Contratos": "Cantidad"},
                            color_discrete_sequence=["#E63946"]
                        )
                        fig.update_traces(textposition='outside')
                        fig.update_layout(font=dict(size=14), xaxis=dict(tickmode='linear'))
                        st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📜 Listado de Contratos")
                columnas_tabla = {
                    "nombre_entidad": "Entidad",
                    "id_contrato": "ID Contrato",
                    "estado_contrato": "Estado",
                    "justificacion_modalidad_de": "Justificación",
                    "fecha_de_firma": "Fecha de Firma",
                    "valor_del_contrato": "Valor del Contrato",
                    "objeto_del_contrato": "Objeto del Contrato"
                }
                df_mostrar = df[list(columnas_tabla.keys())].rename(columns=columnas_tabla)
                df_mostrar["Fecha de Firma"] = pd.to_datetime(df_mostrar["Fecha de Firma"], errors='coerce').dt.strftime("%d/%m/%Y")
                st.dataframe(df_mostrar, height=300)
                
                estado_counts = df["estado_contrato"].value_counts().reset_index()
                estado_counts.columns = ["Estado", "Cantidad"]
                fig_pie = px.pie(estado_counts, names="Estado", values="Cantidad", title="📊 Estado de los Contratos")
                st.plotly_chart(fig_pie, use_container_width=True)

                # Botón para descargar los datos en Excel
                output = convertir_df_a_excel(df)
                st.download_button(
                    label="📥 Descargar datos en Excel",
                    data=output,
                    file_name="contratos_secop_ii.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("No se encontraron datos para el proveedor ingresado.")

elif opcion == "Procesos de Contratación":
    st.header("Procesos de Contratación")
    proveedor_procesos = st.text_input("Ingrese el nombre o NIT del proveedor:")
    if st.button("Buscar Procesos"):
        if proveedor_procesos:
            datos_procesos = consultar_procesos_por_proveedor(proveedor_procesos)
            if datos_procesos:
                df_procesos = pd.DataFrame(datos_procesos)
                
                if "nombre_del_proveedor" in df_procesos.columns and "nit_del_proveedor_adjudicado" in df_procesos.columns:
                    nombres_proveedores_procesos = df_procesos[["nombre_del_proveedor", "nit_del_proveedor_adjudicado"]].drop_duplicates()
                    proveedor_nombre_procesos = nombres_proveedores_procesos.iloc[0]["nombre_del_proveedor"].upper()
                    nit_proveedor_procesos = nombres_proveedores_procesos.iloc[0]["nit_del_proveedor_adjudicado"]
                    
                    st.markdown(f"""
                    <h2 style='color:#D7263D; font-weight:bold;'>📌 Nombre del Proveedor:</h2>
                    <h3 style='color:#0077CC; font-weight:bold;'>{proveedor_nombre_procesos}</h3>
                    <p style='font-size:16px;'><b>NIT:</b> {nit_proveedor_procesos}</p>
                    """, unsafe_allow_html=True)
                
                if "precio_base" in df_procesos.columns:
                    df_procesos["precio_base"] = pd.to_numeric(df_procesos["precio_base"], errors='coerce')
                    total_valor_procesos = df_procesos["precio_base"].sum()
                else:
                    total_valor_procesos = 0
                    st.warning("No se encontró la columna de precio base en los datos.")
                
                num_procesos = len(df_procesos)
                num_entidades_procesos = df_procesos["entidad"].nunique() if "entidad" in df_procesos.columns else 0
                
                st.markdown(f"""
                <div style="font-size:18px; font-weight:bold; margin-top:10px;">
                    💰 <b>Valor Total de Procesos:</b> ${total_valor_procesos:,.2f} COP
                </div>
                <div style="display:flex; gap:20px; margin-top:10px;">
                    <div>📜 <b>Número de Procesos:</b> {num_procesos}</div>
                    <div>🏢 <b>Total Entidades:</b> {num_entidades_procesos}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.divider()
                
                if "fecha_de_publicacion_del_proceso" in df_procesos.columns:
                    df_procesos["año_proceso"] = pd.to_datetime(df_procesos["fecha_de_publicacion_del_proceso"], errors='coerce').dt.year
                    procesos_por_año = df_procesos.groupby("año_proceso").size().reset_index(name="Cantidad de Procesos")
                    st.write(procesos_por_año)  # Mensaje de depuración
                    if not procesos_por_año.empty:
                        fig_procesos = px.bar(
                            procesos_por_año,
                            x="año_proceso",
                            y="Cantidad de Procesos",
                            title="📊 Procesos de Contratación por Año",
                            text="Cantidad de Procesos",
                            labels={"año_proceso": "Año del Proceso", "Cantidad de Procesos": "Cantidad"},
                            color_discrete_sequence=["#2ca02c"]
                        )
                        fig_procesos.update_traces(textposition='outside')
                        fig_procesos.update_layout(font=dict(size=14))
                        st.plotly_chart(fig_procesos, use_container_width=True)
                
                st.subheader("📜 Listado de Procesos de Contratación")
                columnas_procesos = {
                    "entidad": "Entidad",
                    "nombre_del_proveedor": "Proveedor",
                    "nit_del_proveedor_adjudicado": "NIT Proveedor",
                    "fecha_de_publicacion_del_proceso": "Fecha de Publicación",
                    "precio_base": "Precio Base"
                }
                columnas_existentes = [col for col in columnas_procesos.keys() if col in df_procesos.columns]
                df_mostrar_procesos = df_procesos[columnas_existentes].rename(columns=columnas_procesos)
                if "fecha_de_publicacion_del_proceso" in df_mostrar_procesos.columns:
                    df_mostrar_procesos["Fecha de Publicación"] = pd.to_datetime(df_mostrar_procesos["fecha_de_publicacion_del_proceso"], errors='coerce').dt.strftime("%d/%m/%Y")
                if "precio_base" in df_mostrar_procesos.columns:
                    df_mostrar_procesos["Precio Base"] = df_mostrar_procesos["precio_base"].apply(lambda x: f"${x:,.2f} COP" if pd.notna(x) else "N/A")
                if "nombre_del_proveedor" in df_mostrar_procesos.columns:
                    df_mostrar_procesos["Proveedor"] = df_mostrar_procesos["nombre_del_proveedor"].str.upper()
                st.dataframe(df_mostrar_procesos, height=300)
                
                if "estado_proceso" in df_procesos.columns:
                    estado_counts_procesos = df_procesos["estado_proceso"].value_counts().reset_index()
                    estado_counts_procesos.columns = ["Estado", "Cantidad"]
                    fig_pie_procesos = px.pie(estado_counts_procesos, names="Estado", values="Cantidad", title="📊 Estado de los Procesos")
                    st.plotly_chart(fig_pie_procesos, use_container_width=True)

                # Botón para descargar los datos en Excel
                output = convertir_df_a_excel(df_procesos)
                st.download_button(
                    label="📥 Descargar datos en Excel",
                    data=output,
                    file_name="procesos_contratacion.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("No se encontraron datos para el proveedor ingresado.")