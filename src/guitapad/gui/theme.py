"""GuitaPaD Qt stylesheet."""

APP_STYLESHEET = """
QWidget {
    background-color: #101318;
    color: #f1f3f5;
    font-family: "Segoe UI";
    font-size: 14px;
}

QMainWindow {
    background-color: #101318;
}

QFrame#card {
    background-color: #191e26;
    border: 1px solid #2b3340;
    border-radius: 16px;
}

QLabel#title {
    font-size: 34px;
    font-weight: 800;
    color: #f5a623;
}

QLabel#subtitle {
    color: #939dab;
    font-size: 14px;
}

QLabel#sectionTitle {
    color: #aab2bd;
    font-size: 12px;
    font-weight: 700;
}

QLabel#bigValue {
    color: #ffffff;
    font-size: 27px;
    font-weight: 700;
}

QLabel#metricValue {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
}

QLabel#metricName {
    color: #8e99a8;
    font-size: 12px;
}

QLabel#signalBlock {
    background-color: #242b35;
    border: 1px solid #353e4b;
    border-radius: 10px;
    padding: 12px 18px;
    font-weight: 700;
}

QPushButton {
    min-height: 42px;
    border-radius: 10px;
    padding-left: 20px;
    padding-right: 20px;
    font-weight: 700;
}

QPushButton#startButton {
    background-color: #f5a623;
    color: #121417;
    border: none;
}

QPushButton#startButton:hover {
    background-color: #ffb83d;
}

QPushButton#stopButton {
    background-color: #292f38;
    color: #e9ecef;
    border: 1px solid #404956;
}

QPushButton#stopButton:hover {
    background-color: #343c47;
}


QPushButton#hpfButton {
    background-color: #252b33;
    color: #9da7b4;
    border: 1px solid #3b444f;
}

QPushButton#hpfButton:checked {
    background-color: #173b2c;
    color: #62d69b;
    border: 1px solid #286848;
}

QPushButton#hpfButton:hover {
    border: 1px solid #66717f;
}


QPushButton#overdriveButton {
    background-color: #252b33;
    color: #9da7b4;
    border: 1px solid #3b444f;
}

QPushButton#overdriveButton:checked {
    background-color: #553113;
    color: #ffb85c;
    border: 1px solid #9a5b20;
}

QPushButton#overdriveButton:hover {
    border: 1px solid #8b96a5;
}

QPushButton:disabled {
    background-color: #20252c;
    color: #606a77;
    border: 1px solid #2c333d;
}

QSlider::groove:horizontal {
    height: 8px;
    background-color: #2b323d;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background-color: #f5a623;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    width: 22px;
    margin: -7px 0;
    background-color: #ffffff;
    border: 3px solid #f5a623;
    border-radius: 11px;
}

QProgressBar {
    background-color: #272e38;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #f5a623;
    border-radius: 6px;
}

QProgressBar#inputMeter::chunk {
    background-color: #47c98b;
}

QProgressBar#outputMeter::chunk {
    background-color: #f5a623;
}
"""
