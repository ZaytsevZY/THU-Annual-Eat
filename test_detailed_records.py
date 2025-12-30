#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清华大学校园卡消费记录详细查询测试脚本
可以获取每条消费的详细信息，包括时间、金额、地点等
"""

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import requests
from datetime import datetime
import sys

def decrypt_aes_ecb(encrypted_data: str) -> str:
    """AES ECB模式解密函数"""
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')

def fetch_detailed_records(idserial, servicehall, start_date="2025-01-01", end_date="2025-12-31"):
    """
    获取详细的消费记录

    Args:
        idserial: 学号
        servicehall: 服务代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        list: 详细的消费记录列表
    """

    print(f"正在获取 {start_date} 到 {end_date} 的消费记录...")

    # 构建请求URL
    url = f"https://card.tsinghua.edu.cn/business/querySelfTradeList?pageNumber=0&pageSize=5000&starttime={start_date}&endtime={end_date}&idserial={idserial}&tradetype=-1"

    # 设置cookie
    cookie = {
        "servicehall": servicehall,
    }

    try:
        # 发送请求
        response = requests.post(url, cookies=cookie, timeout=30)
        response.raise_for_status()

        # 解密数据
        encrypted_string = json.loads(response.text)["data"]
        decrypted_string = decrypt_aes_ecb(encrypted_string)

        # 解析JSON数据
        data = json.loads(decrypted_string)

        # 获取所有消费记录
        records = data["resultData"]["rows"]

        print(f"成功获取到 {len(records)} 条消费记录")
        return records

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"发生错误: {e}")
        return []

def display_records(records):
    """显示消费记录的详细信息"""

    if not records:
        print("没有找到任何消费记录")
        return

    print("\n" + "="*80)
    print("详细消费记录")
    print("="*80)

    total_amount = 0
    for i, record in enumerate(records, 1):
        try:
            # 提取信息
            mername = record.get("mername", "未知商户")
            txamt = record.get("txamt", 0) / 100  # 转换为元
            txdate = record.get("txdate", "")
            txtime = record.get("txtime", "")

            # 格式化时间
            if txdate and txtime:
                try:
                    dt = datetime.strptime(f"{txdate} {txtime}", "%Y%m%d %H%M%S")
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    formatted_time = f"{txdate} {txtime}"
            else:
                formatted_time = "时间未知"

            print(f"{i:3d}. {formatted_time} | {mername:<20} | {txamt:>8.2f}元")

            # 显示其他可用字段（调试用）
            extra_fields = {k:v for k,v in record.items()
                          if k not in ["mername", "txamt", "txdate", "txtime"]}
            if extra_fields:
                print(f"    其他信息: {extra_fields}")

            total_amount += txamt

        except Exception as e:
            print(f"{i:3d}. 解析记录时出错: {e}")
            print(f"    原始数据: {record}")

    print("-"*80)
    print(f"总计: {len(records)} 条记录，总消费: {total_amount:.2f}元")
    print("="*80)

def save_records_to_file(records, filename="detailed_records.json"):
    """将详细记录保存到JSON文件"""
    if not records:
        return

    # 转换金额单位
    for record in records:
        if "txamt" in record:
            record["txamt_yuan"] = record["txamt"] / 100

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"记录已保存到 {filename}")
    except Exception as e:
        print(f"保存文件失败: {e}")

def main():
    """主函数"""
    print("清华大学校园卡消费记录详细查询测试脚本")
    print("="*50)

    # 获取用户输入
    idserial = input("请输入学号: ").strip()
    servicehall = input("请输入服务代码: ").strip()

    # 可选的日期范围
    print("\n可选：输入查询日期范围（直接回车使用全年）")
    start_date = input("开始日期 (YYYY-MM-DD，默认2025-01-01): ").strip()
    end_date = input("结束日期 (YYYY-MM-DD，默认2025-12-31): ").strip()

    if not start_date:
        start_date = "2025-01-01"
    if not end_date:
        end_date = "2025-12-31"

    # 验证日期格式
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("日期格式错误，请使用YYYY-MM-DD格式")
        return

    # 获取详细记录
    records = fetch_detailed_records(idserial, servicehall, start_date, end_date)

    if records:
        # 显示记录
        display_records(records)

        # 询问是否保存到文件
        save_choice = input("\n是否将详细记录保存到JSON文件？(y/n): ").strip().lower()
        if save_choice == 'y':
            save_records_to_file(records)
    else:
        print("未能获取到任何消费记录，请检查学号和服务代码是否正确")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        sys.exit(1)