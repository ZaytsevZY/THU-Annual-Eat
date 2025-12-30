#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：检查月度消费数据获取和解析问题
"""

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import requests
from datetime import datetime

def decrypt_aes_ecb(encrypted_data: str) -> str:
    """AES ECB模式解密函数"""
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')

def fetch_and_debug(idserial, servicehall, start_date="2025-01-01", end_date="2025-12-31"):
    """获取并调试数据"""
    print(f"正在调试 {idserial} 的数据...")
    print(f"日期范围: {start_date} 到 {end_date}")

    all_records = []
    page_number = 0
    page_size = 5000

    while True:
        url = f"https://card.tsinghua.edu.cn/business/querySelfTradeList?pageNumber={page_number}&pageSize={page_size}&starttime={start_date}&endtime={end_date}&idserial={idserial}&tradetype=-1"
        cookie = {"servicehall": servicehall}

        try:
            print(f"正在获取第 {page_number + 1} 页数据...")
            response = requests.post(url, cookies=cookie, timeout=30)
            response.raise_for_status()

            # 解密数据
            result = json.loads(response.text)
            if "data" not in result:
                print("错误：响应中没有'data'字段")
                print("响应内容:", result)
                break

            encrypted_string = result["data"]
            decrypted_string = decrypt_aes_ecb(encrypted_string)

            # 解析JSON数据
            data = json.loads(decrypted_string)
            records = data["resultData"]["rows"]

            print(f"第 {page_number + 1} 页获取到 {len(records)} 条记录")

            if not records:
                print("没有更多记录")
                break

            all_records.extend(records)

            # 如果返回的记录数小于page_size，说明已经获取完所有数据
            if len(records) < page_size:
                break

            page_number += 1

        except Exception as e:
            print(f"获取数据时出错: {e}")
            break

    print(f"\n总共获取到 {len(all_records)} 条记录")

    if not all_records:
        print("没有获取到任何记录")
        return

    # 调试月度数据
    print("\n=== 调试月度数据 ===")
    monthly_data = {}

    for record in all_records:
        try:
            txdate = record.get("txdate", "")
            mername = record.get("mername", "")
            txamt = record.get("txamt", 0)

            # 跳过未知档口和位置商户
            if not mername or mername.strip() in ["未知档口", "未知商户", "", "位置商户"]:
                continue

            print(f"原始记录: txdate={txdate}, mername={mername}, txamt={txamt}")

            if txdate:
                # 解析时间
                date_str = str(txdate)

                # 提取年月信息
                month_key = None
                try:
                    if len(date_str) >= 8 and date_str[0:8].isdigit():
                        # YYYYMMDD 格式
                        month_key = f"{date_str[:4]}-{date_str[4:6]}"
                    elif "-" in date_str:
                        # YYYY-MM-DD 格式
                        parts = date_str.split("-")
                        if len(parts) >= 2:
                            month_key = f"{parts[0]}-{parts[1]}"
                    else:
                        # 尝试解析其他格式
                        dt = datetime.strptime(date_str.split(" ")[0], "%Y%m%d")
                        month_key = dt.strftime("%Y-%m")
                except Exception as e:
                    print(f"时间解析失败: {date_str}, 错误: {e}")
                    continue

                if month_key:
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {
                            "total": 0.0,
                            "stalls": {},
                            "records": []
                        }

                    monthly_data[month_key]["total"] += txamt / 100
                    monthly_data[month_key]["records"].append({
                        "merchant": mername,
                        "amount": txamt / 100,
                        "date": txdate
                    })

                    if mername not in monthly_data[month_key]["stalls"]:
                        monthly_data[month_key]["stalls"][mername] = 0.0

                    monthly_data[month_key]["stalls"][mername] += txamt / 100

        except Exception as e:
            print(f"处理记录失败: {e}")
            continue

    print(f"\n=== 月度统计结果 ===")
    if monthly_data:
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            print(f"\n{month_key}: 总消费 {round(data['total'], 2)}元")

            # 排序档口
            sorted_stalls = sorted(data["stalls"].items(), key=lambda x: x[1], reverse=True)
            print("  前三档口:")
            for i, (stall, amount) in enumerate(sorted_stalls[:3], 1):
                print(f"    {i}. {stall}: {round(amount, 2)}元")
    else:
        print("没有有效的月度数据")

    return monthly_data

if __name__ == "__main__":
    idserial = "2022012107"
    servicehall = "NWMyOTUwMGYtZmY4Yi00ZjE5LTgzZTctODQ5MDk1ZmQzZThi"

    debug_result = fetch_and_debug(idserial, servicehall)

    print(f"\n=== 总结 ===")
    if debug_result:
        for month, data in debug_result.items():
            print(f"{month}: {round(data['total'], 2)}元")