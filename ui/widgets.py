from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QSpinBox, QLabel
from PySide6.QtCore import QDate, Signal

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