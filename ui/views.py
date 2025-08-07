from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QSizePolicy, QLineEdit, QMessageBox
from PySide6.QtCore import Qt
from logic.constants import ESTILOS, MENU_CONFIG, CAMPOS_CATALOGO, CATALOGO_ANCHOS, CAMPOS_OCULTOS
from logic import catalogo_utils_v2
from logic.catalogo_utils_v2 import obtener_df_por_hoja
from typing import Callable
from functools import partial
import re
import pandas as pd

def build_tabla_productos(df, campos, copiar_callback):
    contenedor = QWidget()
    layout_principal = QVBoxLayout(contenedor)
    contenedor.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

    # Encabezados de columna
    header_layout = QHBoxLayout()
    copiar_header = QLabel("")
    copiar_header.setFixedWidth(CATALOGO_ANCHOS["COPIAR"])
    copiar_header.setFixedHeight(ESTILOS["altura_encabezado"])
    header_layout.addWidget(copiar_header)
    for campo in campos:
        label = QLabel(campo)
        label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))
        label.setStyleSheet(ESTILOS.get("titulo_columna", ""))
        label.setWordWrap(True)
        label.setFixedHeight(ESTILOS["altura_encabezado"])
        header_layout.addWidget(label)
    header_layout.addWidget(QLabel(""))  # espacio para botón "..."
    layout_principal.addLayout(header_layout)

    def crear_funcion_detalle(fila_dict_local):
        def mostrar_detalle():
            detalles = []
            for campo in CAMPOS_OCULTOS:
                if campo in fila_dict_local and pd.notna(fila_dict_local[campo]):
                    valor = fila_dict_local[campo]
                    if isinstance(valor, (int, float)):
                        valor = f"${valor:,.0f}".replace(",", ".")
                    detalles.append(f"{ESTILOS['popup_detalle']['prefijo']}{campo}: {valor}")
            icon_str = ESTILOS["popup_detalle"].get("icono", "information")
            icon = {
                "information": QMessageBox.Information,
                "warning": QMessageBox.Warning,
                "critical": QMessageBox.Critical,
                "question": QMessageBox.Question
            }.get(icon_str, QMessageBox.Information)
            msg_box = QMessageBox()
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(ESTILOS["popup_detalle"]["titulo"])
            msg_box.setText("\n".join(detalles))
            msg_box.exec()
        return mostrar_detalle

    for i, fila in df.iterrows():
        layout_fila = QHBoxLayout()
        estilo_fondo = ESTILOS['fila_par'] if i % 2 == 0 else ESTILOS['fila_impar']

        fila_widget = QWidget()
        fila_widget.setStyleSheet(f"background-color: {estilo_fondo};")
        fila_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        info_fila = {}

        # Botón de copiado de fila
        boton = QPushButton("📋")
        boton.setStyleSheet(ESTILOS['boton_copiar'])
        boton.setMaximumWidth(CATALOGO_ANCHOS["COPIAR"])
        boton.setMinimumWidth(CATALOGO_ANCHOS["COPIAR"])
        boton.setFixedHeight(ESTILOS["altura_celda"])
        boton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        boton.clicked.connect(partial(copiar_callback, info_fila))
        layout_fila.addWidget(boton)

        for campo in campos:
            valor = fila.get(campo, "")
            es_numerico = False
            if isinstance(valor, (int, float)):
                es_numerico = True
                valor = f"${valor:,.0f}"
            else:
                valor = str(valor)

            valor = valor.replace(",", ".")
            label = QLabel(valor)
            label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))
            label.setStyleSheet((ESTILOS.get("celda_numero") if es_numerico else ESTILOS.get("celda_texto")) or "")
            label.setFixedHeight(ESTILOS["altura_celda"])
            layout_fila.addWidget(label)
            info_fila[campo] = valor

        # Botón para mostrar precios adicionales
        btn_mas = QPushButton("⋯")
        btn_mas.setStyleSheet(ESTILOS.get("boton_ver_mas", ""))
        btn_mas.setFixedHeight(ESTILOS["altura_celda"])
        btn_mas.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_mas.clicked.connect(crear_funcion_detalle(fila.to_dict()))
        layout_fila.addWidget(btn_mas)

        fila_widget.setLayout(layout_fila)
        layout_principal.addWidget(fila_widget)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(contenedor)
    scroll.setFrameShape(QFrame.NoFrame)

    return scroll

def build_categoria_view(key: str, sheets: dict, volver_callback: Callable, tipo_producto: str = "colchones") -> QWidget:
    vista = QWidget()
    layout = QVBoxLayout(vista)

    campos = [c for c in CAMPOS_CATALOGO[tipo_producto] if c != "COSTO"]
    copiar_callback = getattr(catalogo_utils_v2, f"copiar_info_{tipo_producto}")

    df = obtener_df_por_hoja(sheets, key)
    campos_visibles = [c for c in campos if c in df.columns]

    tabla = build_tabla_productos(df, campos_visibles, copiar_callback)
    layout.addWidget(tabla)

    boton_volver = QPushButton("Volver al Menú")
    boton_volver.setStyleSheet(ESTILOS['boton_volver'])
    boton_volver.clicked.connect(volver_callback)
    layout.addWidget(boton_volver)

    return vista

def build_menu_view(opciones: dict, on_click: Callable[[str], None], estilo_boton: str, volver_callback: Callable = None) -> QWidget:
    menu = QWidget()
    layout = QVBoxLayout(menu)

    for key, config in opciones.items():
        nombre = config.get("nombre", key)
        boton = QPushButton(nombre)
        boton.setStyleSheet(estilo_boton)
        boton.clicked.connect(lambda _, k=key: on_click(k))
        layout.addWidget(boton)

    if volver_callback:
        boton_volver = QPushButton("Volver")
        boton_volver.setStyleSheet(ESTILOS['boton_volver'])
        boton_volver.clicked.connect(volver_callback)
        layout.addWidget(boton_volver)

    return menu

def build_busqueda_view(on_buscar: Callable[[str], pd.DataFrame], volver_callback: Callable) -> QWidget:
    vista = QWidget()
    layout = QVBoxLayout(vista)

    input_codigo = QLineEdit()
    input_codigo.setPlaceholderText("Ingrese el código del producto...")
    layout.addWidget(input_codigo)

    boton_buscar = QPushButton("Buscar")
    boton_buscar.setStyleSheet(ESTILOS["boton_volver"])
    layout.addWidget(boton_buscar)

    resultados_contenedor = QWidget()
    resultados_layout = QVBoxLayout(resultados_contenedor)
    layout.addWidget(resultados_contenedor)

    def ejecutar_busqueda():
        codigo = input_codigo.text().strip()
        if codigo:
            df = on_buscar(codigo)
            for i in reversed(range(resultados_layout.count())):
                widget = resultados_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
            if not df.empty:
                campos_visibles = [col for col in df.columns if col == "CÓDIGO" or col == "CODIGO" or col in CAMPOS_CATALOGO.get("colchones", []) or col in CAMPOS_CATALOGO.get("otros", [])]
                tabla = build_tabla_productos(df, campos_visibles, catalogo_utils_v2.copiar_info_busqueda)
                resultados_layout.addWidget(tabla)

    boton_buscar.clicked.connect(ejecutar_busqueda)

    boton_volver = QPushButton("Volver al Menú")
    boton_volver.setStyleSheet(ESTILOS['boton_volver'])
    boton_volver.clicked.connect(volver_callback)
    layout.addWidget(boton_volver)

    return vista
