#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
华为备忘录提取工具 / Huawei Notepad Extractor

批量提取华为手机备忘录内容的Python脚本
A Python script for batch extracting Huawei phone notepad content

作者 / Authors: Jessica & Claude
许可 / License: MIT License
仓库 / Repository: https://github.com/yourusername/huawei-notepad-extractor

⚠️  重要提示 / IMPORTANT NOTICE:
本工具仅供个人学习和备份使用，严禁商业用途！
This tool is for personal learning and backup only. Commercial use is strictly prohibited!

任何转售、商业使用或以盈利为目的的再分发都违反许可条款。
Any resale, commercial use, or redistribution for profit violates the license terms.
"""

import subprocess
import re
import time

def adb(cmd):
    result = subprocess.run(f'adb shell {cmd}', shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def tap(x, y):
    adb(f'input tap {x} {y}')
    time.sleep(0.6)

def back():
    adb('input keyevent KEYCODE_BACK')
    time.sleep(0.6)

def swipe_one_item():
    """向上滑动整整一条备忘录的距离"""
    adb('input swipe 350 750 350 550 200')
    time.sleep(0.8)

def get_note_content():
    """获取当前详情页的备忘录内容"""
    adb('uiautomator dump /sdcard/window_dump.xml')
    subprocess.run('adb pull /sdcard/window_dump.xml .', shell=True, 
                   capture_output=True)
    
    with open('window_dump.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # 先找到包含 notetext_textview 的整个 node 标签
    node_match = re.search(r'<node[^>]*resource-id="com\.huawei\.notepad:id/notetext_textview"[^>]*>', xml_content)
    
    if node_match:
        node = node_match.group(0)
        # 从这个node里提取text属性（可能是单引号或双引号）
        text_match = re.search(r"text='([^']*)'", node)
        if not text_match:
            text_match = re.search(r'text="([^"]*)"', node)
        
        if text_match:
            content = text_match.group(1)
            # 解码HTML实体（如 &#10; 是换行符）
            import html
            content = html.unescape(content)
            return content
    
    return None

def get_note_title():
    """获取备忘录标题"""
    adb('uiautomator dump /sdcard/window_dump.xml')
    subprocess.run('adb pull /sdcard/window_dump.xml .', shell=True,
                   capture_output=True)
    
    with open('window_dump.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # 先找到包含 title 的整个 node 标签
    node_match = re.search(r'<node[^>]*resource-id="com\.huawei\.notepad:id/title"[^>]*>', xml_content)
    
    title = "未知"
    if node_match:
        node = node_match.group(0)
        # 从这个node里提取text属性
        text_match = re.search(r"text='([^']*)'", node)
        if not text_match:
            text_match = re.search(r'text="([^"]*)"', node)
        
        if text_match:
            import html
            title = html.unescape(text_match.group(1))
    
    # 提取时间戳
    timestamp_match = re.search(r'<node[^>]*resource-id="com\.huawei\.notepad:id/notecontent_date_text"[^>]*>', xml_content)
    if timestamp_match:
        node = timestamp_match.group(0)
        text_match = re.search(r'text="([^"]*)"', node)
        if not text_match:
            text_match = re.search(r"text='([^']*)'", node)
        
        if text_match:
            import html
            timestamp = html.unescape(text_match.group(1))
            return f"{title} - {timestamp}"
    
    return title

def get_folder_name():
    """获取当前备忘录文件夹名称"""
    adb('uiautomator dump /sdcard/window_dump.xml')
    subprocess.run('adb pull /sdcard/window_dump.xml .', shell=True,
                   capture_output=True)
    
    with open('window_dump.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # 文件夹名在 extend_appbar_title 节点
    node_match = re.search(r'<node[^>]*resource-id="com\.huawei\.notepad:id/extend_appbar_title"[^>]*>', xml_content)
    
    if node_match:
        node = node_match.group(0)
        text_match = re.search(r'text="([^"]*)"', node)
        if not text_match:
            text_match = re.search(r"text='([^']*)'", node)
        
        if text_match:
            import html
            folder_name = html.unescape(text_match.group(1))
            # 清理文件名中不允许的字符
            folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            return folder_name
    
    return None

def save_note(f, title, content, note_num, tag=""):
    """保存备忘录到文件"""
    f.write(f"\n{'='*50}\n")
    f.write(f"备忘录 #{note_num} - {title} {tag}\n")
    f.write(f"{'='*50}\n")
    f.write(content)
    f.write(f"\n\n")

print("=== 华为备忘录自动提取工具（终极版）===")
print("\n正在检测当前备忘录文件夹...")

# 尝试获取备忘录文件夹名
folder_name = get_folder_name()

if folder_name:
    print(f"检测到文件夹: {folder_name}")
    default_filename = folder_name
else:
    print("未检测到文件夹名，将使用默认名称")
    import os
    current_folder = os.path.basename(os.getcwd())
    default_filename = f"{current_folder}_备忘录"

print("\n模式选择：")
print("  1. 全自动模式 - 从头提取到底（推荐）")
print("  2. 最后一屏模式 - 只提取当前屏幕")
print("  3. 带截图模式 - 提取文字 + 保存截图")
mode = input("选择模式 (1/2/3): ").strip()

# 询问是否使用默认文件名
print(f"\n默认输出文件名: {default_filename}.txt")
custom_name = input("直接回车使用默认，或输入自定义名称: ").strip()

if custom_name:
    output_file = f'{custom_name}.txt'
    screenshot_dir_base = custom_name
else:
    output_file = f'{default_filename}.txt'
    screenshot_dir_base = default_filename

if mode == "2":
    # ==================== 最后一屏模式 ====================
    print("\n=== 最后一屏模式 ===")
    print("将依次点击屏幕上的5个位置")
    input("请手动滑到最后一屏，按回车开始...")
    
    extracted = 0
    seen_notes = set()
    skip_count = 0
    
    # 实测坐标：只点前5个位置，避免点到屏幕底部
    POSITIONS = [640, 880, 1140, 1395, 1654]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"华为备忘录导出（最后一屏）\n")
        f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"="*50 + "\n\n")
    
    print(f"\n{'='*50}")
    for idx, y_pos in enumerate(POSITIONS, start=1):
        tap(350, y_pos)
        time.sleep(0.5)
        
        title = get_note_title()
        content = get_note_content()
        
        # 检测是否为空（点到屏幕外或空白处）
        if not content or len(content) < 5:
            print(f"[位置 {idx}/5] y={y_pos} → ○ 空位置 (标题: {title})")
            back()
            print(f"→ 检测到空位置，最后一屏提取完毕")
            break
        
        content_hash = content[:100]
        
        if content_hash not in seen_notes:
            seen_notes.add(content_hash)
            
            with open(output_file, 'a', encoding='utf-8') as f:
                save_note(f, title, content, extracted+1, f"[位置{idx}]")
            
            extracted += 1
            print(f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条)")
            back()
            time.sleep(0.3)
        else:
            # 重复内容
            skip_count += 1
            print(f"[位置 {idx}/5] y={y_pos} → ⊗ 跳过: {title} (原因: 内容重复)")
            back()
            time.sleep(0.3)
    
    print(f"{'='*50}")
    print(f"\n✅ 最后一屏提取完成！")
    print(f"成功提取: {extracted} 条")
    print(f"跳过: {skip_count} 条")
    print(f"已保存到: {output_file}")

elif mode == "3":
    # ==================== 带截图模式 ====================
    print("\n=== 带截图模式 ===")
    print("将提取文字内容 + 保存截图到单独文件夹")
    input("请确保手机在备忘录列表顶部，按回车开始...")
    
    # 创建截图文件夹
    import os
    screenshot_dir = f'{screenshot_dir_base}_screenshots'
    os.makedirs(screenshot_dir, exist_ok=True)
    
    extracted = 0
    seen_notes = set()
    last_content = None
    same_content_count = 0
    skip_count = 0
    iteration = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"华为备忘录导出（带截图）\n")
        f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"="*50 + "\n\n")
    
    # 主循环
    while True:
        iteration += 1
        
        tap(350, 560)
        time.sleep(0.5)
        
        title = get_note_title()
        content = get_note_content()
        
        # 检测到底
        if content and content == last_content:
            same_content_count += 1
            if same_content_count >= 3:
                print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复3次-检测到底)")
                back()
                break
            else:
                skip_count += 1
                print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复)")
        else:
            same_content_count = 0
            
            # 模式3：即使内容为空也要截图（可能是纯手绘）
            content_hash = content[:100] if content else f"empty_{iteration}"
            
            if content_hash not in seen_notes:
                seen_notes.add(content_hash)
                
                # 截图
                screenshot_filename = f"note_{extracted+1:04d}.png"
                screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
                
                adb('screencap -p /sdcard/temp_screenshot.png')
                subprocess.run(f'adb pull /sdcard/temp_screenshot.png "{screenshot_path}"', 
                               shell=True, capture_output=True)
                
                # 保存文字 + 截图链接
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"备忘录 #{extracted+1} - {title}\n")
                    f.write(f"{'='*50}\n")
                    if content and len(content) >= 5:
                        f.write(content)
                        f.write(f"\n\n")
                    else:
                        f.write("[纯手绘/图片备忘录，无文字内容]\n\n")
                    f.write(f"[📸 截图: {screenshot_path}]\n\n")
                
                extracted += 1
                print(f"\r[点击 #{iteration}] 已提取: {extracted}条 📸", end='', flush=True)
            else:
                skip_count += 1
                print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复)")
        
        last_content = content
        back()
        swipe_one_item()
        
        if iteration % 30 == 0:
            print(f"\n[暂停3秒] 当前进度: {extracted}条")
            time.sleep(3)
    
    # 提取最后一屏
    print(f"\n\n{'='*50}")
    print("开始提取最后一屏的剩余备忘录...")
    print(f"{'='*50}")
    
    POSITIONS = [880, 1140, 1395, 1654]
    
    for idx, y_pos in enumerate(POSITIONS, start=2):
        tap(350, y_pos)
        time.sleep(0.5)
        
        title = get_note_title()
        content = get_note_content()
        
        # 模式3：即使内容为空也处理（可能是纯手绘）
        content_hash = content[:100] if content else f"empty_last_{idx}"
        
        if content_hash not in seen_notes:
            seen_notes.add(content_hash)
            
            # 截图
            screenshot_filename = f"note_{extracted+1:04d}.png"
            screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
            
            adb('screencap -p /sdcard/temp_screenshot.png')
            subprocess.run(f'adb pull /sdcard/temp_screenshot.png "{screenshot_path}"', 
                           shell=True, capture_output=True)
            
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"备忘录 #{extracted+1} - {title} [最后一屏]\n")
                f.write(f"{'='*50}\n")
                if content and len(content) >= 5:
                    f.write(content)
                    f.write(f"\n\n")
                else:
                    f.write("[纯手绘/图片备忘录，无文字内容]\n\n")
                f.write(f"[📸 截图: {screenshot_path}]\n\n")
            
            extracted += 1
            print(f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条) 📸")
            back()
            time.sleep(0.3)
        else:
            skip_count += 1
            print(f"[位置 {idx}/5] y={y_pos} → ⊗ 跳过: {title} (原因: 内容重复)")
            back()
            time.sleep(0.3)
    
    print(f"\n\n{'='*50}")
    print(f"✅ 带截图提取完成！")
    print(f"{'='*50}")
    print(f"总点击次数: {iteration} 次")
    print(f"成功提取: {extracted} 条")
    print(f"跳过: {skip_count} 条")
    print(f"文字保存到: {output_file}")
    print(f"截图保存到: {screenshot_dir}/ 文件夹 ({extracted} 张)")
    
    # 清理临时文件
    adb('rm /sdcard/temp_screenshot.png')

else:
    # ==================== 全自动模式 ====================
    print("\n=== 全自动模式 ===")
    print("将从第一条开始，一直提取到最后")
    input("请确保手机在备忘录列表顶部，按回车开始...")
    
    extracted = 0
    seen_notes = set()
    last_content = None
    same_content_count = 0
    skip_count = 0
    iteration = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"华为备忘录导出（全量）\n")
        f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"="*50 + "\n\n")
    
    # 主循环：一直提取到检测到底
    while True:
        iteration += 1
        
        # 点击第一条
        tap(350, 560)
        time.sleep(0.5)
        
        title = get_note_title()
        content = get_note_content()
        
        # 检测是否到底（连续3次内容相同）
        if content and content == last_content:
            same_content_count += 1
            if same_content_count >= 3:
                print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复3次-检测到底)")
                back()
                break
            else:
                # 重复但未到3次
                skip_count += 1
                print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复)")
        else:
            same_content_count = 0
            
            # 保存内容
            if content and len(content) >= 5:
                content_hash = content[:100]
                
                if content_hash not in seen_notes:
                    seen_notes.add(content_hash)
                    
                    with open(output_file, 'a', encoding='utf-8') as f:
                        save_note(f, title, content, extracted+1)
                    
                    extracted += 1
                    # 正常提取，刷新同一行
                    print(f"\r[点击 #{iteration}] 已提取: {extracted}条", end='', flush=True)
                else:
                    skip_count += 1
                    print(f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 内容重复)")
            else:
                # 空内容
                print(f"\n[点击 #{iteration}] y=560 → ○ 跳过: {title} (原因: 内容为空或过短)")
        
        last_content = content
        back()
        swipe_one_item()
        
        # 每30次暂停
        if iteration % 30 == 0:
            print(f"\n[暂停3秒] 当前进度: {extracted}条")
            time.sleep(3)
    
    # 提取最后一屏的剩余备忘录（从第2条开始，避免重复点第1条）
    print(f"\n\n{'='*50}")
    print("开始提取最后一屏的剩余备忘录...")
    print(f"{'='*50}")
    
    # 最后一屏实测坐标，从第2条开始（跳过640，因为已经在检测到底前点过了）
    POSITIONS = [880, 1140, 1395, 1654]  # 第2-5条
    
    for idx, y_pos in enumerate(POSITIONS, start=2):
        tap(350, y_pos)
        time.sleep(0.5)
        
        title = get_note_title()
        content = get_note_content()
        
        # 检测是否为空（点到屏幕外或空白处）
        if not content or len(content) < 5:
            print(f"[位置 {idx}/5] y={y_pos} → ○ 空位置 (标题: {title})")
            back()
            print(f"→ 检测到空位置，最后一屏提取完毕")
            break
        
        content_hash = content[:100]
        
        if content_hash not in seen_notes:
            seen_notes.add(content_hash)
            
            with open(output_file, 'a', encoding='utf-8') as f:
                save_note(f, title, content, extracted+1, "[最后一屏]")
            
            extracted += 1
            print(f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条)")
            back()
            time.sleep(0.3)
        else:
            skip_count += 1
            print(f"[位置 {idx}/5] y={y_pos} → ⊗ 跳过: {title} (原因: 内容重复)")
            back()
            time.sleep(0.3)
    
    print(f"\n\n{'='*50}")
    print(f"✅ 全部提取完成！")
    print(f"{'='*50}")
    print(f"总点击次数: {iteration} 次")
    print(f"成功提取: {extracted} 条")
    print(f"跳过: {skip_count} 条")
    print(f"已保存到: {output_file}")
