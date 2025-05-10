import os
import io
import json
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageChops

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QCheckBox, QSpinBox, QSlider, QGroupBox, QListWidget,
    QListWidgetItem, QTextEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


def compress_image_to_size(img: Image.Image, target_size_mb: int) -> Image.Image | None:
    target_size = target_size_mb * 1024 * 1024
    quality = 95
    width, height = img.size
    scale_factor = 0.95
    for _ in range(30):
        buffer = io.BytesIO()
        temp_img = img.resize((int(width), int(height)), Image.Resampling.LANCZOS)
        temp_img.convert("RGB").save(buffer, format="JPEG", quality=quality)
        if buffer.tell() <= target_size:
            buffer.seek(0)
            return Image.open(buffer)
        quality -= 5
        width *= scale_factor
        height *= scale_factor
        if quality < 20:
            scale_factor -= 0.05
    return None


def create_rotated_frame(original: Image.Image, angle: float, crop: bool) -> Image.Image:
    canvas_size = original.size
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    rotated = original.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    if crop:
        bg = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
        diff = ImageChops.difference(rotated, bg)
        bbox = diff.getbbox()
        if bbox:
            rotated = rotated.crop(bbox)
    x = (canvas_size[0] - rotated.size[0]) // 2
    y = (canvas_size[1] - rotated.size[1]) // 2
    canvas.paste(rotated, (x, y), rotated)
    return canvas


def encode_image_to_base64(img: Image.Image) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class ImageFactory(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Factory")
        self.setGeometry(100, 100, 1000, 600)
        self.setAcceptDrops(True)
        self.original_image = None
        self.image_path = ""
        os.makedirs("presets", exist_ok=True)
        os.makedirs("output", exist_ok=True)
        os.makedirs("input", exist_ok=True)
        self.init_ui()
        self.load_my_workflow()

    def init_ui(self):
        layout = QHBoxLayout()

        # 左側圖片顯示區
        left_layout = QVBoxLayout()
        self.original_label = QLabel("原圖")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label = QLabel("預覽")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(400, 300)
        self.preview_label.setScaledContents(True)
        left_layout.addWidget(self.original_label)
        left_layout.addWidget(self.preview_label)
        layout.addLayout(left_layout, 2)

        # 右側控制區
        right_layout = QVBoxLayout()
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        right_layout.addWidget(self.message_log)
        
        from PyQt6.QtWidgets import QStackedLayout, QWidget

        # === 功能選單（左邊選單 + 右邊功能設定） ===
        self.feature_switch = QListWidget()
        self.feature_switch.setFixedHeight(80)
        self.feature_switch.addItems(["旋轉設定", "壓縮設定", "匯出設定"])
        self.feature_switch.currentRowChanged.connect(self.switch_feature_panel)
        right_layout.addWidget(QLabel("功能設定選單"))
        right_layout.addWidget(self.feature_switch)

        # 建立功能區堆疊容器
        self.feature_stack = QStackedLayout()
        feature_container = QWidget()
        feature_container.setLayout(self.feature_stack)
        right_layout.addWidget(feature_container)

        # === 旋轉功能區 ===
        rotate_box = QGroupBox("旋轉設定")
        rotate_layout = QVBoxLayout()
        self.rotate_checkbox = QCheckBox("啟用旋轉")
        rotate_layout.addWidget(self.rotate_checkbox)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("幀數："))
        self.rotate_spin = QSpinBox()
        self.rotate_spin.setRange(10, 360)
        self.rotate_spin.setValue(36)
        h1.addWidget(self.rotate_spin)
        rotate_layout.addLayout(h1)

        self.rotate_bar = QSlider(Qt.Orientation.Horizontal)
        self.rotate_bar.setRange(10, 360)
        self.rotate_bar.setValue(36)
        self.rotate_bar.valueChanged.connect(self.rotate_spin.setValue)
        self.rotate_spin.valueChanged.connect(self.rotate_bar.setValue)
        rotate_layout.addWidget(self.rotate_bar)

        self.crop_checkbox = QCheckBox("去黑邊")
        rotate_layout.addWidget(self.crop_checkbox)
        rotate_box.setLayout(rotate_layout)
        self.feature_stack.addWidget(rotate_box)

        # === 壓縮功能區 ===
        compress_box = QGroupBox("壓縮設定")
        compress_layout = QVBoxLayout()
        self.compress_checkbox = QCheckBox("啟用壓縮")
        compress_layout.addWidget(self.compress_checkbox)
        self.file_size_label = QLabel("目前圖片大小：--")
        compress_layout.addWidget(self.file_size_label)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("目標大小(MB)："))
        self.compress_spin = QSpinBox()
        self.compress_spin.setRange(1, 100)
        self.compress_spin.setValue(10)
        h2.addWidget(self.compress_spin)
        compress_layout.addLayout(h2)

        self.compress_bar = QSlider(Qt.Orientation.Horizontal)
        self.compress_bar.setRange(1, 100)
        self.compress_bar.setValue(10)
        self.compress_bar.valueChanged.connect(self.compress_spin.setValue)
        self.compress_spin.valueChanged.connect(self.compress_bar.setValue)
        compress_layout.addWidget(self.compress_bar)
        compress_box.setLayout(compress_layout)
        self.feature_stack.addWidget(compress_box)
        
        # 匯出 Base64 設定區（新增）
        export_box = QGroupBox("匯出設定")
        export_layout = QVBoxLayout()
        self.export_checkbox = QCheckBox("啟用匯出 Base64")
        export_layout.addWidget(self.export_checkbox)
        export_box.setLayout(export_layout)
        self.feature_stack.addWidget(export_box)

        # === 自定流程區（無勾選，只排序） ===
        pipeline_box = QGroupBox("自定流程順序（僅排序，實際執行由上方設定）")
        pipeline_layout = QVBoxLayout()

        self.pipeline_list = QListWidget()
        for step in ["旋轉", "壓縮", "匯出 Base64"]:
            self.pipeline_list.addItem(QListWidgetItem(step))
        self.pipeline_list.setFixedHeight(100)
        pipeline_layout.addWidget(self.pipeline_list)

        btn_move = QHBoxLayout()
        btn_up = QPushButton("↑")
        btn_up.clicked.connect(self.move_step_up)
        btn_down = QPushButton("↓")
        btn_down.clicked.connect(self.move_step_down)
        btn_move.addWidget(btn_up)
        btn_move.addWidget(btn_down)
        pipeline_layout.addLayout(btn_move)

        btn_save = QPushButton("儲存流程（my_workflow.json）")
        btn_save.clicked.connect(self.save_pipeline_to_json)
        pipeline_layout.addWidget(btn_save)

        self.run_pipeline_button = QPushButton("執行流程")
        self.run_pipeline_button.clicked.connect(self.run_pipeline)
        pipeline_layout.addWidget(self.run_pipeline_button)

        pipeline_box.setLayout(pipeline_layout)
        right_layout.addWidget(pipeline_box)

        # 檔案操作
        file_btns = QHBoxLayout()
        btn_load = QPushButton("載入圖片")
        btn_load.clicked.connect(self.load_image)
        btn_save = QPushButton("儲存圖片")
        btn_save.clicked.connect(self.save_image)
        file_btns.addWidget(btn_load)
        file_btns.addWidget(btn_save)
        right_layout.addLayout(file_btns)

        layout.addLayout(right_layout, 1)
        self.setLayout(layout)

    def log(self, msg):
        self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "選擇圖片", "input", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            self.image_path = file_name
            self.original_image = Image.open(file_name).convert("RGBA")
            pixmap = QPixmap(file_name).scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio)
            self.original_label.setPixmap(pixmap)
            self.preview_label.clear()
            self.log(f"✅ 已載入：{os.path.basename(file_name)}")
            
            size_bytes = os.path.getsize(file_name)
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                size_str = f"{size_bytes / 1024:.1f} KB"
            self.file_size_label.setText(f"目前圖片大小：{size_str}")

    def get_pipeline_order(self):
        return [self.pipeline_list.item(i).text() for i in range(self.pipeline_list.count())]

    def switch_feature_panel(self, index):
        self.feature_stack.setCurrentIndex(index)

    def run_pipeline(self):
        if not self.original_image:
            self.log("❌ 尚未載入圖片")
            return

        steps = self.get_pipeline_order()
        self.log(f"🚀 執行流程順序：{' > '.join(steps)}")

        enabled_map = {
            "旋轉": self.rotate_checkbox.isChecked(),
            "壓縮": self.compress_checkbox.isChecked(),
            "匯出 Base64": self.export_checkbox.isChecked()
        }

        img = self.original_image.copy().convert("RGBA")
        frames = []

        for step in steps:
            if not enabled_map.get(step, False):
                self.log(f"⏭ 跳過未啟用功能：{step}")
                continue
            if step == "旋轉":
                frame_count = self.rotate_spin.value()
                for i in range(frame_count):
                    angle = (360 / frame_count) * i
                    frame = create_rotated_frame(img, angle, self.crop_checkbox.isChecked())
                    frames.append(frame)
            elif step == "壓縮":
                if frames:
                    compressed_frames = []
                    for f in frames:
                        c = compress_image_to_size(f.convert("RGB"), self.compress_spin.value())
                        if c:
                            compressed_frames.append(c.convert("RGBA"))
                    frames = compressed_frames
                else:
                    img = compress_image_to_size(img.convert("RGB"), self.compress_spin.value())
            elif step == "匯出 Base64":
                encoded = encode_image_to_base64(img.convert("RGB"))
                name = os.path.splitext(os.path.basename(self.image_path))[0] + "_base64.json"
                with open(f"presets/{name}", "w", encoding="utf-8") as f:
                    json.dump({"key": encoded}, f)
                self.log(f"✅ 匯出：{name}")

        # 預覽處理
        if self.rotate_checkbox.isChecked():
            gif_path = "presets/temp_output.gif"
            if os.path.exists(gif_path):
                # 🧼 停止 QMovie 並釋放檔案
                if self.preview_label.movie():
                    self.preview_label.movie().stop()
                    self.preview_label.clear()
                os.remove(gif_path)
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=100,
                loop=0,
                disposal=2
            )
            from PyQt6.QtGui import QMovie
            movie = QMovie(gif_path)
            self.preview_label.setMovie(movie)
            movie.start()
            self.log("🌀 已產生旋轉動畫預覽（GIF）")
        else:
            temp_path = "presets/temp_output.jpg"
            if os.path.exists(temp_path):
                os.remove(temp_path)
            img.convert("RGB").save(temp_path, format="JPEG")
            self.preview_label.setPixmap(QPixmap(temp_path))
            self.log("🖼️ 已更新圖片預覽")

    def save_image(self):
        gif_path = "presets/temp_output.gif"
        jpg_path = "presets/temp_output.jpg"

        # 根據檔案存在性判斷是 GIF 或 JPG 預覽
        if os.path.exists(gif_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"processed_{timestamp}.gif"
            path, _ = QFileDialog.getSaveFileName(self, "儲存動畫", f"output/{default_filename}", "GIF (*.gif)")
            if path:
                from PIL import Image
                frames = []
                with Image.open(gif_path) as img:
                    try:
                        while True:
                            frames.append(img.copy())
                            img.seek(len(frames))  # 下一幀
                    except EOFError:
                        pass

                if frames:
                    frames[0].save(
                        path,
                        save_all=True,
                        append_images=frames[1:],
                        duration=100,
                        loop=0,
                        disposal=2
                    )
                    self.log(f"✅ 已儲存 GIF 圖片：{os.path.basename(path)}")
                else:
                    self.log("❌ 無有效幀數可儲存")
            return

        elif os.path.exists(jpg_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"processed_{timestamp}.jpg"
            path, _ = QFileDialog.getSaveFileName(self, "儲存圖片", f"output/{default_filename}", "JPEG (*.jpg)")
            if path:
                Image.open(jpg_path).convert("RGB").save(path, format="JPEG")
                self.log(f"✅ 已儲存圖片：{os.path.basename(path)}")
            return

        else:
            self.log("❌ 尚未執行流程，無可儲存之圖片")

    def move_step_up(self):
        row = self.pipeline_list.currentRow()
        if row > 0:
            item = self.pipeline_list.takeItem(row)
            self.pipeline_list.insertItem(row - 1, item)
            self.pipeline_list.setCurrentRow(row - 1)

    def move_step_down(self):
        row = self.pipeline_list.currentRow()
        if row < self.pipeline_list.count() - 1:
            item = self.pipeline_list.takeItem(row)
            self.pipeline_list.insertItem(row + 1, item)
            self.pipeline_list.setCurrentRow(row + 1)

    def save_pipeline_to_json(self):
        steps = self.get_pipeline_order()
        path = "presets/my_workflow.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(steps, f, ensure_ascii=False, indent=2)
        self.log(f"已儲存流程設定到：{path}")


    def load_pipeline_from_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "載入流程設定", "presets", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                steps = json.load(f)
            self.pipeline_list.clear()
            for s in steps:
                self.pipeline_list.addItem(QListWidgetItem(s))
            self.log(f"已載入流程設定：{os.path.basename(path)}")
    
    def load_my_workflow(self):
        path = "presets/my_workflow.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    steps = json.load(f)
                self.pipeline_list.clear()
                for s in steps:
                    self.pipeline_list.addItem(QListWidgetItem(s))
                self.log("📂 已自動載入 my_workflow.json")
            except Exception as e:
                self.log(f"⚠️ 載入流程設定失敗：{e}")
    
    def closeEvent(self, event):
        for temp_path in ["presets/temp_output.jpg", "presets/temp_output.gif"]:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    self.log(f"🧹 已清除暫存檔：{os.path.basename(temp_path)}")
                except Exception as e:
                    self.log(f"⚠️ 清除暫存圖失敗：{e}")
        event.accept()
            
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = ImageFactory()
    window.show()
    sys.exit(app.exec())
