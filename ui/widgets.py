from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QSpinBox, QLabel, QDialog, QVBoxLayout, QPushButton, QApplication, QMessageBox
from PySide6.QtCore import QDate, Signal, Qt
import os

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