#ui\catalogo.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QHBoxLayout, QFrame, QApplication, QStackedLayout
)
from PySide6.QtCore import Qt
from functools import partial
from logic.precios import calcular_precios_desde_fila
from logic.constants import CATALOGO_UI, CAMPOS_CATALOGO, CATALOGO_ANCHOS, ESTILOS
from logic.catalogo_utils import formatear_info_para_copiar, copiar_al_portapapeles
import pandas as pd

from logic.constants import CATALOGO_ANCHOS

class CatalogoWidget(QWidget):
    def __init__(self, sheets):
        super().__init__()
        self.sheets = sheets

        self.stack = QStackedLayout()
        self.vistas = {}

        self._init_menu()
        self.setLayout(self.stack)

    def _init_menu(self):
        menu = QWidget()
        layout = QVBoxLayout()

        opciones = [
            (CATALOGO_UI["menu"]["tamano"], self.abrir_colchones_tamano),
            (CATALOGO_UI["menu"]["marca"], self.abrir_colchones_marca),
            (CATALOGO_UI["menu"]["sommiers"], self.abrir_almohadas_sommiers),
            (CATALOGO_UI["menu"]["otros"], self.abrir_otros_productos)
        ]

        for texto, accion in opciones:
            btn = QPushButton(texto)
            btn.setStyleSheet(ESTILOS['boton_menu'])
            btn.clicked.connect(accion)
            layout.addWidget(btn)

        menu.setLayout(layout)
        self.vistas['menu'] = menu
        self.stack.addWidget(menu)

    def mostrar_vista(self, nombre):
        if nombre in self.vistas:
            self.stack.setCurrentWidget(self.vistas[nombre])
        elif isinstance(nombre, QWidget):
            self.stack.addWidget(nombre)
            self.stack.setCurrentWidget(nombre)

    def abrir_colchones_tamano(self):
        vista = QWidget()
        layout = QVBoxLayout()

        volver = QPushButton(CATALOGO_UI["volver"])
        volver.clicked.connect(lambda: self.mostrar_vista('menu'))
        layout.addWidget(volver)

        for nombre in ['1 PLAZA', '1 PLAZA Y MEDIA', '2 PLAZAS', 'QUEEN', 'KING']:
            btn = QPushButton(nombre)
            btn.setStyleSheet(ESTILOS['boton_menu'])
            btn.clicked.connect(partial(self._abrir_tabla_por_tamano, nombre))
            layout.addWidget(btn)

        vista.setLayout(layout)
        self.vistas['colchones_tamano'] = vista
        self.stack.addWidget(vista)
        self.mostrar_vista('colchones_tamano')

    def _abrir_tabla_por_tamano(self, nombre):
        df = self._obtener_colchones_por_tamano(nombre)
        self._mostrar_tabla_productos(df, 'colchones_tamano', CAMPOS_CATALOGO['colchones'], self._copiar_info_fila)

    def abrir_colchones_marca(self):
        df = self.sheets['GENERAL'].copy()
        df = df.dropna(subset=['PROVEEDOR'])
        df = self._agregar_precios_desde_fila(df)
        marcas = sorted(set(m.strip() for m in df['PROVEEDOR'].dropna().astype(str)))
        tiene_proveedor = df['PROVEEDOR'].notna()
        sin_proveedor = df[~tiene_proveedor]

        vista = QWidget()
        layout = QVBoxLayout()

        volver = QPushButton(CATALOGO_UI["volver"])
        volver.clicked.connect(lambda: self.mostrar_vista('menu'))
        layout.addWidget(volver)

        for marca in sorted(marcas):
            btn = QPushButton(marca)
            btn.setStyleSheet("font-size: 16px; padding: 10px;")
            btn.clicked.connect(partial(self._abrir_tabla_por_marca, df, marca))
            layout.addWidget(btn)

        if not sin_proveedor.empty:
            btn = QPushButton("Sin proveedor")
            btn.setStyleSheet("font-size: 16px; padding: 10px;")
            btn.clicked.connect(lambda: self._mostrar_tabla_productos(sin_proveedor, 'colchones_marca', CAMPOS_CATALOGO['colchones'], self._copiar_info_fila))
            layout.addWidget(btn)

        vista.setLayout(layout)
        self.vistas['colchones_marca'] = vista
        self.stack.addWidget(vista)
        self.mostrar_vista('colchones_marca')

    def _abrir_tabla_por_marca(self, df, marca):
        filtrado = df[df['PROVEEDOR'] == marca]
        self._mostrar_tabla_productos(filtrado, 'colchones_marca', CAMPOS_CATALOGO['colchones'], self._copiar_info_fila)

    def abrir_almohadas_sommiers(self):
        vista = QWidget()
        layout = QVBoxLayout()

        volver = QPushButton(CATALOGO_UI["volver"])
        volver.clicked.connect(lambda: self.mostrar_vista('menu'))
        layout.addWidget(volver)

        opciones = [
            ("Almohadas", 'ALMOHADAS'),
            ("Sommiers", 'SOMMIERS')
        ]

        for texto, hoja in opciones:
            btn = QPushButton(texto)
            btn.setStyleSheet("font-size: 16px; padding: 10px;")
            btn.clicked.connect(partial(self._abrir_tabla_generica, hoja, 'almohadas_sommiers'))
            layout.addWidget(btn)

        vista.setLayout(layout)
        self.vistas['almohadas_sommiers'] = vista
        self.stack.addWidget(vista)
        self.mostrar_vista('almohadas_sommiers')

    def _abrir_tabla_generica(self, hoja, origen):
        df = self.sheets[hoja].copy()
        df = df.dropna(subset=['COSTO']) if 'COSTO' in df.columns else df.dropna(subset=['costo'])
        df = self._agregar_precios_desde_fila(df)
        tipo = 'colchones' if hoja in ['ALMOHADAS', 'SOMMIERS'] else 'otros'
        campos = CAMPOS_CATALOGO.get(tipo, CAMPOS_CATALOGO['otros'])
        copiar = self._copiar_info_fila if tipo == 'colchones' else self._copiar_info_fila_otros
        self._mostrar_tabla_productos(df, origen, campos, copiar)

    def abrir_otros_productos(self):
        df = self._obtener_otros_productos()
        self._mostrar_tabla_productos(df, 'menu', CAMPOS_CATALOGO['otros'], self._copiar_info_fila_otros)

    def _obtener_colchones_por_tamano(self, nombre_hoja):
        df = self.sheets[nombre_hoja].copy()
        df.columns = [col.strip() for col in df.columns]
        df = df.dropna(subset=['COSTO'])
        df = self._agregar_precios_desde_fila(df)
        return df

    def _obtener_otros_productos(self):
        df = self.sheets['OTROS'].copy()
        df.columns = [col.strip() for col in df.columns]

        df = df.dropna(subset=['COSTO'])
        df = self._agregar_precios_desde_fila(df)
        return df

    def _agregar_precios_desde_fila(self, df):
        precios = df.apply(lambda row: calcular_precios_desde_fila(row), axis=1)
        for tipo in precios.iloc[0].keys():
            df[tipo] = precios.apply(lambda p: p[tipo])
        return df

    def _mostrar_tabla_productos(self, df, origen, campos, funcion_copiar):
        print(f"[INFO] Mostrando productos de {origen} ({len(df)} filas)")
        vista = QWidget()
        layout = QVBoxLayout()

        volver = QPushButton(CATALOGO_UI["volver"])
        volver.clicked.connect(lambda: self.mostrar_vista(origen))
        layout.addWidget(volver)

        scroll_area = QScrollArea()
        content = QWidget()
        content_layout = QVBoxLayout()

        # Agregar fila de títulos
        anchos = CATALOGO_ANCHOS
        header = QFrame()
        header.setStyleSheet(ESTILOS['header_fondo'])
        header_layout = QHBoxLayout()
        label_copiar = QLabel(CATALOGO_UI["btn_copiar"])
        label_copiar.setStyleSheet(ESTILOS['titulo_columna'])
        label_copiar.setFixedWidth(CATALOGO_ANCHOS["COPIAR"])
        header_layout.addWidget(label_copiar)
        for campo in campos:
            nombre_col = campo.replace("TRANSF/DEBIT/CREDIT", "TRNSF/DEB/CRE")
            titulo = QLabel(nombre_col)
            titulo.setStyleSheet(ESTILOS['titulo_columna'])
            titulo.setFixedWidth(anchos.get(campo, 100))
            header_layout.addWidget(titulo)
        header.setLayout(header_layout)
        content_layout.addWidget(header)

        for idx, row in df.iterrows():
            fila = self._crear_fila_visual(row, idx, campos, funcion_copiar)
            content_layout.addWidget(fila)

        content.setLayout(content_layout)
        scroll_area.setWidget(content)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        vista.setLayout(layout)
        self.stack.addWidget(vista)
        self.mostrar_vista(vista)

    def _crear_fila_visual(self, row, idx, campos, funcion_copiar):
        color = ESTILOS['fila_par'] if idx % 2 == 0 else ESTILOS['fila_impar']
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {color}; {ESTILOS['padding_fila']}")
        layout = QHBoxLayout()
        anchos = CATALOGO_ANCHOS

        btn_copiar = QPushButton(CATALOGO_UI["btn_copiar"])
        btn_copiar.setFixedWidth(CATALOGO_ANCHOS["COPIAR"])
        btn_copiar.clicked.connect(partial(funcion_copiar, row))
        layout.addWidget(btn_copiar)

        for campo in campos:
            valor = row.get(campo, "-")
            if pd.isnull(valor):
                texto = "-"
            elif campo.startswith("EFECTIVO") or campo.startswith("TRANSF"):
                texto = f"$ {valor}"
            elif campo.startswith("3") or campo.startswith("6"):
                cuotas = int(campo.split()[0])
                texto = f"$ {valor} ({cuotas}x ${int(valor) // cuotas})"
            else:
                texto = str(valor)
            label = QLabel(texto)
            label.setStyleSheet(ESTILOS['celda'])
            label.setFixedWidth(anchos.get(campo, 100))
            layout.addWidget(label)

        frame.setLayout(layout)
        return frame

    def _copiar_info_fila(self, fila):
        texto = formatear_info_para_copiar(fila, tipo="colchones")
        copiar_al_portapapeles(texto)

    def _copiar_info_fila_otros(self, fila):
        texto = formatear_info_para_copiar(fila, tipo="otros")
        copiar_al_portapapeles(texto)
