#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
华为备忘录提取工具 / Huawei Notepad Extractor

批量提取华为手机备忘录内容的Python脚本
A Python script for batch extracting Huawei phone notepad content

作者 / Authors: Jessica & Claude
修复 / Fixes: GPT-5.6 Sol (OpenAI)
许可 / License: MIT License
请仅提取你有权访问和备份的数据。
Only extract data that you are authorized to access and back up.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

APP_ID_PREFIX = "com.huawei.notepad:id/"
MAX_ITERATIONS = 10000


class ExtractionError(RuntimeError):
    """可向用户显示的提取错误。"""


def find_adb():
    """优先使用 PATH 中的 ADB，也支持仓库中已解压的 Windows 工具。"""
    executable = shutil.which("adb")
    if executable:
        return executable

    bundled = Path(__file__).resolve().parent / "platform-tools" / "adb.exe"
    if bundled.is_file():
        return str(bundled)

    raise ExtractionError(
        "未找到 ADB。请安装 ADB 并加入 PATH，或将仓库中的 "
        "platform-tools-latest-windows.zip 解压到仓库根目录。"
    )


ADB = None
DEVICE_SERIAL = None


def adb_command(*args):
    """构造锁定到已检查设备的 ADB 命令。"""
    if ADB is None:
        raise ExtractionError("ADB 尚未初始化。")
    command = [ADB]
    if DEVICE_SERIAL:
        command.extend(["-s", DEVICE_SERIAL])
    command.extend(args)
    return command


def adb(cmd):
    """在唯一已连接设备上执行 shell 命令，失败时立即停止。"""
    args = cmd.split() if isinstance(cmd, str) else list(cmd)
    result = subprocess.run(
        adb_command("shell", *args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise ExtractionError(f"ADB 命令失败: {detail}")
    return result.stdout.strip()


def check_device():
    """确保恰好有一台已授权设备，避免操作错设备。"""
    global DEVICE_SERIAL
    DEVICE_SERIAL = None
    if ADB is None:
        raise ExtractionError("ADB 尚未初始化。")
    result = subprocess.run(
        [ADB, "devices"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=True,
    )
    devices = []
    unauthorized = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
        elif len(parts) >= 2:
            unauthorized.append(f"{parts[0]} ({parts[1]})")
    if len(devices) != 1:
        detail = f"；异常设备: {', '.join(unauthorized)}" if unauthorized else ""
        raise ExtractionError(
            f"需要且只能连接一台已授权设备，当前检测到 {len(devices)} 台{detail}"
        )
    DEVICE_SERIAL = devices[0]


def tap(x, y):
    adb(f"input tap {x} {y}")
    time.sleep(0.6)


def back():
    adb("input keyevent KEYCODE_BACK")
    time.sleep(0.6)


def swipe_one_item():
    """向上滑动整整一条备忘录的距离"""
    adb("input swipe 350 750 350 550 200")
    time.sleep(0.8)


def dump_ui():
    """获取并解析一次当前 UI；绝不复用失败前遗留的 XML。"""
    adb(["rm", "-f", "/sdcard/window_dump.xml"])
    adb(["uiautomator", "dump", "/sdcard/window_dump.xml"])
    result = subprocess.run(
        adb_command("exec-out", "cat", "/sdcard/window_dump.xml"),
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.decode("utf-8", "replace").strip() or "未取得 UI XML"
        raise ExtractionError(f"读取手机界面失败: {detail}")
    try:
        return ET.fromstring(result.stdout)
    except ET.ParseError as exc:
        raise ExtractionError(f"手机界面 XML 无法解析: {exc}") from exc


def node_text(root, resource_name):
    resource_id = APP_ID_PREFIX + resource_name
    for node in root.iter("node"):
        if node.attrib.get("resource-id") == resource_id:
            return node.attrib.get("text", ""), True
    return "", False


def ui_signature(root):
    """生成列表界面的稳定签名，用于判断滑动是否真的移动了列表。"""
    visible = []
    for node in root.iter("node"):
        attributes = node.attrib
        resource_id = attributes.get("resource-id", "")
        if attributes.get(
            "package"
        ) != "com.huawei.notepad" and not resource_id.startswith(APP_ID_PREFIX):
            continue
        visible.append(
            (
                resource_id,
                attributes.get("text", ""),
                attributes.get("content-desc", ""),
                attributes.get("bounds", ""),
            )
        )
    return hashlib.sha256(repr(visible).encode("utf-8")).hexdigest()


def get_note():
    """用同一次 UI 快照取得标题、时间和正文，并确认确实在详情页。"""
    root = dump_ui()
    title, has_title = node_text(root, "title")
    timestamp, has_timestamp = node_text(root, "notecontent_date_text")
    content, has_content = node_text(root, "notetext_textview")
    # 列表页也可能含有 title 节点；时间或正文节点才足以证明已进入详情页。
    if not (has_timestamp or has_content):
        return None
    display_title = title or "未知"
    if timestamp:
        display_title = f"{display_title} - {timestamp}"
    identity = hashlib.sha256(
        "\0".join((title, timestamp, content)).encode("utf-8")
    ).hexdigest()
    return display_title, content, identity


def get_folder_name():
    """获取当前备忘录文件夹名称"""
    folder_name, found = node_text(dump_ui(), "extend_appbar_title")
    return safe_name(folder_name) if found and folder_name.strip() else None


def safe_name(name):
    """把用户或手机提供的名称限制为当前目录中的安全文件名。"""
    cleaned = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name)
    cleaned = cleaned.strip(" .")[:120].rstrip(" .")
    reserved = {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"}
    reserved.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    # Windows 也会把 CON.txt、LPT1.backup 等视为保留设备名。
    if cleaned.partition(".")[0].upper() in reserved:
        cleaned = f"_{cleaned}"
    return cleaned or "华为备忘录导出"


def unused_path(path):
    """避免无提示覆盖已有备份。"""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return path
    for number in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{number}{path.suffix}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
    raise ExtractionError("无法生成未占用的输出文件名。")


def take_screenshot(destination):
    adb(["screencap", "-p", "/sdcard/temp_screenshot.png"])
    result = subprocess.run(
        adb_command("pull", "/sdcard/temp_screenshot.png", str(destination)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0 or not Path(destination).is_file():
        detail = result.stderr.strip() or result.stdout.strip() or "截图文件未生成"
        raise ExtractionError(f"拉取截图失败: {detail}")


def save_note(f, title, content, note_num, tag=""):
    """保存备忘录到文件"""
    f.write(f"\n{'=' * 50}\n")
    f.write(f"备忘录 #{note_num} - {title} {tag}\n")
    f.write(f"{'=' * 50}\n")
    f.write(content)
    f.write("\n\n")


def main():
    global ADB
    print("=== 华为备忘录自动提取工具（终极版）===")
    ADB = find_adb()
    check_device()
    print("\n正在检测当前备忘录文件夹...")

    # 尝试获取备忘录文件夹名
    folder_name = get_folder_name()

    if folder_name:
        print(f"检测到文件夹: {folder_name}")
        default_filename = folder_name
    else:
        print("未检测到文件夹名，将使用默认名称")
        current_folder = os.path.basename(os.getcwd())
        default_filename = f"{current_folder}_备忘录"

    print("\n模式选择：")
    print("  1. 全自动模式 - 从头提取到底（推荐）")
    print("  2. 最后一屏模式 - 只提取当前屏幕")
    print("  3. 带截图模式 - 提取文字 + 保存截图")
    mode = input("选择模式 (1/2/3): ").strip()
    while mode not in {"1", "2", "3"}:
        print("输入无效，请输入 1、2 或 3。")
        mode = input("选择模式 (1/2/3): ").strip()

    # 询问是否使用默认文件名
    print(f"\n默认输出文件名: {default_filename}.txt")
    custom_name = input("直接回车使用默认，或输入自定义名称: ").strip()

    if custom_name:
        screenshot_dir_base = safe_name(custom_name)
    else:
        screenshot_dir_base = safe_name(default_filename)

    output_file = unused_path(f"{screenshot_dir_base}.txt")

    if mode == "2":
        # ==================== 最后一屏模式 ====================
        print("\n=== 最后一屏模式 ===")
        print("将依次点击屏幕上的5个位置")
        input("请手动滑到最后一屏，按回车开始...")

        extracted = 0
        skip_count = 0

        # 实测坐标：只点前5个位置，避免点到屏幕底部
        POSITIONS = [640, 880, 1140, 1395, 1654]

        with open(output_file, "x", encoding="utf-8") as f:
            f.write("华为备忘录导出（最后一屏）\n")
            f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

        print(f"\n{'=' * 50}")
        for idx, y_pos in enumerate(POSITIONS, start=1):
            tap(350, y_pos)
            time.sleep(0.5)

            note = get_note()

            # 检测是否为空（点到屏幕外或空白处）
            if note is None:
                print(f"[位置 {idx}/5] y={y_pos} → ○ 未进入备忘录详情页")
                print("→ 检测到空位置，最后一屏提取完毕")
                break

            title, content, _identity = note

            with open(output_file, "a", encoding="utf-8") as f:
                save_note(f, title, content, extracted + 1, f"[位置{idx}]")

            extracted += 1
            print(f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条)")
            back()
            time.sleep(0.3)

        print(f"{'=' * 50}")
        print("\n✅ 最后一屏提取完成！")
        print(f"成功提取: {extracted} 条")
        print(f"跳过: {skip_count} 条")
        print(f"已保存到: {output_file}")

    elif mode == "3":
        # ==================== 带截图模式 ====================
        print("\n=== 带截图模式 ===")
        print("将提取文字内容 + 保存截图到单独文件夹")
        input("请确保手机在备忘录列表顶部，按回车开始...")

        # 创建截图文件夹
        screenshot_dir = unused_path(f"{screenshot_dir_base}_screenshots")
        os.makedirs(screenshot_dir)

        extracted = 0
        processed_positions = set()
        stagnation_count = 0
        skip_count = 0
        iteration = 0

        with open(output_file, "x", encoding="utf-8") as f:
            f.write("华为备忘录导出（带截图）\n")
            f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

        # 主循环
        current_list_signature = ui_signature(dump_ui())
        while True:
            iteration += 1
            position_seen = current_list_signature in processed_positions

            tap(350, 560)
            time.sleep(0.5)

            note = get_note()
            if note is None:
                raise ExtractionError(
                    "点击后未进入备忘录详情页；已停止以避免误操作。请检查坐标。"
                )
            title, content, _identity = note

            # 检测到底
            if position_seen:
                skip_count += 1
                print(
                    f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 列表未移动)"
                )
            else:
                processed_positions.add(current_list_signature)

                # 模式3：即使内容为空也要截图（可能是纯手绘）
                screenshot_filename = f"note_{extracted + 1:04d}.png"
                screenshot_path = screenshot_dir / screenshot_filename
                take_screenshot(screenshot_path)

                # 保存文字 + 截图链接
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 50}\n")
                    f.write(f"备忘录 #{extracted + 1} - {title}\n")
                    f.write(f"{'=' * 50}\n")
                    if content:
                        f.write(content)
                        f.write("\n\n")
                    else:
                        f.write("[纯手绘/图片备忘录，无文字内容]\n\n")
                    f.write(f"[📸 截图: {screenshot_path}]\n\n")

                extracted += 1
                print(
                    f"\r[点击 #{iteration}] 已提取: {extracted}条 📸",
                    end="",
                    flush=True,
                )

            back()
            before_swipe = ui_signature(dump_ui())
            swipe_one_item()
            after_swipe = ui_signature(dump_ui())
            current_list_signature = after_swipe
            if before_swipe == after_swipe:
                stagnation_count += 1
                if stagnation_count >= 3:
                    print("\n列表连续3次未移动，已到达底部。")
                    break
            else:
                stagnation_count = 0

            if iteration % 30 == 0:
                print(f"\n[暂停3秒] 当前进度: {extracted}条")
                time.sleep(3)

            if iteration >= MAX_ITERATIONS:
                raise ExtractionError(
                    f"已达到安全上限 {MAX_ITERATIONS} 次，提取已停止。"
                )

        # 提取最后一屏
        print(f"\n\n{'=' * 50}")
        print("开始提取最后一屏的剩余备忘录...")
        print(f"{'=' * 50}")

        POSITIONS = [880, 1140, 1395, 1654]

        for idx, y_pos in enumerate(POSITIONS, start=2):
            tap(350, y_pos)
            time.sleep(0.5)

            note = get_note()

            # 模式3：即使内容为空也处理（可能是纯手绘）
            if note is None:
                print(f"[位置 {idx}/5] y={y_pos} → ○ 未进入备忘录详情页")
                break
            title, content, _identity = note

            screenshot_filename = f"note_{extracted + 1:04d}.png"
            screenshot_path = screenshot_dir / screenshot_filename
            take_screenshot(screenshot_path)

            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 50}\n")
                f.write(f"备忘录 #{extracted + 1} - {title} [最后一屏]\n")
                f.write(f"{'=' * 50}\n")
                if content:
                    f.write(content)
                    f.write("\n\n")
                else:
                    f.write("[纯手绘/图片备忘录，无文字内容]\n\n")
                f.write(f"[📸 截图: {screenshot_path}]\n\n")

            extracted += 1
            print(
                f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条) 📸"
            )
            back()
            time.sleep(0.3)

        print(f"\n\n{'=' * 50}")
        print("✅ 带截图提取完成！")
        print(f"{'=' * 50}")
        print(f"总点击次数: {iteration} 次")
        print(f"成功提取: {extracted} 条")
        print(f"跳过: {skip_count} 条")
        print(f"文字保存到: {output_file}")
        print(f"截图保存到: {screenshot_dir}/ 文件夹 ({extracted} 张)")

        # 清理临时文件
        adb("rm /sdcard/temp_screenshot.png")

    else:
        # ==================== 全自动模式 ====================
        print("\n=== 全自动模式 ===")
        print("将从第一条开始，一直提取到最后")
        input("请确保手机在备忘录列表顶部，按回车开始...")

        extracted = 0
        processed_positions = set()
        stagnation_count = 0
        skip_count = 0
        iteration = 0

        with open(output_file, "x", encoding="utf-8") as f:
            f.write("华为备忘录导出（全量）\n")
            f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

        # 主循环：一直提取到检测到底
        current_list_signature = ui_signature(dump_ui())
        while True:
            iteration += 1
            position_seen = current_list_signature in processed_positions

            # 点击第一条
            tap(350, 560)
            time.sleep(0.5)

            note = get_note()
            if note is None:
                raise ExtractionError(
                    "点击后未进入备忘录详情页；已停止以避免误操作。请检查坐标。"
                )
            title, content, _identity = note

            if position_seen:
                skip_count += 1
                print(
                    f"\n[点击 #{iteration}] y=560 → ⊗ 跳过: {title} (原因: 列表未移动)"
                )
            else:
                processed_positions.add(current_list_signature)

                # 保存内容
                if content:
                    with open(output_file, "a", encoding="utf-8") as f:
                        save_note(f, title, content, extracted + 1)

                    extracted += 1
                    # 正常提取，刷新同一行
                    print(
                        f"\r[点击 #{iteration}] 已提取: {extracted}条",
                        end="",
                        flush=True,
                    )
                else:
                    # 空内容
                    print(
                        f"\n[点击 #{iteration}] y=560 → ○ 跳过: {title} (原因: 内容为空)"
                    )

            back()
            before_swipe = ui_signature(dump_ui())
            swipe_one_item()
            after_swipe = ui_signature(dump_ui())
            current_list_signature = after_swipe
            if before_swipe == after_swipe:
                stagnation_count += 1
                if stagnation_count >= 3:
                    print("\n列表连续3次未移动，已到达底部。")
                    break
            else:
                stagnation_count = 0

            # 每30次暂停
            if iteration % 30 == 0:
                print(f"\n[暂停3秒] 当前进度: {extracted}条")
                time.sleep(3)

            if iteration >= MAX_ITERATIONS:
                raise ExtractionError(
                    f"已达到安全上限 {MAX_ITERATIONS} 次，提取已停止。"
                )

        # 提取最后一屏的剩余备忘录（从第2条开始，避免重复点第1条）
        print(f"\n\n{'=' * 50}")
        print("开始提取最后一屏的剩余备忘录...")
        print(f"{'=' * 50}")

        # 最后一屏实测坐标，从第2条开始（跳过640，因为已经在检测到底前点过了）
        POSITIONS = [880, 1140, 1395, 1654]  # 第2-5条

        for idx, y_pos in enumerate(POSITIONS, start=2):
            tap(350, y_pos)
            time.sleep(0.5)

            note = get_note()

            # 检测是否为空（点到屏幕外或空白处）
            if note is None:
                print(f"[位置 {idx}/5] y={y_pos} → ○ 未进入备忘录详情页")
                print("→ 检测到空位置，最后一屏提取完毕")
                break
            title, content, _identity = note

            with open(output_file, "a", encoding="utf-8") as f:
                save_note(f, title, content, extracted + 1, "[最后一屏]")

            extracted += 1
            print(f"[位置 {idx}/5] y={y_pos} → ✓ 提取: {title} (已提取: {extracted}条)")
            back()
            time.sleep(0.3)

        print(f"\n\n{'=' * 50}")
        print("✅ 全部提取完成！")
        print(f"{'=' * 50}")
        print(f"总点击次数: {iteration} 次")
        print(f"成功提取: {extracted} 条")
        print(f"跳过: {skip_count} 条")
        print(f"已保存到: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except (ExtractionError, subprocess.SubprocessError, OSError) as exc:
        print(f"\n❌ 提取已安全停止: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断，提取已停止。", file=sys.stderr)
        raise SystemExit(130)
