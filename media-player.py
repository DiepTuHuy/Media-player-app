import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QSlider, QHBoxLayout, QSizePolicy, QSpacerItem, QMenu
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QSize, QTime
from PyQt6.QtGui import QAction, QIcon

def resource_path(relative_path):
    """ Hàm lấy đường dẫn chính xác khi chạy file .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MinimalistVideoPlayer(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.setWindowTitle("Minimalist MP4 Player")
        
        # --- THÊM ICON ---
        self.setWindowIcon(QIcon(resource_path("app_icon.ico")))
        
        self.setGeometry(100, 100, 800, 450)
        self.is_looping = False 
        self.is_pinned = False # Trạng thái ghim
        self.old_pos = None
        self.video_ratio = 16/9

        self.init_ui()
        self.init_media_player()
        
        if initial_file:
            self.load_video(initial_file)
    
    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)        
        self.video_widget.mousePressEvent = self.handle_video_click 
        self.main_layout.addWidget(self.video_widget)

        # Action: Loop
        self.loop_action = QAction("Lặp lại (Loop)", self)
        self.loop_action.setCheckable(True)
        self.loop_action.triggered.connect(self.toggle_loop)

        # Action: Pin (Ghim)
        self.pin_action = QAction("Ghim lên trên (Always on Top)", self)
        self.pin_action.setCheckable(True)
        self.pin_action.triggered.connect(self.toggle_pin)

        self.controls_overlay = QWidget(self.central_widget)
        self.controls_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 8px;")
        self.controls_overlay_layout = QVBoxLayout(self.controls_overlay)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.setStyleSheet("QSlider::groove:horizontal { height: 4px; background: #555; } QSlider::handle:horizontal { background: #fff; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::sub-page:horizontal { background: #007ACC; }")
        self.controls_overlay_layout.addWidget(self.position_slider)

        self.buttons_layout = QHBoxLayout()
        self.time_label = QPushButton("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white; border: none;")
        self.buttons_layout.addWidget(self.time_label)

        self.buttons_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.loop_button = QPushButton("Loop: OFF")
        self.loop_button.setFixedSize(80, 30)
        self.loop_button.setStyleSheet("color: #aaa; background: rgba(255,255,255,0.1); border-radius: 5px; font-weight: bold;")
        self.loop_button.clicked.connect(self.toggle_loop)
        self.buttons_layout.addWidget(self.loop_button)

        self.controls_overlay_layout.addLayout(self.buttons_layout)
        
        # Thiết lập Window Flags ban đầu
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.central_widget.setStyleSheet("background-color: black; border-radius: 10px;")
        self.controls_overlay.hide()

    def show_custom_context_menu(self, global_pos):
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu { background-color: #222; color: white; border: 1px solid #555; padding: 5px; }
            QMenu::item { padding: 5px 25px 5px 20px; }
            QMenu::item:selected { background-color: #007ACC; }
        """)        
        
        self.loop_action.setChecked(self.is_looping)
        context_menu.addAction(self.loop_action)
        
        # Thêm mục Ghim vào Menu
        self.pin_action.setChecked(self.is_pinned)
        context_menu.addAction(self.pin_action)
        
        context_menu.addSeparator()
        quit_action = context_menu.addAction("Thoát (Esc)")
        quit_action.triggered.connect(self.close)
        
        context_menu.exec(global_pos)

    def toggle_pin(self):
        """ Xử lý bật/tắt ghim cửa sổ """
        self.is_pinned = self.pin_action.isChecked()
        flags = self.windowFlags()
        if self.is_pinned:
            # Thêm flag ghim
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            # Bỏ flag ghim
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show() # Cần gọi lại show() để cập nhật flag

    def init_media_player(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)

    def load_video(self, filename):
        if filename:
            filename = filename.strip('"')
            if os.path.exists(filename):
                self.media_player.setSource(QUrl.fromLocalFile(os.path.abspath(filename)))
                self.media_player.play()

    def media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            size = self.video_widget.sizeHint()
            if size.isValid():
                self.video_ratio = size.width() / size.height()
                self.resize(size) 
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.is_looping:
            self.media_player.setPosition(0)
            self.media_player.play()

    def toggle_loop(self):
        if self.sender() == self.loop_button:
            self.is_looping = not self.is_looping
            self.loop_action.setChecked(self.is_looping)
        else:
            self.is_looping = self.loop_action.isChecked()

        status = "ON" if self.is_looping else "OFF"
        color = "#007ACC" if self.is_looping else "rgba(255,255,255,0.1)"
        self.loop_button.setText(f"Loop: {status}")
        self.loop_button.setStyleSheet(f"color: white; background: {color}; border-radius: 5px; font-weight: bold;")

    def wheelEvent(self, event):
        scale = 1.1 if event.angleDelta().y() > 0 else 0.9
        nw = int(self.width() * scale)
        if 200 < nw < 2560: self.resize(nw, int(nw / self.video_ratio))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.media_player.pause()
            else: self.media_player.play()
        elif event.key() == Qt.Key.Key_Right: self.media_player.setPosition(self.media_player.position() + 5000)
        elif event.key() == Qt.Key.Key_Left: self.media_player.setPosition(self.media_player.position() - 5000)
        elif event.key() == Qt.Key.Key_Escape: self.close()

    def handle_video_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton: 
            self.old_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_custom_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            
    def mouseReleaseEvent(self, event): 
        self.old_pos = None
        
    def enterEvent(self, event): self.controls_overlay.show()
    def leaveEvent(self, event): self.controls_overlay.hide()
    def resizeEvent(self, event): self.controls_overlay.setGeometry(10, self.height() - 80, self.width() - 20, 70)
    
    def position_changed(self, p):
        self.position_slider.setValue(p)
        curr = QTime(0,0).addMSecs(p).toString("mm:ss")
        total = QTime(0,0).addMSecs(self.media_player.duration()).toString("mm:ss")
        self.time_label.setText(f"{curr} / {total}")
        
    def duration_changed(self, d): self.position_slider.setRange(0, d)
    def set_position(self, p): self.media_player.setPosition(p)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_to_open = sys.argv[1] if len(sys.argv) > 1 else None
    player = MinimalistVideoPlayer(file_to_open)
    player.show()
    sys.exit(app.exec())