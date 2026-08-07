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
        self._di_save_pending = False

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
        root.addWidget(self._build_level_meter_card())
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
            "Real-time guitar processing | "
            "Audient EVO 4 | ASIO"
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

        self.record_button = QPushButton(
            "RECORD DI"
        )
        self.record_button.setObjectName(
            "recordButton"
        )
        self.record_button.setCheckable(True)
        self.record_button.clicked.connect(
            self.toggle_di_recording
        )

        self.recording_note = QLabel(
            "Raw input | 24-bit WAV | max 10 s"
        )
        self.recording_note.setObjectName(
            "subtitle"
        )

        layout.addWidget(section_title)
        layout.addSpacing(6)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.record_button)
        layout.addWidget(self.recording_note)
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


    def _build_level_meter_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(10)

        title = QLabel("SIGNAL LEVELS")
        title.setObjectName("sectionTitle")

        input_header = QHBoxLayout()

        input_name = QLabel("INPUT")
        input_name.setObjectName("metricName")

        self.input_meter_value = QLabel("-90.0 dBFS")
        self.input_meter_value.setObjectName("subtitle")
        self.input_meter_value.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        input_header.addWidget(input_name)
        input_header.addStretch()
        input_header.addWidget(
            self.input_meter_value
        )

        self.input_meter = QProgressBar()
        self.input_meter.setObjectName("inputMeter")
        self.input_meter.setRange(0, 600)
        self.input_meter.setValue(0)
        self.input_meter.setTextVisible(False)

        output_header = QHBoxLayout()

        output_name = QLabel("OUTPUT")
        output_name.setObjectName("metricName")

        self.output_meter_value = QLabel("-90.0 dBFS")
        self.output_meter_value.setObjectName("subtitle")
        self.output_meter_value.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        output_header.addWidget(output_name)
        output_header.addStretch()
        output_header.addWidget(
            self.output_meter_value
        )

        self.output_meter = QProgressBar()
        self.output_meter.setObjectName("outputMeter")
        self.output_meter.setRange(0, 600)
        self.output_meter.setValue(0)
        self.output_meter.setTextVisible(False)

        layout.addWidget(title)
        layout.addLayout(input_header)
        layout.addWidget(self.input_meter)
        layout.addSpacing(4)
        layout.addLayout(output_header)
        layout.addWidget(self.output_meter)

        return card

    def _build_signal_chain_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 20)
        outer.setSpacing(12)

        title = QLabel("SIGNAL CHAIN")
        title.setObjectName("sectionTitle")

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()

        self.hpf_button = QPushButton("HPF ON")
        self.hpf_button.setObjectName("hpfButton")
        self.hpf_button.setCheckable(True)
        self.hpf_button.setChecked(True)
        self.hpf_button.clicked.connect(
            self.high_pass_toggled
        )

        header.addWidget(self.hpf_button)

        self.overdrive_button = QPushButton(
            "OVERDRIVE ON"
        )
        self.overdrive_button.setObjectName(
            "overdriveButton"
        )
        self.overdrive_button.setCheckable(True)
        self.overdrive_button.setChecked(True)
        self.overdrive_button.clicked.connect(
            self.overdrive_toggled
        )

        header.addWidget(
            self.overdrive_button
        )

        chain = QHBoxLayout()
        chain.setSpacing(10)

        for index, name in enumerate(
            [
                "INPUT 1",
                "HPF 35 Hz",
                "OVERDRIVE V3",
                "MASTER GAIN",
                "SAFETY LIMITER",
                "OUTPUT 1/2",
            ]
        ):
            label = QLabel(name)
            label.setObjectName("signalBlock")
            label.setAlignment(Qt.AlignCenter)

            chain.addWidget(label)

            if index < 3:
                arrow = QLabel("->")
                arrow.setObjectName("subtitle")
                arrow.setAlignment(Qt.AlignCenter)
                chain.addWidget(arrow)

        outer.addLayout(header)
        outer.addLayout(chain)

        drive_row = QHBoxLayout()

        drive_name = QLabel("DRIVE")
        drive_name.setObjectName("metricName")

        self.overdrive_drive_slider = QSlider(
            Qt.Horizontal
        )
        self.overdrive_drive_slider.setRange(
            0,
            36,
        )
        self.overdrive_drive_slider.setValue(
            12
        )
        self.overdrive_drive_slider.valueChanged.connect(
            self.overdrive_drive_changed
        )

        self.overdrive_drive_value = QLabel(
            "12 dB"
        )
        self.overdrive_drive_value.setObjectName(
            "subtitle"
        )
        self.overdrive_drive_value.setMinimumWidth(
            55
        )
        self.overdrive_drive_value.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        drive_row.addWidget(drive_name)
        drive_row.addWidget(
            self.overdrive_drive_slider,
            stretch=1,
        )
        drive_row.addWidget(
            self.overdrive_drive_value
        )

        outer.addLayout(drive_row)

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
        value = QLabel("->")
        value.setObjectName("metricValue")

        label = QLabel(name)
        label.setObjectName("metricName")

        layout.addWidget(value, 0, column)
        layout.addWidget(label, 1, column)

        return value

    @Slot()
    def toggle_di_recording(self) -> None:
        if self.runtime.is_di_recording:
            self._stop_di_and_schedule_save()
            return

        try:
            self.runtime.start_di_recording()
        except Exception as error:
            QMessageBox.critical(
                self,
                "DI recording error",
                str(error),
            )
            return

        self.record_button.setChecked(True)
        self.record_button.setText(
            "STOP RECORDING"
        )
        self.recording_note.setText(
            "Recording raw Input 1..."
        )

        # Safety auto-stop at ten seconds.
        QTimer.singleShot(
            10_000,
            self._auto_stop_di_recording,
        )

    @Slot()
    def _auto_stop_di_recording(self) -> None:
        if self.runtime.is_di_recording:
            self._stop_di_and_schedule_save()

    def _stop_di_and_schedule_save(self) -> None:
        if not self.runtime.is_di_recording:
            return

        self.runtime.stop_di_recording()

        self._di_save_pending = True

        self.record_button.setEnabled(False)
        self.record_button.setText(
            "SAVING..."
        )

        # Give any in-flight callback plenty of time
        # to leave the preallocated recording buffer.
        QTimer.singleShot(
            40,
            self._save_di_recording,
        )

    @Slot()
    def _save_di_recording(self) -> None:
        try:
            path = (
                self.runtime.save_di_recording()
            )

            self.recording_note.setText(
                f"Saved: recordings/{path.name}"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "DI recording error",
                str(error),
            )

            self.recording_note.setText(
                "Recording was not saved"
            )

        finally:
            self._di_save_pending = False

            self.record_button.setChecked(
                False
            )
            self.record_button.setText(
                "RECORD DI"
            )

            self.refresh_metrics()

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
        if self.runtime.is_di_recording:
            self._stop_di_and_schedule_save()

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
            self.master_db.setText("-inf dB")
        else:
            self.master_db.setText(
                f"{db_value:.1f} dB"
            )

    @Slot(bool)
    def high_pass_toggled(
        self,
        enabled: bool,
    ) -> None:
        self.runtime.set_high_pass_enabled(
            enabled
        )

        self._update_hpf_button(enabled)

    def _update_hpf_button(
        self,
        enabled: bool,
    ) -> None:
        desired_text = (
            "HPF ON"
            if enabled
            else "HPF BYPASS"
        )

        # Avoid touching Qt state during every 100 ms metrics refresh
        # when nothing has actually changed.
        if (
            self.hpf_button.isChecked() == enabled
            and self.hpf_button.text() == desired_text
        ):
            return

        self.hpf_button.blockSignals(True)
        self.hpf_button.setChecked(enabled)
        self.hpf_button.setText(desired_text)
        self.hpf_button.blockSignals(False)

    @Slot(bool)
    def overdrive_toggled(
        self,
        enabled: bool,
    ) -> None:
        self.runtime.set_overdrive_enabled(
            enabled
        )

        self._update_overdrive_button(
            enabled
        )

    def _update_overdrive_button(
        self,
        enabled: bool,
    ) -> None:
        desired_text = (
            "OVERDRIVE ON"
            if enabled
            else "OVERDRIVE BYPASS"
        )

        if (
            self.overdrive_button.isChecked() == enabled
            and self.overdrive_button.text()
            == desired_text
        ):
            return

        self.overdrive_button.blockSignals(True)
        self.overdrive_button.setChecked(
            enabled
        )
        self.overdrive_button.setText(
            desired_text
        )
        self.overdrive_button.blockSignals(False)

    @Slot(int)
    def overdrive_drive_changed(
        self,
        value: int,
    ) -> None:
        self.runtime.set_overdrive_drive_db(
            float(value)
        )

        self.overdrive_drive_value.setText(
            f"{value} dB"
        )

    def _update_overdrive_drive(
        self,
        drive_db: float,
    ) -> None:
        value = round(drive_db)

        if (
            self.overdrive_drive_slider.value()
            == value
        ):
            return

        self.overdrive_drive_slider.blockSignals(
            True
        )
        self.overdrive_drive_slider.setValue(
            value
        )
        self.overdrive_drive_slider.blockSignals(
            False
        )

        self.overdrive_drive_value.setText(
            f"{value} dB"
        )

    @Slot()
    def refresh_metrics(self) -> None:
        snapshot = self.runtime.snapshot()

        self._update_status(snapshot)
        self._update_hpf_button(
            snapshot.high_pass_enabled
        )
        self._update_overdrive_button(
            snapshot.overdrive_enabled
        )
        self._update_overdrive_drive(
            snapshot.overdrive_drive_db
        )

        self.start_button.setEnabled(
            not snapshot.running
        )
        self.stop_button.setEnabled(
            snapshot.running
        )

        if not self._di_save_pending:
            self.record_button.setEnabled(
                snapshot.running
            )

        if snapshot.total_latency_ms is None:
            self.latency_value.setText("--")
        else:
            self.latency_value.setText(
                f"{snapshot.total_latency_ms:.2f} ms"
            )


        input_db = max(
            -60.0,
            min(0.0, snapshot.input_peak_dbfs),
        )
        output_db = max(
            -60.0,
            min(0.0, snapshot.output_peak_dbfs),
        )

        self.input_meter.setValue(
            round((input_db + 60.0) * 10.0)
        )
        self.output_meter.setValue(
            round((output_db + 60.0) * 10.0)
        )

        self.input_meter_value.setText(
            f"{snapshot.input_peak_dbfs:.1f} dBFS"
        )
        self.output_meter_value.setText(
            f"{snapshot.output_peak_dbfs:.1f} dBFS"
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
                f"{snapshot.callback_error_count} | "
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
