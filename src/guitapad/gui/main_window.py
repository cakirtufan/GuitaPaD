"""Main GuitaPaD desktop window."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from guitapad.runtime import (
    GuitaPadRuntime,
    RuntimeSnapshot,
)


def linear_to_db(value: float) -> float:
    """Convert linear gain to decibels."""

    if value <= 0.0:
        return -90.0

    return 20.0 * math.log10(value)


class MainWindow(QMainWindow):
    """Live control surface for the GuitaPaD audio engine."""

    def __init__(
        self,
        runtime: GuitaPadRuntime,
    ) -> None:
        super().__init__()

        self.runtime = runtime

        self.setWindowTitle("GuitaPaD")
        self.setMinimumSize(940, 680)
        self.resize(1080, 760)

        self._build_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(
            self.refresh_metrics
        )
        self.refresh_timer.start()

        self.refresh_metrics()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(18)

        root.addLayout(self._build_header())

        control_row = QHBoxLayout()
        control_row.setSpacing(18)
        control_row.addWidget(
            self._build_transport_card(),
            stretch=1,
        )
        control_row.addWidget(
            self._build_master_card(),
            stretch=2,
        )

        root.addLayout(control_row)
        root.addWidget(self._build_signal_chain_card())
        root.addWidget(
            self._build_performance_card(),
            stretch=1,
        )

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()

        title_column = QVBoxLayout()

        title = QLabel("GuitaPaD")
        title.setObjectName("title")

        subtitle = QLabel(
            "Real-time guitar processing ? "
            "Audient EVO 4 ? ASIO"
        )
        subtitle.setObjectName("subtitle")

        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        header.addLayout(title_column)
        header.addStretch()

        self.status_badge = QLabel("STOPPED")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumWidth(120)

        header.addWidget(self.status_badge)

        return header

    def _build_transport_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        section_title = QLabel("AUDIO ENGINE")
        section_title.setObjectName("sectionTitle")

        self.start_button = QPushButton("START")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(
            self.start_audio
        )

        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(
            self.stop_audio
        )

        layout.addWidget(section_title)
        layout.addSpacing(6)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addStretch()

        return card

    def _build_master_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        section_title = QLabel("MASTER OUTPUT")
        section_title.setObjectName("sectionTitle")

        value_row = QHBoxLayout()

        self.master_value = QLabel("0.60")
        self.master_value.setObjectName("bigValue")

        self.master_db = QLabel("-4.4 dB")
        self.master_db.setObjectName("subtitle")
        self.master_db.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        value_row.addWidget(self.master_value)
        value_row.addStretch()
        value_row.addWidget(self.master_db)

        self.master_slider = QSlider(
            Qt.Horizontal
        )
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(60)
        self.master_slider.valueChanged.connect(
            self.master_gain_changed
        )

        note = QLabel(
            "Software output level before the safety limiter"
        )
        note.setObjectName("subtitle")

        layout.addWidget(section_title)
        layout.addLayout(value_row)
        layout.addWidget(self.master_slider)
        layout.addWidget(note)

        return card

    def _build_signal_chain_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 20)
        outer.setSpacing(12)

        title = QLabel("SIGNAL CHAIN")
        title.setObjectName("sectionTitle")

        chain = QHBoxLayout()
        chain.setSpacing(10)

        for index, name in enumerate(
            [
                "INPUT 1",
                "MASTER GAIN",
                "SAFETY LIMITER",
                "OUTPUT 1?2",
            ]
        ):
            label = QLabel(name)
            label.setObjectName("signalBlock")
            label.setAlignment(Qt.AlignCenter)

            chain.addWidget(label)

            if index < 3:
                arrow = QLabel("?")
                arrow.setObjectName("subtitle")
                arrow.setAlignment(Qt.AlignCenter)
                chain.addWidget(arrow)

        outer.addWidget(title)
        outer.addLayout(chain)

        return card

    def _build_performance_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(16)

        title = QLabel("REAL-TIME PERFORMANCE")
        title.setObjectName("sectionTitle")

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(38)
        metrics.setVerticalSpacing(8)

        self.latency_value = self._add_metric(
            metrics,
            column=0,
            name="TOTAL LATENCY",
        )

        self.callback_value = self._add_metric(
            metrics,
            column=1,
            name="MAX CALLBACK",
        )

        self.callback_count_value = self._add_metric(
            metrics,
            column=2,
            name="CALLBACKS",
        )

        self.buffer_value = self._add_metric(
            metrics,
            column=3,
            name="TARGET BUFFER",
        )

        self.callback_load_bar = QProgressBar()
        self.callback_load_bar.setRange(0, 100)
        self.callback_load_bar.setValue(0)
        self.callback_load_bar.setTextVisible(False)

        self.callback_load_label = QLabel(
            "Callback deadline load: 0.0%"
        )
        self.callback_load_label.setObjectName(
            "subtitle"
        )

        self.error_label = QLabel(
            "No stream errors"
        )
        self.error_label.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addLayout(metrics)
        layout.addWidget(self.callback_load_label)
        layout.addWidget(self.callback_load_bar)
        layout.addWidget(self.error_label)

        return card

    @staticmethod
    def _add_metric(
        layout: QGridLayout,
        *,
        column: int,
        name: str,
    ) -> QLabel:
        value = QLabel("?")
        value.setObjectName("metricValue")

        label = QLabel(name)
        label.setObjectName("metricName")

        layout.addWidget(value, 0, column)
        layout.addWidget(label, 1, column)

        return value

    @Slot()
    def start_audio(self) -> None:
        try:
            self.runtime.start()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Audio engine error",
                str(error),
            )

        self.refresh_metrics()

    @Slot()
    def stop_audio(self) -> None:
        self.runtime.stop()
        self.refresh_metrics()

    @Slot(int)
    def master_gain_changed(
        self,
        slider_value: int,
    ) -> None:
        linear_gain = slider_value / 100.0

        self.runtime.set_master_gain(
            linear_gain
        )

        self.master_value.setText(
            f"{linear_gain:.2f}"
        )

        db_value = linear_to_db(
            linear_gain
        )

        if db_value <= -90.0:
            self.master_db.setText("-? dB")
        else:
            self.master_db.setText(
                f"{db_value:.1f} dB"
            )

    @Slot()
    def refresh_metrics(self) -> None:
        snapshot = self.runtime.snapshot()

        self._update_status(snapshot)

        self.start_button.setEnabled(
            not snapshot.running
        )
        self.stop_button.setEnabled(
            snapshot.running
        )

        if snapshot.total_latency_ms is None:
            self.latency_value.setText("?")
        else:
            self.latency_value.setText(
                f"{snapshot.total_latency_ms:.2f} ms"
            )

        self.callback_value.setText(
            f"{snapshot.maximum_callback_ms:.3f} ms"
        )

        self.callback_count_value.setText(
            f"{snapshot.callback_count:,}"
        )

        self.buffer_value.setText(
            f"{self.runtime.config.block_size}"
        )

        load_value = max(
            0.0,
            snapshot.callback_load_percent,
        )

        self.callback_load_bar.setValue(
            min(100, round(load_value))
        )

        self.callback_load_label.setText(
            "Callback deadline load: "
            f"{load_value:.1f}%"
        )

        if (
            snapshot.callback_error_count
            or snapshot.block_size_mismatch_count
        ):
            self.error_label.setText(
                "Callback errors: "
                f"{snapshot.callback_error_count} ? "
                "Block mismatches: "
                f"{snapshot.block_size_mismatch_count}"
            )
        else:
            self.error_label.setText(
                "No callback errors or block mismatches"
            )

    def _update_status(
        self,
        snapshot: RuntimeSnapshot,
    ) -> None:
        self.status_badge.setText(
            snapshot.stream_status
        )

        if snapshot.stream_status == "OK":
            self.status_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #173b2c;
                    color: #62d69b;
                    border: 1px solid #286848;
                    border-radius: 12px;
                    padding: 7px 14px;
                    font-weight: 800;
                }
                """
            )
        elif snapshot.stream_status == "STOPPED":
            self.status_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #252b33;
                    color: #9da7b4;
                    border: 1px solid #3b444f;
                    border-radius: 12px;
                    padding: 7px 14px;
                    font-weight: 800;
                }
                """
            )
        else:
            self.status_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #492323;
                    color: #ff8181;
                    border: 1px solid #7b3535;
                    border-radius: 12px;
                    padding: 7px 14px;
                    font-weight: 800;
                }
                """
            )

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.refresh_timer.stop()
        self.runtime.stop()
        event.accept()
