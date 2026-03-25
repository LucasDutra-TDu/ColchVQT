from PySide6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QComboBox, QSpinBox, QLabel, QDialog, QVBoxLayout, QPushButton, QApplication, QMessageBox
from PySide6.QtCore import QDate, Signal, Qt
import os
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path


class MonthYearSelector(QWidget):
    # Señal para avisar a la ventana padre que cambió la fecha
    dateChanged = Signal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Selector de Mes
        self.combo_mes = QComboBox()
        self.meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        self.combo_mes.addItems(self.meses)
        
        # Selector de Año
        self.spin_anio = QSpinBox()
        self.spin_anio.setRange(2020, 2040)
        
        # Setear fecha actual por defecto
        hoy = QDate.currentDate()
        self.combo_mes.setCurrentIndex(hoy.month() - 1)
        self.spin_anio.setValue(hoy.year())
        
        # Conectar señales
        self.combo_mes.currentIndexChanged.connect(lambda: self.dateChanged.emit())
        self.spin_anio.valueChanged.connect(lambda: self.dateChanged.emit())
        
        layout.addWidget(self.combo_mes)
        layout.addWidget(self.spin_anio)

    def get_date(self):
        """Devuelve (mes, anio) como enteros."""
        return self.combo_mes.currentIndex() + 1, self.spin_anio.value()
    
class SuccessDialog(QDialog):
    def __init__(self, titulo, mensaje, ruta_archivo=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(450, 200)
        self.ruta_archivo = ruta_archivo
        
        layout = QVBoxLayout(self)
        
        # Icono y Mensaje
        lbl_msg = QLabel(mensaje)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl_msg)
        
        if ruta_archivo:
            # Caja con la ruta para que se vea bien
            lbl_path = QLabel(ruta_archivo)
            lbl_path.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; font-family: Consolas;")
            lbl_path.setWordWrap(True)
            lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse) # Permitir seleccionar texto
            layout.addWidget(lbl_path)

        # Botones
        btn_layout = QHBoxLayout()
        
        if ruta_archivo:
            btn_copy = QPushButton("📋 Copiar Ruta")
            btn_copy.clicked.connect(self.copiar_ruta)
            btn_layout.addWidget(btn_copy)
            
            btn_open = QPushButton("📂 Abrir Carpeta")
            btn_open.clicked.connect(self.abrir_carpeta)
            btn_layout.addWidget(btn_open)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def copiar_ruta(self):
        if self.ruta_archivo:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.ruta_archivo)
            QMessageBox.information(self, "Copiado", "Ruta copiada al portapapeles.")

    def abrir_carpeta(self):
        if self.ruta_archivo:
            try:
                folder = os.path.dirname(self.ruta_archivo)
                os.startfile(folder)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo abrir la carpeta: {e}")

class ImageViewerDialog(QDialog):
    """
    Ventana modal para visualizar la imagen de un producto en tamaño grande.
    """
    def __init__(self, parent, titulo_producto: str, ruta_imagen: Path):
        super().__init__(parent)
        self.setWindowTitle(f"Ver Imagen - {titulo_producto}")
        # Asegura que sea una ventana modal bloqueante
        self.setWindowModality(Qt.WindowModal) 
        
        # Tamaño inicial razonable, pero permite redimensionar
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Label contenedor de la imagen
        self.lbl_imagen = QLabel()
        self.lbl_imagen.setAlignment(Qt.AlignCenter)
        # Permite que la QLabel se achique/estire si redimensionamos la ventana
        self.lbl_imagen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored) 
        layout.addWidget(self.lbl_imagen)

        # 2. Guardar la ruta y cargar la imagen inicial
        self.ruta_imagen = str(ruta_imagen)
        self.original_pixmap = QPixmap(self.ruta_imagen)
        
        # 3. Botón de Cerrar (Abajo)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(100)
        btn_cerrar.clicked.connect(self.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Centrar el botón
        button_layout.addWidget(btn_cerrar)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Aplicar estilos si tienes definidos para botones normales
        # from ui.style import ESTILOS (asumiendo que está disponible)
        # btn_cerrar.setStyleSheet(ESTILOS.get('boton_volver', ''))

    def showEvent(self, event):
        """Al mostrar la ventana, escalamos la imagen por primera vez."""
        super().showEvent(event)
        self.actualizar_imagen_escalada()

    def resizeEvent(self, event):
        """Al redimensionar la ventana, re-escalamos la imagen."""
        super().resizeEvent(event)
        if not self.original_pixmap.isNull():
            self.actualizar_imagen_escalada()

    def actualizar_imagen_escalada(self):
        """Escala la imagen para que quepa en el QLabel actual manteniendo ratio."""
        if self.lbl_imagen.size().width() <= 0: return
        
        # Calculamos la escala manteniendo la relación de aspecto
        scaled_pixmap = self.original_pixmap.scaled(
            self.lbl_imagen.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.lbl_imagen.setPixmap(scaled_pixmap)
