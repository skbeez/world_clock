import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QComboBox, QHBoxLayout, QDateTimeEdit, QPushButton,
    QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import QTimer, QDateTime, Qt
from PyQt5.QtGui import QIcon
import pytz
from datetime import datetime
import tzlocal
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller onefile """
    try:
        base_path = sys._MEIPASS  # PyInstaller extracts to temp folder
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

local_timezone_str = tzlocal.get_localzone_name()
local_tz = pytz.timezone(local_timezone_str)

def timezones_equivalent(now, tz1_str, tz2_str):
    tz1 = pytz.timezone(tz1_str)
    tz2 = pytz.timezone(tz2_str)
    return tz1.utcoffset(now) == tz2.utcoffset(now)

class TimeZoneWidget(QWidget):
    def __init__(self, default_tz):
        super().__init__()
        self.layout = QVBoxLayout()

        self.combo = QComboBox()
        self.combo.addItems(pytz.all_timezones)
        self.combo.setCurrentText(default_tz)

        self.live_label = QLabel()
        self.live_label.setStyleSheet("font-size: 16px; padding: 6px;")
        self.live_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.combo)
        self.layout.addWidget(self.live_label)
        self.setLayout(self.layout)

        self.use_24h = True
        self.update_live_time()

    def update_live_time(self, use_24h=True):
        self.use_24h = use_24h
        tz = pytz.timezone(self.combo.currentText())
        now = datetime.now(tz)
        line1 = now.strftime('%a %b %d, %Y')
        if use_24h:
            line2 = now.strftime('%H:%M:%S %Z')
        else:
            line2 = now.strftime('%I:%M:%S %p %Z')

        self.live_label.setText(f"{line1}\n{line2}")

    def current_timezone(self):
        return self.combo.currentText()

class TimeZoneApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Clock")
        self.resize(1000, 500)
        self.use_24h = False

        self.main_layout = QVBoxLayout()

        # ─── Display Format Toggle ───
        top_row = QHBoxLayout()
        top_row.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.format_label = QLabel("Display Format:")
        self.format_toggle = QComboBox()
        self.format_toggle.addItems(["12-hour", "24-hour"])
        self.format_toggle.setCurrentIndex(0)
        self.format_toggle.currentTextChanged.connect(self.toggle_format)
        top_row.addWidget(self.format_label)
        top_row.addWidget(self.format_toggle)
        self.main_layout.addLayout(top_row)

        # ─── TimeZone Widgets Row ───
        self.timezone_widgets = []
        self.clock_row = QHBoxLayout()
        reference_zones = ['US/Eastern', 'US/Pacific', 'Europe/Paris', 'Asia/Kolkata', 'Asia/Tokyo']
        now = datetime.now()
        other_timezones = [tz for tz in reference_zones if not timezones_equivalent(now, tz, local_timezone_str)]
        default_timezones = [local_timezone_str] + other_timezones[:4]

        for tz in default_timezones:
            widget = TimeZoneWidget(tz)
            self.timezone_widgets.append(widget)
            self.clock_row.addWidget(widget)
            widget.combo.currentTextChanged.connect(self.update_projected_times)

        self.main_layout.addLayout(self.clock_row)

        # ─── Meeting Time Input Row ───
        controls_row = QHBoxLayout()
        self.datetime_label = QLabel("Project a meeting time (local time):")
        self.datetime_label.setStyleSheet("font-weight: bold;")

        # Date picker
        self.date_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setCalendarPopup(True)
        self.date_input.setTimeSpec(Qt.LocalTime)
        self.date_input.setFixedHeight(28)
        self.date_input.setMinimumWidth(130)
        self.date_input.dateTimeChanged.connect(self.update_projected_times)

        # Time picker
        self.time_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.time_input.setDisplayFormat("hh:mm AP")
        self.time_input.setFixedHeight(28)
        self.time_input.setMinimumWidth(100)
        self.time_input.setTimeSpec(Qt.LocalTime)
        self.time_input.setCurrentSection(QDateTimeEdit.HourSection)
        self.time_input.dateTimeChanged.connect(self.update_projected_times)

        # Now button
        self.now_button = QPushButton("Now")
        self.now_button.setFont(self.time_input.font())
        self.now_button.setStyleSheet("padding: 2px 8px;")
        self.now_button.setFixedHeight(28)
        self.now_button.clicked.connect(self.set_now)

        controls_row.addWidget(self.datetime_label)
        controls_row.addWidget(self.date_input)
        controls_row.addWidget(self.time_input)
        controls_row.addWidget(self.now_button)
        controls_row.addStretch()

        self.main_layout.addLayout(controls_row)

        # ─── Projected Times Row ───
        self.projected_row = QHBoxLayout()
        self.projected_labels = []
        for _ in self.timezone_widgets:
            label = QLabel()
            label.setStyleSheet("font-size: 16px; padding: 6px; color: gray;")
            label.setAlignment(Qt.AlignCenter)
            self.projected_labels.append(label)
            self.projected_row.addWidget(label)

        self.main_layout.addLayout(self.projected_row)

        self.setLayout(self.main_layout)

        # ─── Timers ───
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all_live_times)
        self.timer.start(1000)

        self.update_all_live_times()
        self.update_projected_times()

    def update_all_live_times(self):
        for widget in self.timezone_widgets:
            widget.update_live_time(self.use_24h)

    def update_projected_times(self):
        from datetime import datetime as dt
        local_dt = dt.combine(
            self.date_input.date().toPyDate(),
            self.time_input.time().toPyTime()
        )
        for widget, label in zip(self.timezone_widgets, self.projected_labels):
            tz = pytz.timezone(widget.current_timezone())
            try:
                local_aware = local_tz.localize(local_dt)
            except Exception:
                local_aware = local_dt.astimezone(local_tz)
            target_time = local_aware.astimezone(tz)
            line1 = target_time.strftime('%a %b %d, %Y')
            if self.use_24h:
                line2 = target_time.strftime('%H:%M:%S %Z')
            else:
                line2 = target_time.strftime('%I:%M:%S %p %Z')

            label.setText(f"{line1}\n{line2}")

    def set_now(self):
        now = QDateTime.currentDateTime()
        self.date_input.setDate(now.date())
        self.time_input.setTime(now.time())

    def toggle_format(self, text):
        self.use_24h = (text == "24-hour")
        if self.use_24h:
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.time_input.setDisplayFormat("HH:mm")
        else:
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.time_input.setDisplayFormat("hh:mm AP")
        self.update_all_live_times()
        self.update_projected_times()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("app_icon.png")))
    window = TimeZoneApp()
    window.show()
    sys.exit(app.exec_())
