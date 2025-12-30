from fastapi import FastAPI, Request, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import requests
import os
from typing import Dict, List
from datetime import datetime

app = FastAPI(title="清华大学食堂消费分析", description="网页版食堂消费数据分析工具")

# 创建静态文件和模板目录
if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists("templates"):
    os.makedirs("templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def decrypt_aes_ecb(encrypted_data: str) -> str:
    """AES ECB模式解密"""
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    """处理Chrome开发者工具请求"""
    return {"status": "ok", "message": "Chrome devtools endpoint"}

@app.post("/api/analyze")
async def analyze_consumption(
    idserial: str = Form(...),
    servicehall: str = Form(...),
    start_date: str = Form(default="2025-01-01"),
    end_date: str = Form(default="2025-12-31")
) -> Dict:
    return await _perform_analysis(idserial, servicehall, start_date, end_date)

@app.get("/api/analyze")
async def analyze_consumption_get(
    idserial: str,
    servicehall: str,
    start_date: str = Query("2024-01-01", alias="startDate"),
    end_date: str = Query("2024-12-31", alias="endDate")
) -> Dict:
    return await _perform_analysis(idserial, servicehall, start_date, end_date)

def fetch_all_records(idserial, servicehall, start_date, end_date):
    """
    获取指定日期范围内的所有消费记录
    """
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

            # 如果返回的记录数小于page_size，说明已经获取完所有数据
            if len(records) < page_size:
                break

            page_number += 1

        except Exception as e:
            print(f"获取数据时出错: {e}")
            break

    return all_records

def analyze_monthly_stall_trends(records):
    """
    分析月度档口消费趋势
    """
    monthly_stall_data = {}
    monthly_stall_totals = {}

    for record in records:
        try:
            # 提取时间和商户信息
            txdate = record.get("txdate", "")
            mername = record.get("mername", "")
            txamt = record.get("txamt", 0) / 100  # 转换为元

            # 跳过未知档口和位置商户
            if not mername or mername.strip() in ["未知档口", "未知商户", "", "位置商户"]:
                continue

            if txdate:
                # 解析月份
                try:
                    # 处理时间格式
                    date_str = str(txdate)

                    # 提取年月信息
                    if " " in date_str:
                        date_part = date_str.split(" ")[0]
                    else:
                        date_part = date_str

                    # 标准化月份格式 - 统一使用YYYY-MM格式
                    if len(date_part) == 8:  # YYYYMMDD
                        month_key = f"{date_part[:4]}-{date_part[4:6]}"
                    elif len(date_part) == 10 and date_part.count("-") == 2:  # YYYY-MM-DD
                        month_key = date_part[:7]
                    else:
                        # 尝试其他格式
                        try:
                            dt = datetime.strptime(date_part[:10], "%Y%m%d" if len(date_part) >= 8 else "%Y-%m-%d")
                            month_key = dt.strftime("%Y-%m")
                        except:
                            continue

                    # 累积月度档口数据
                    if month_key not in monthly_stall_data:
                        monthly_stall_data[month_key] = {}
                        monthly_stall_totals[month_key] = 0.0

                    if mername not in monthly_stall_data[month_key]:
                        monthly_stall_data[month_key][mername] = 0.0

                    monthly_stall_data[month_key][mername] += round(txamt, 2)
                    monthly_stall_totals[month_key] = round(monthly_stall_totals[month_key] + txamt, 2)

                except Exception as e:
                    print(f"解析时间失败: {txdate}, 错误: {e}")
                    continue

        except Exception as e:
            print(f"处理记录失败: {e}")
            continue

    # 格式化月度趋势数据
    monthly_trends = {}
    all_stalls = set()

    # 收集所有档口
    for month_data in monthly_stall_data.values():
        all_stalls.update(month_data.keys())

    # 计算每个档口的总消费金额，用于筛选TOP3
    stall_totals = {}
    for stall in all_stalls:
        total = sum(monthly_stall_data[month_key].get(stall, 0) for month_key in monthly_stall_data.keys())
        stall_totals[stall] = total

    # 获取TOP3档口
    top3_stalls = sorted(stall_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_stall_names = {stall for stall, _ in top3_stalls}

    # 为每个月准备数据
    for month_key in sorted(monthly_stall_data.keys()):
        stall_data = monthly_stall_data[month_key]

        # 只包含TOP3档口的数据，但显示所有月份的实际金额
        top3_month_data = []
        for stall_name in top3_stall_names:
            amount = stall_data.get(stall_name, 0)
            top3_month_data.append({"stall": stall_name, "amount": round(amount, 2)})

        monthly_trends[month_key] = {
            "total": round(monthly_stall_totals[month_key], 2),
            "top3": top3_month_data,
            "all_stalls": {stall: round(amount, 2) for stall, amount in stall_data.items()}
        }

    return monthly_trends

async def _perform_analysis(
    idserial: str,
    servicehall: str,
    start_date: str,
    end_date: str
) -> Dict:
    """分析消费数据"""
    try:
        # 获取所有消费记录
        records = fetch_all_records(idserial, servicehall, start_date, end_date)

        if not records:
            return {"success": False, "error": "没有获取到任何消费记录"}

        # 分析总体消费数据
        all_data = {}
        for record in records:
            try:
                merchant = record.get("mername", "")
                amount = record.get("txamt", 0)

                # 跳过未知档口和位置商户
                if not merchant or merchant.strip() in ["未知档口", "未知商户", "", "位置商户"]:
                    continue

                if merchant in all_data:
                    all_data[merchant] += amount
                else:
                    all_data[merchant] = amount
            except Exception:
                continue

        # 转换为元并排序
        all_data = {k: round(v / 100, 2) for k, v in all_data.items()}
        sorted_data = dict(sorted(all_data.items(), key=lambda x: x[1], reverse=True))

        # 计算统计信息
        total_amount = sum(all_data.values())
        avg_amount = total_amount / len(all_data) if all_data else 0

        # 准备总体消费数据
        result = []
        for merchant, amount in sorted_data.items():
            result.append({
                "merchant": merchant,
                "amount": amount,
                "percentage": round((amount / total_amount) * 100, 2) if total_amount > 0 else 0
            })

        # 分析月度档口数据
        monthly_trends = analyze_monthly_stall_trends(records)

        return {
            "success": True,
            "data": result,
            "total": total_amount,
            "count": len(result),
            "average": round(avg_amount, 2),
            "start_date": start_date,
            "end_date": end_date,
            "monthly_trends": monthly_trends
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)