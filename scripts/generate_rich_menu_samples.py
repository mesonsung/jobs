#!/usr/bin/env python3

"""
生成 LINE Rich Menu 範例圖片

此腳本會生成兩種 Rich Menu 的範例圖片：
1. 已註冊用戶 Rich Menu (2500 x 1686)
2. 未註冊用戶 Rich Menu (2500 x 1686)
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("錯誤：需要安裝 Pillow 套件")
    print("請執行: pip install Pillow")
    sys.exit(1)


# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def draw_multiline_text_centered(draw, text: str, position: tuple, font, fill: str, line_spacing: int = 10):
    """
    繪製多行置中文字
    
    參數:
        draw: ImageDraw 物件
        text: 要繪製的文字（可包含換行符 \n）
        position: 文字中心位置 (x, y)
        font: 字體物件
        fill: 文字顏色
        line_spacing: 行間距
    """
    lines = text.split('\n')
    if not lines:
        return
    
    # 計算總高度
    line_heights = []
    for line in lines:
        if line.strip():  # 忽略空行
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        else:
            line_heights.append(0)
    
    total_height = sum(line_heights) + (len([h for h in line_heights if h > 0]) - 1) * line_spacing
    
    # 從中心位置開始向上繪製
    current_y = position[1] - total_height // 2
    
    for i, line in enumerate(lines):
        if not line.strip():
            current_y += line_spacing
            continue
        
        # 計算這行的寬度並置中
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        
        # 繪製這行文字（置中）
        draw.text(
            (position[0] - line_width // 2, current_y),
            line,
            fill=fill,
            font=font
        )
        
        current_y += line_height + line_spacing


def create_registered_user_menu(output_path: str = "rich_menu_registered.jpg"):
    """建立已註冊用戶的 Rich Menu 範例圖片"""
    width, height = 2500, 843
    
    # 建立圖片
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # 定義顏色
    bg_color = '#4A90E2'  # 藍色背景
    header_color = '#2C5F8D'  # 深藍色標題區
    area1_color = '#E8F4F8'  # 淺藍色區域1
    area2_color = '#F0F8E8'  # 淺綠色區域2
    area3_color = '#FFF8E8'  # 淺黃色區域3
    text_color = '#333333'
    header_text_color = '#FFFFFF'
    
    # 繪製背景
    draw.rectangle([(0, 0), (width, height)], fill=bg_color)
    
    # 繪製標題區
    draw.rectangle([(0, 0), (width, 200)], fill=header_color)
    
    # 繪製三個功能區域
    # 區域1: 檢視註冊資料 (0-833)
    draw.rectangle([(0, 200), (833, height)], fill=area1_color)
    draw.rectangle([(0, 200), (833, height)], outline='#CCCCCC', width=3)
    
    # 區域2: 可報班工作 (833-1666)
    draw.rectangle([(833, 200), (1666, height)], fill=area2_color)
    draw.rectangle([(833, 200), (1666, height)], outline='#CCCCCC', width=3)
    
    # 區域3: 已報班記錄 (1666-2500)
    draw.rectangle([(1666, 200), (width, height)], fill=area3_color)
    draw.rectangle([(1666, 200), (width, height)], outline='#CCCCCC', width=3)
    
    # 嘗試載入支援中文的字體
    title_font = None
    text_font = None
    
    # 常見的中文字體路徑列表（優先使用系統已安裝的字體）
    chinese_font_paths = [
        # Linux 系統常見中文字體（優先使用 opentype 目錄下的字體）
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        # macOS 系統常見中文字體
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Microsoft/SimHei.ttf",
        # Windows 系統常見中文字體（如果在 WSL 中）
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "/mnt/c/Windows/Fonts/simsun.ttc",
    ]
    
    # 嘗試載入中文字體
    for font_path in chinese_font_paths:
        try:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, int(80 * 1.2))  # 放大 1.2 倍: 96
                text_font = ImageFont.truetype(font_path, int(60 * 2))  # 放大 2.4 倍: 144
                print(f"使用字體: {font_path}")
                break
        except Exception as e:
            continue
    
    # 如果找不到中文字體，嘗試使用系統預設字體
    if title_font is None:
        try:
            # 嘗試使用系統字體
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(80 * 1.2))
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(60 * 2))
        except:
            try:
                # 嘗試使用其他常見字體
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(80 * 1.2))
                text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(60 * 2))
            except:
                # 使用預設字體（可能無法顯示中文）
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                print("警告：使用預設字體，可能無法正確顯示中文")
    
    # 繪製標題文字（垂直置中）
    title = "已註冊用戶"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    # 標題區中心 Y 座標
    header_center_y = 200 / 2
    # 文字中心相對於 bbox top 的偏移
    text_center_offset = (title_bbox[3] + title_bbox[1]) / 2
    # 計算垂直置中的 Y 位置
    title_y = header_center_y - text_center_offset
    draw.text(
        ((width - title_width) // 2, title_y),
        title,
        fill=header_text_color,
        font=title_font
    )
    
    # 繪製區域文字（使用多行置中繪製）
    center_y = (height - 200) // 2 + 200  # 區域中心 Y 座標
    
    # 區域1: 檢視註冊資料
    text1 = "檢視\n報班帳號"
    center_x1 = 833 // 2  # 區域1的中心 X 座標
    draw_multiline_text_centered(draw, text1, (center_x1, center_y), text_font, text_color, line_spacing=15)
    
    # 區域2: 可報班工作
    text2 = "我想找工作"
    center_x2 = 833 + 833 // 2  # 區域2的中心 X 座標
    draw_multiline_text_centered(draw, text2, (center_x2, center_y), text_font, text_color, line_spacing=15)
    
    # 區域3: 已報班記錄
    text3 = "我的報班"
    center_x3 = 1666 + 834 // 2  # 區域3的中心 X 座標
    draw_multiline_text_centered(draw, text3, (center_x3, center_y), text_font, text_color, line_spacing=15)
    
    # 儲存圖片
    img.save(output_path, 'JPEG', quality=95)
    print(f"✅ 已生成已註冊用戶 Rich Menu: {output_path}")
    return output_path


def create_unregistered_user_menu(output_path: str = "rich_menu_unregistered.jpg"):
    """建立未註冊用戶的 Rich Menu 範例圖片"""
    width, height = 2500, 843
    
    # 建立圖片
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # 定義顏色
    bg_color = '#FF6B6B'  # 紅色背景
    header_color = '#C92A2A'  # 深紅色標題區
    area1_color = '#FFE8E8'  # 淺紅色區域1
    area2_color = '#E8F4F8'  # 淺藍色區域2
    text_color = '#333333'
    header_text_color = '#FFFFFF'
    
    # 繪製背景
    draw.rectangle([(0, 0), (width, height)], fill=bg_color)
    
    # 繪製標題區
    draw.rectangle([(0, 0), (width, 200)], fill=header_color)
    
    # 繪製兩個功能區域
    # 區域1: 註冊功能 (0-1250)
    draw.rectangle([(0, 200), (1250, height)], fill=area1_color)
    draw.rectangle([(0, 200), (1250, height)], outline='#CCCCCC', width=3)
    
    # 區域2: 可報班工作 (1250-2500)
    draw.rectangle([(1250, 200), (width, height)], fill=area2_color)
    draw.rectangle([(1250, 200), (width, height)], outline='#CCCCCC', width=3)
    
    # 嘗試載入支援中文的字體
    title_font = None
    text_font = None
    
    # 常見的中文字體路徑列表（優先使用系統已安裝的字體）
    chinese_font_paths = [
        # Linux 系統常見中文字體（優先使用 opentype 目錄下的字體）
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        # macOS 系統常見中文字體
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Microsoft/SimHei.ttf",
        # Windows 系統常見中文字體（如果在 WSL 中）
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "/mnt/c/Windows/Fonts/simsun.ttc",
    ]
    
    # 嘗試載入中文字體
    for font_path in chinese_font_paths:
        try:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, int(80 * 1.2))  # 放大 1.2 倍: 96
                text_font = ImageFont.truetype(font_path, int(60 * 2))  # 放大 2.4 倍: 144
                print(f"使用字體: {font_path}")
                break
        except Exception as e:
            continue
    
    # 如果找不到中文字體，嘗試使用系統預設字體
    if title_font is None:
        try:
            # 嘗試使用系統字體
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(80 * 1.2))
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(60 * 2))
        except:
            try:
                # 嘗試使用其他常見字體
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(80 * 1.2))
                text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(60 * 2))
            except:
                # 使用預設字體（可能無法顯示中文）
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                print("警告：使用預設字體，可能無法正確顯示中文")
    
    # 繪製標題文字（垂直置中）
    title = "未註冊用戶"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    # 標題區中心 Y 座標
    header_center_y = 200 / 2
    # 文字中心相對於 bbox top 的偏移
    text_center_offset = (title_bbox[3] + title_bbox[1]) / 2
    # 計算垂直置中的 Y 位置
    title_y = header_center_y - text_center_offset
    draw.text(
        ((width - title_width) // 2, title_y),
        title,
        fill=header_text_color,
        font=title_font
    )
    
    # 繪製區域文字（使用多行置中繪製）
    center_y = (height - 200) // 2 + 200  # 區域中心 Y 座標
    
    # 區域1: 註冊功能
    text1 = "註冊\n報班帳號"
    center_x1 = 1250 // 2  # 區域1的中心 X 座標
    draw_multiline_text_centered(draw, text1, (center_x1, center_y), text_font, text_color, line_spacing=15)
    
    # 區域2: 可報班工作
    text2 = "可報班\n工作"
    center_x2 = 1250 + 1250 // 2  # 區域2的中心 X 座標
    draw_multiline_text_centered(draw, text2, (center_x2, center_y), text_font, text_color, line_spacing=15)
    
    # 儲存圖片
    img.save(output_path, 'JPEG', quality=95)
    print(f"✅ 已生成未註冊用戶 Rich Menu: {output_path}")
    return output_path


def main():
    """主函數"""
    print("開始生成 Rich Menu 範例圖片...")
    print("=" * 50)
    
    # 建立輸出目錄
    output_dir = "rich_menu_samples"
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成已註冊用戶的 Rich Menu
    registered_path = os.path.join(output_dir, "rich_menu_registered.jpg")
    create_registered_user_menu(registered_path)
    
    # 生成未註冊用戶的 Rich Menu
    unregistered_path = os.path.join(output_dir, "rich_menu_unregistered.jpg")
    create_unregistered_user_menu(unregistered_path)
    
    print("=" * 50)
    print("✅ 所有 Rich Menu 範例圖片已生成完成！")
    print(f"📁 輸出目錄: {output_dir}/")
    print(f"   - {registered_path}")
    print(f"   - {unregistered_path}")


if __name__ == "__main__":
    main()
