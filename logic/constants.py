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
        "SOPORTA (PorPlaza)", "EFECTIVO/TRANSF", "DEBIT/CREDIT", "3 CUOTAS", "6 CUOTAS"
    ],
    "otros": [
        "CARACTERISTICAS", "MODELO",
        "EFECTIVO/TRANSF", "DEBIT/CREDIT", "3 CUOTAS", "6 CUOTAS"
    ]
}

# === ANCHOS DE COLUMNA PARA CATALOGO VISUAL ===
CATALOGO_ANCHOS = {
    "COPIAR": 25,
    "PROVEEDOR": 100,
    "MODELO": 340,
    "MEDIDA (LARG-ANCH-ESP)": 120,
    "MATERIAL": 100,
    "SOPORTA (PorPlaza)": 90,
    "EFECTIVO/TRANSF": 95,
    "DEBIT/CREDIT": 95,
    "3 CUOTAS": 250,
    "6 CUOTAS": 250,
    "CARACTERISTICAS": 250
}

# === ESTILOS VISUALES REUTILIZABLES ===
ESTILOS = {
    "boton_menu": "font-size: 16px; padding: 10px",
    "boton_copiar": "font-size: 13px; padding: 0px 2px; background-color: #aaccee; color: #000;",
    "titulo_columna": "padding: 0 2px; font-size: 13px; color: black; font-family: 'Arial Narrow', Arial, sans-serif;",
    "celda_texto": "padding: 0 2px; font-size: 18px; color: black;",
    "celda_numero": "padding: 0 2px; font-size: 20px; color: black; qproperty-alignment: 'AlignRight';",
    "header_fondo": "#ddd",
    "fila_par": "#fff8d0",     # amarillo claro
    "fila_impar": "#f0f0f0",   # gris claro
    "padding_fila": "padding: 4px;",
    "boton_volver": "font-size: 14px; padding: 6px 10px; background-color: #ccc; color: #000; font-weight: bold;",
    "altura_celda": 26,
    "altura_encabezado": 32
}

# === ESTILOS VISUALES REUTILIZABLES (MODO OSCURO) ===
"""ESTILOS = {
    "boton_menu": "font-size: 16px; padding: 10px; background-color: #222; color: #fff;",
    "titulo_columna": "padding: 0 2px; font-size: 13px; color: #f0f0f0; font-family: 'Arial Narrow', Arial, sans-serif;",
    "celda": "padding: 0 2px; color: #e0e0e0; font-size: 14px; font-family: 'Arial Narrow', Arial, sans-serif;",
    "header_fondo": "#333",
    "fila_par": "#2a2a2a",
    "fila_impar": "#1e1e1e",
    "padding_fila": "padding: 4px;"
}"""

MENU_CONFIG = {
    "colchones": {
        "nombre": "Colchones",
        "tipo_producto": "colchones",
        "hojas": ["1 PLAZA", "1 PLAZA Y MEDIA", "2 PLAZAS", "QUEEN", "KING", "CUNA"]
    },
    "almohadas_sommiers": {
        "nombre": "Almohadas / Sommiers",
        "tipo_producto": "colchones",
        "hojas": ["ALMOHADAS", "SOMMIERS"]
    },
    "otros": {
        "nombre": "Otros Productos",
        "tipo_producto": "otros",
        "hojas": [
            "ACOLCHADOS", "ALFOMBRAS DE BAÑO", "AROMATIZADORES", "BATAS DE BAÑO",
            "CESTOS PARA ROPA", "FRAZADAS", "MUEBLES", "TOALLAS", "SABANAS", "RESPALDOS"
        ]
    }
}

# === CONFIGURACIÓN DE HOJAS DEL CATÁLOGO ===
SHEET_CONFIG = {
    "GENERAL": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "1 PLAZA": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "1 1/2 PLAZA": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "2 PLAZAS": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "QUEEN": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "KING": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO", "MATERIAL", "SOPORTA (PorPlaza)"],
        "copiar": "copiar_colchon"
    },
    "ALMOHADAS": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO"],
        "copiar": "copiar_otros"
    },
    "SOMMIERS": {
        "campos": ["PROVEEDOR", "MEDIDA (LARG-ANCH-ESP)", "MODELO"],
        "copiar": "copiar_otros"
    },
    "ALFOMBRAS DE BAÑO": {
        "campos": ["MODELO"],
        "copiar": "copiar_otros"
    },
    "AROMATIZADORES": {
        "campos": ["MODELO"],
        "copiar": "copiar_otros"
    },
    "CESTOS PARA ROPA": {
        "campos": ["MODELO"],
        "copiar": "copiar_otros"
    },
    "MUEBLES": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "SABANAS": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "TOALLAS": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "BATAS DE BAÑO": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "FRAZADAS": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "ACOLCHADOS": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    },
    "RESPALDOS": {
        "campos": ["CARACTERISTICAS", "MODELO"],
        "copiar": "copiar_otros"
    }
}


