# Image_Factory
Convenient photo editing tools

## 如何使用
### 1. 安裝環境(Windows/Linux)
```bash
conda env create -f environment.yaml
```
### 2. 啟用圖形介面
```bash
python main.py
```

## 專案結構
ImageFactory/
├── main.py                  # 啟動主程式
├── presets/                 # 儲存使用者流程設定
│   └── my_workflow.json
├── environment.yaml         # Conda 環境設定
├── input/                   # 預設載入圖片目錄
├── output/                  # 處理後圖片儲存目錄
└── imgtools/                # 圖片工具模組
    ├── __init__.py
    ├── gui.py               # GUI 操作邏輯
    └── utils.py             # 處理函式（壓縮、旋轉、編碼）

## 待改進
因為當前功能有點多，未來可能會新增更多功能
