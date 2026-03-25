# logic/constants.py
import sys
import os
from pathlib import Path

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

# --- RESOLUCIÓN DE RUTAS (Compatible con PyInstaller) ---
if getattr(sys, 'frozen', False):
    # Si estamos ejecutando el .exe compilado
    BASE_DIR = Path(sys.executable).parent
else:
    # Si estamos ejecutando main.py desde el código fuente (saliendo de la carpeta logic/)
    BASE_DIR = Path(__file__).parent.parent

# Rutas de Datos Compartidas
# Asumimos que BASE_DIR ya está definido apuntando a la raíz del proyecto
DATA_DIR = BASE_DIR / "data"
IMG_CATALOGO_DIR = DATA_DIR / "imagenes" # data/imagenes/
RECURSOS_DIR = DATA_DIR / "recursos"     # data/recursos/

# Recursos específicos para el Flyer
RUTA_FONT_FLYER = RECURSOS_DIR / "arial.ttf" # Necesitas conseguir este archivo .ttf
RUTA_LOGO_EMPRESA = RECURSOS_DIR / "logo_galpon.png" # Opcional .png transparente

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
        "SOPORTA (PORPLAZA)", "EFECTIVO/TRANSF", "DEBIT/CREDIT"
    ],
    "otros": [
        "CARACTERISTICAS", "MODELO",
        "EFECTIVO/TRANSF", "DEBIT/CREDIT"
    ]
}

# === ANCHOS DE COLUMNA PARA CATALOGO VISUAL ===
CATALOGO_ANCHOS = {
    "COPIAR": 25,
    "PROVEEDOR": 100,
    "MODELO": 340,
    "CARACTERISTICAS": 250,
    "MEDIDA (LARG-ANCH-ESP)": 120,
    "MATERIAL": 100,
    "SOPORTA (PORPLAZA)": 90,
    "EFECTIVO/TRANSF": 95,
    "DEBIT/CREDIT": 95
}

# === ESTILOS VISUALES REUTILIZABLES ===
ESTILOS = {
    "boton_menu": "font-size: 16px; padding: 10px",
    "boton_copiar": "font-size: 13px; padding: 0px 2px; background-color: #aaccee; color: #000;",
    "boton_ver_mas": "font-size: 13px; padding: 2px 6px; background-color: #ddd; color: #000;",
    "boton_volver": "font-size: 14px; padding: 6px 10px; background-color: #ccc; color: #000; font-weight: bold;",
    "titulo_columna": "padding: 0 2px; font-size: 13px; color: black; font-family: 'Arial Narrow', Arial, sans-serif;",
    "celda_texto": "padding: 0 2px; font-size: 18px; color: black;",
    "celda_numero": "padding: 0 2px; font-size: 20px; color: black; qproperty-alignment: 'AlignRight';",
    "header_fondo": "#ddd",
    "fila_par": "#fff8d0",     # amarillo claro
    "fila_impar": "#f0f0f0",   # gris claro
    "padding_fila": "padding: 4px;",
    "altura_celda": 26,
    "altura_encabezado": 32,
    "popup_detalle": {
        "titulo": "Crédito de La Casa",
        "icono": "information"
    }
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
        "tipo": "categoria",
        "hojas": ["1 PLAZA", "1 PLAZA Y MEDIA", "2 PLAZAS", "QUEEN", "KING", "CUNA"]
    },
    "almohadas_sommiers": {
        "nombre": "Almohadas / Sommiers",
        "tipo_producto": "colchones",
        "tipo": "categoria",
        "hojas": ["ALMOHADAS", "SOMMIERS"]
    },
    "otros": {
        "nombre": "Otros Productos",
        "tipo_producto": "otros",
        "tipo": "categoria",
        "hojas": [
            "ACOLCHADOS", "ALFOMBRAS DE BAÑO", "AROMATIZADORES", "BATAS DE BAÑO",
            "CESTOS PARA ROPA", "FRAZADAS", "MUEBLES", "TOALLAS", "SABANAS", "RESPALDOS"
        ]
    },
    "busqueda": {
        "nombre": "Buscar por nombre",
        "tipo": "busqueda"
    }
}

# Definición del Mapeo para el Portapapeles (Constante)
MAPEO_CLIPBOARD = [
    ("PROVEEDOR", "Marca"),
    ("MODELO", "Modelo"),
    ("MEDIDA (LARG-ANCH-ESP)", "Medida"),
    ("MATERIAL", "Material"),
    ("SOPORTA (PORPLAZA)", "PesoSoportado"),
    ("CARACTERISTICAS", "Detalle")
]

# Tasa de interés mensual para "Crédito de la Casa" (8%)
TASA_INTERES_MENSUAL = 0.08 

# Métodos de Pago
METODOS_PAGO = [
    "Efectivo / Transferencia",
    "Tarjeta Debito / Credito",
    "Crédito de la Casa"  # <--- Nuevo método especial
]