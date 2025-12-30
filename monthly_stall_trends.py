#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清华大学校园卡月度档口消费趋势统计脚本
获取所有消费记录，统计每月前三档口消费情况
"""

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import requests
from datetime import datetime
import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Tuple

def decrypt_aes_ecb(encrypted_data: str) -> str:
    """AES ECB模式解密函数"""
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')

def fetch_all_records(idserial, servicehall, start_date="2025-01-01", end_date="2025-12-31"):
    """
    获取指定日期范围内的所有消费记录
    """
    print(f"正在获取 {start_date} 到 {end_date} 的所有消费记录...")

    all_records = []
    page_number = 0
    page_size = 5000

    while True:
        url = f"https://card.tsinghua.edu.cn/business/querySelfTradeList?pageNumber={page_number}&pageSize={page_size}&starttime={start_date}&endtime={end_date}&idserial={idserial}&tradetype=-1"
        cookie = {"servicehall": servicehall}

        try:
            response = requests.post(url, cookies=cookie, timeout=30)
            response.raise_for_status()

            # 解密数据
            encrypted_string = json.loads(response.text)["data"]
            decrypted_string = decrypt_aes_ecb(encrypted_string)

            # 解析JSON数据
            data = json.loads(decrypted_string)
            records = data["resultData"]["rows"]

            if not records:
                break

            all_records.extend(records)
            print(f"已获取第 {page_number + 1} 页，共 {len(records)} 条记录")

            # 如果返回的记录数小于page_size，说明已经获取完所有数据
            if len(records) < page_size:
                break

            page_number += 1

        except Exception as e:
            print(f"获取数据时出错: {e}")
            break

    print(f"总共获取到 {len(all_records)} 条消费记录")
    return all_records

def analyze_monthly_stall_trends(records):
    """
    分析每月各档口消费情况
    """
    monthly_stall_data = defaultdict(lambda: defaultdict(float))
    monthly_total = defaultdict(float)

    for record in records:
        try:
            # 提取时间和金额信息
            txdate = record.get("txdate", "")
            mername = record.get("mername", "未知档口")
            txamt = record.get("txamt", 0) / 100  # 转换为元

            if txdate:
                # 解析时间
                try:
                    if " " in txdate:
                        date_part = txdate.split(" ")[0]
                    else:
                        date_part = txdate

                    # 处理不同的时间格式
                    if len(date_part) == 8:  # YYYYMMDD
                        month_key = date_part[:6]  # YYYYMM
                    elif len(date_part) == 10 and date_part.count("-") == 2:  # YYYY-MM-DD
                        month_key = date_part[:7].replace("-", "")  # YYYYMM
                    else:
                        continue

                    # 累积数据
                    monthly_stall_data[month_key][mername] += txamt
                    monthly_total[month_key] += txamt

                except Exception as e:
                    print(f"解析时间失败: {txdate}, 错误: {e}")
                    continue

        except Exception as e:
            print(f"处理记录失败: {e}")
            continue

    return monthly_stall_data, monthly_total

def get_top3_stalls_per_month(monthly_stall_data):
    """
    获取每月前三档口
    """
    monthly_top3 = {}

    for month, stall_data in monthly_stall_data.items():
        # 按消费金额排序
        sorted_stalls = sorted(stall_data.items(), key=lambda x: x[1], reverse=True)
        top3 = sorted_stalls[:3]
        monthly_top3[month] = {
            'top3': top3,
            'total': sum(stall_data.values())
        }

    return monthly_top3

def display_monthly_top3(monthly_top3):
    """
    显示每月前三档口信息
    """
    print("\n" + "="*100)
    print("每月前三档口消费统计")
    print("="*100)

    for month in sorted(monthly_top3.keys()):
        year = month[:4]
        month_num = month[4:]
        data = monthly_top3[month]

        print(f"\n📅 {year}年{month_num}月 (总消费: {data['total']:.2f}元)")
        print("-" * 50)

        for rank, (stall, amount) in enumerate(data['top3'], 1):
            percentage = (amount / data['total'] * 100) if data['total'] > 0 else 0
            print(f"{rank}. {stall:<30} | {amount:>8.2f}元 | {percentage:>5.1f}%")

def create_trend_chart(monthly_stall_data, monthly_total, start_date=None):
    """
    创建消费趋势图表 - 显示所有月份前三名档口的并集，包含完整的12个月
    """
    if not monthly_stall_data:
        print("没有足够的数据创建图表")
        return

    # 动态获取年份
    year = "2025"
    if start_date and len(start_date) >= 4:
        year = start_date[:4]

    # 准备完整的12个月数据
    all_months = [f"{year}{str(i).zfill(2)}" for i in range(1, 13)]
    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月',
                    '7月', '8月', '9月', '10月', '11月', '12月']

    # 收集所有月份的前三名档口并集
    all_top_stalls = set()

    # 为每个月计算前三名
    monthly_top3 = {}
    for month_key in monthly_stall_data.keys():
        stall_data = monthly_stall_data[month_key]
        sorted_stalls = sorted(stall_data.items(), key=lambda x: x[1], reverse=True)
        top3 = sorted_stalls[:3]
        monthly_top3[month_key] = [stall for stall, _ in top3]
        all_top_stalls.update(stall for stall, _ in top3)

    # 为TOP3并集中的档口准备12个月的完整数据
    stall_data = {stall: [0] * 12 for stall in all_top_stalls}

    for i, month_key in enumerate(all_months):
        if month_key in monthly_stall_data:
            month_data = monthly_stall_data[month_key]
            for stall in all_top_stalls:
                # 显示该档口在这个月的实际金额
                stall_data[stall][i] = month_data.get(stall, 0)

    # 创建图表
    plt.figure(figsize=(15, 8))

    # 使用与web应用相同的哈希颜色系统
    def hash_color(stall_name):
        """生成与web应用相同的哈希颜色"""
        import hashlib
        # 使用与web应用相同的哈希逻辑
        parts = stall_name.split('_')
        restaurant = parts[0] if parts else stall_name

        # 为餐厅生成基础色调
        restaurant_hash = hashlib.md5(restaurant.encode()).hexdigest()
        base_hue = int(restaurant_hash[:6], 16) % 360

        # 为档口生成小的偏移
        if len(parts) > 1:
            stall_hash = hashlib.md5(stall_name.encode()).hexdigest()
            offset = (int(stall_hash[:4], 16) % 41) - 20  # -20到+20的偏移
            hue = (base_hue + offset + 360) % 360
        else:
            hue = base_hue

        return hue

    def hsl_to_rgb(h, s, l):
        """将HSL转换为RGB"""
        h = h / 360
        s = s / 100
        l = l / 100

        if s == 0:
            r = g = b = l
        else:
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)

        return (r, g, b)

    # 为每个TOP3档口生成一致的颜色
    stall_colors = {}
    for stall in stall_data.keys():
        hue = hash_color(stall)
        # 使用与web应用相同的亮度和饱和度
        rgb_color = hsl_to_rgb(hue, 70, 60)  # 70%饱和度，60%亮度
        stall_colors[stall] = rgb_color

    # 绘制TOP3档口的趋势线，显示所有月份的完整数据
    for stall, amounts in stall_data.items():
        # 所有TOP3档口都使用粗线
        line_width = 6
        color = stall_colors[stall]
        plt.plot(month_labels, amounts, marker='o', linewidth=line_width, label=stall, color=color)

    plt.title('每月档口消费金额趋势图', fontsize=16, fontweight='bold')
    plt.xlabel('月份', fontsize=12)
    plt.ylabel('消费金额 (元)', fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 保存图表
    plt.savefig('monthly_stall_trends.png', dpi=300, bbox_inches='tight')
    print(f"趋势图已保存为 monthly_stall_trends.png")
    plt.show()

def save_analysis_results(monthly_top3, monthly_stall_data, filename="monthly_analysis.json"):
    """
    保存分析结果到文件
    """
    try:
        # 格式化数据
        formatted_data = {
            "monthly_top3": {},
            "monthly_details": {}
        }

        for month, data in monthly_top3.items():
            year = month[:4]
            month_num = month[4:]
            formatted_data["monthly_top3"][f"{year}-{month_num}"] = {
                "total": data["total"],
                "top3": [{"stall": stall, "amount": amount} for stall, amount in data["top3"]]
            }

        for month, stalls in monthly_stall_data.items():
            year = month[:4]
            month_num = month[4:]
            formatted_data["monthly_details"][f"{year}-{month_num}"] = {
                stall: amount for stall, amount in stalls.items()
            }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)
        print(f"分析结果已保存到 {filename}")

    except Exception as e:
        print(f"保存结果失败: {e}")

def main():
    """主函数"""
    print("清华大学校园卡月度档口消费趋势统计脚本")
    print("="*60)

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

    try:
        # 获取所有消费记录
        records = fetch_all_records(idserial, servicehall, start_date, end_date)

        if not records:
            print("没有获取到任何消费记录")
            return

        # 分析月度档口趋势
        monthly_stall_data, monthly_total = analyze_monthly_stall_trends(records)
        monthly_top3 = get_top3_stalls_per_month(monthly_stall_data)

        # 显示结果
        display_monthly_top3(monthly_top3)

        # 创建图表
        create_trend_chart(monthly_stall_data, monthly_total, start_date)

        # 保存结果
        save_analysis_results(monthly_top3, monthly_stall_data)

        print("\n🎉 分析完成！")
        print("查看生成的文件：")
        print("- monthly_stall_trends.png (趋势图)")
        print("- monthly_analysis.json (详细数据)")

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()