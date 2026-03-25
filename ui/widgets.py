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
    def __init__(self, parent, titulo_producto: str, ruta_imagen: Path):
        super().__init__(parent)
        self.setWindowTitle(f"Ver Imagen - {titulo_producto}")
        self.setWindowModality(Qt.WindowModal) 
        self.setStyleSheet("background-color: #1e1e1e;") 
        
        # Eliminar los bordes de la ventana para que sea realmente pantalla completa
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Cero márgenes
        layout.setSpacing(0)

        # 1. EL CONTENEDOR DE IMAGEN
        self.lbl_imagen = QLabel()
        self.lbl_imagen.setAlignment(Qt.AlignCenter)
        # IMPORTANTE: Esto le permite usar todo el espacio sin restricciones
        self.lbl_imagen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        self.lbl_imagen.setMinimumSize(1, 1) 
        layout.addWidget(self.lbl_imagen)

        self.ruta_imagen = str(ruta_imagen)
        self.original_pixmap = QPixmap(self.ruta_imagen)
        
        # 2. BOTÓN DE CERRAR
        btn_cerrar = QPushButton("Cerrar Imagen (Esc)")
        btn_cerrar.setFixedWidth(250)
        btn_cerrar.setFixedHeight(45)
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; font-weight: bold;
                border-radius: 10px; margin-bottom: 20px; border: 2px solid #c0392b;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_cerrar.clicked.connect(self.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_cerrar)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 3. MAXIMIZAR Y CARGAR CON RETRASO
        self.showMaximized()
        
        # El truco maestro: Esperamos 100ms a que Windows termine de estirar la ventana
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.actualizar_imagen_escalada)

    def keyPressEvent(self, event):
        # Si presionan Esc, cerramos (por si el FramelessWindowHint quita el comportamiento por defecto)
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Usamos un timer singleShot para no saturar el procesador mientras arrastras, 
        # pero que siempre actualice al tamaño final.
        self.actualizar_imagen_escalada()

    def actualizar_imagen_escalada(self):
        # Forzamos a procesar eventos para que width() y height() sean reales
        QApplication.processEvents()
        
        ancho = self.lbl_imagen.width()
        alto = self.lbl_imagen.height()

        if ancho <= 10 or alto <= 10:
            return
        
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            # Escalado suave a pantalla completa
            scaled_pixmap = self.original_pixmap.scaled(
                ancho,
                alto,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.lbl_imagen.setPixmap(scaled_pixmap)

