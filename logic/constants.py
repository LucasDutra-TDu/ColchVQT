# logic/constants.py
import os

# ============================
# 📌 NOTAS PARA DESARROLLADORES
# ============================
# - Este archivo debe contener SOLO:
#     ✔ Rutas de archivos locales
#     ✔ Mensajes para i18n centralizados
#     ✔ Configuraciones constantes
# - NO colocar funciones de negocio, carga de datos, ni lógica dinámica

# ============================
# 📁 CONFIGURACIÓN DE RUTAS
# ============================
LOCAL_FILENAME = "colchonería.xlsx"

# ============================
# 💬 MENSAJES CATEGORIZADOS
# ============================
messages = {
    "ui": {
        "app_title": "ColchonesApp",
    },
    "errors": {
        "descarga": "No se pudo descargar el archivo ni encontrar una copia local.\nEl programa se cerrará.",
        "fallo_descarga": "⚠️ Falló la descarga:",
        "fallo_total": "❌ No hay archivo local disponible.",
    },
    "logs": {
        "aviso_local": "No se pudo descargar el archivo actualizado.\nSe usará la copia local.",
        "descargando": "Descargando archivo desde Google Sheets...",
        "descarga_exitosa": "✅ Archivo descargado exitosamente.",
        "usando_local": "📄 Usando archivo local existente.",
        "inicio_aplicacion": "Iniciando aplicación..."
    }
}

# === UI DE CATALOGO ===
CATALOGO_UI = {
    "volver": "← Volver",
    "menu": {
        "tamano": "1 - Colchones por Tamaño",
        "marca": "2 - Productos por Marca",
        "sommiers": "3 - Almohadas / Sommiers",
        "otros": "4 - Otros productos"
    },
    "btn_copiar": "📋"
}

# === CAMPOS ESPERADOS POR SECCIÓN ===
CAMPOS_CATALOGO = {
    "colchones": [
        "PROVEEDOR", "MODELO", "MEDIDA (LARG-ANCH-ESP)", "MATERIAL",
        "SOPORTA (PorPlaza)", "EFECTIVO", "TRANSF/DEBIT/CREDIT", "3 CUOTAS", "6 CUOTAS"
    ],
    "otros": [
        "PROVEEDOR", "CARACTERISTICAS", "MODELO",
        "EFECTIVO", "TRANSF/DEBIT/CREDIT", "3 CUOTAS", "6 CUOTAS"
    ]
}

# === ANCHOS DE COLUMNA PARA CATALOGO VISUAL ===
CATALOGO_ANCHOS = {
    "COPIAR": 25,
    "PROVEEDOR": 100,
    "MODELO": 260,
    "MEDIDA (LARG-ANCH-ESP)": 95,
    "MATERIAL": 100,
    "SOPORTA (PorPlaza)": 80,
    "EFECTIVO": 85,
    "TRANSF/DEBIT/CREDIT": 85,
    "3 CUOTAS": 155,
    "6 CUOTAS": 155,
    "CARACTERISTICAS": 200
}

# === ESTILOS VISUALES REUTILIZABLES ===
"""ESTILOS = {
    #"boton_menu": "font-size: 16px; padding: 10px",
    #"titulo_columna": "padding: 0 2px; font-size: 13px; color: black; font-family: 'Arial Narrow', Arial, sans-serif;",
    #"celda": "padding: 0 2px; color: black; font-size: 14px; font-family: 'Arial Narrow', Arial, sans-serif;",
    #"header_fondo": "#ddd",
    #"fila_par": "#fff8d0",     # amarillo claro
    #"fila_impar": "#f0f0f0",   # gris claro
    #"padding_fila": "padding: 4px;"
}"""
# === ESTILOS VISUALES REUTILIZABLES (MODO OSCURO) ===
ESTILOS = {
    "boton_menu": "font-size: 16px; padding: 10px; background-color: #222; color: #fff;",
    "titulo_columna": "padding: 0 2px; font-size: 13px; color: #f0f0f0; font-family: 'Arial Narrow', Arial, sans-serif;",
    "celda": "padding: 0 2px; color: #e0e0e0; font-size: 14px; font-family: 'Arial Narrow', Arial, sans-serif;",
    "header_fondo": "#333",
    "fila_par": "#2a2a2a",
    "fila_impar": "#1e1e1e",
    "padding_fila": "padding: 4px;"
}


