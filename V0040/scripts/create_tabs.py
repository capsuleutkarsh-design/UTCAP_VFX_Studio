import os

tabs = [
    'hrms_leave_tab', 'hrms_payroll_tab', 'hrms_onboarding_tab', 'hrms_performance_tab',
    'prod_scheduling_tab', 'prod_bidding_tab',
    'it_inventory_tab', 'it_licenses_tab', 'it_ticketing_tab', 'it_deployment_tab'
]

template = """from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class {class_name}(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("{class_name} - Under Construction")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #888;")
        layout.addWidget(label)
"""

base_dir = r"d:\Soft\UTCAP\V0040\ut_vfx\gui\tabs"

for tab in tabs:
    class_name = "".join(word.capitalize() for word in tab.split("_"))
    filepath = os.path.join(base_dir, tab + ".py")
    with open(filepath, "w") as f:
        f.write(template.format(class_name=class_name))
    print(f"Created {filepath}")
