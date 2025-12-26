# -*- coding: utf-8 -*-
import sys
import base64
import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# 强制全局编码 + 环境变量净化
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# 环境变量配置（强制转字符串+去空白）
WEATHER_KEY = str(os.getenv("WEATHER_KEY", "")).strip()
WEATHER_HOST = str(os.getenv("WEATHER_HOST", "")).strip()
SMTP_USER = str(os.getenv("SMTP_USER", "")).strip()
SMTP_PWD = str(os.getenv("SMTP_PWD", "")).strip()
TO_EMAIL_STR = str(os.getenv("TO_EMAIL", "")).strip()
TO_EMAIL_LIST = [x.strip() for x in TO_EMAIL_STR.split(",") if x.strip()]
# 新增：GitHub Token（在仓库 Secrets 中添加名为 GITHUB_TOKEN 的密钥）
GITHUB_TOKEN = str(os.getenv("GITHUB_TOKEN", "")).strip()

# 城市配置（纯英文标点）
CITIES = {
    "101281901": "Chaozhou",
    "101281601": "Dongguan"
}

# 新增：获取GitHub Actions剩余额度
def get_gh_actions_remaining():
    if not GITHUB_TOKEN:
        return "GitHub Token not set (add GITHUB_TOKEN in Secrets)"
    url = "https://api.github.com/users/{user}/settings/billing/actions"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        # 先获取用户名
        user_res = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        user_res.raise_for_status()
        username = user_res.json()["login"]
        # 获取Actions账单
        res = requests.get(url.format(user=username), headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return f"GitHub Actions: Used {data['total_minutes_used']} min, Remaining {data['total_minutes_remaining']} min, Cycle ends in {data['days_left_in_billing_cycle']} days"
    except Exception as e:
        return f"Actions quota fetch failed: {str(e)}"

# 新增：估算天气API剩余调用
def estimate_weather_api_remaining():
    total_month_calls = 3 * 30  # 每天3次 × 30天
    used_calls = len(CITIES) * 3  # 每次运行调用次数：城市数 × 3天预报
    remaining = max(0, 10000 - used_calls)  # 假设API日限10000，可修改
    return f"Weather API: Estimated monthly used {total_month_calls} calls, Remaining (est) {remaining} calls"

def get_weather(city_id):
    if not WEATHER_HOST or not WEATHER_KEY:
        return "API config missing, check Secrets"
    url = f"{WEATHER_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data["daily"] if data["code"] == "200" else f"Error code: {data['code']}"
    except Exception as e:
        return f"API failed: {str(e)}"

def format_weather(city_eng, weather_data):
    if isinstance(weather_data, str):
        return f"{city_eng}: {weather_data}\n"
    text = f"\n[{city_eng} 3-Day Weather]\n"
    for day in weather_data:
        text += f"{day['fxDate']}: {day['textDay']}, Temp {day['tempMin']}℃-{day['tempMax']}℃, Wind {day['windDirDay']} {day['windScaleDay']} Level\n"
    return text

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ Email config incomplete")
        return

    # 拼接内容
    total_weather = "Daily Weather Forecast (3-Day)\n"
    for cid, cname in CITIES.items():
        total_weather += format_weather(cname, get_weather(cid))

    # 新增：拼接额度信息到邮件末尾
    total_weather += "\n" + "="*30 + "\n"
    total_weather += "Quota Status:\n"
    total_weather += f"- {get_gh_actions_remaining()}\n"
    total_weather += f"- {estimate_weather_api_remaining()}\n"
    total_weather += f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    try:
        content_b64 = base64.b64encode(total_weather.encode('utf-8')).decode('ascii')
        msg = MIMEText(base64.b64decode(content_b64), 'plain', 'utf-8')
        msg['From'] = SMTP_USER
        msg['Subject'] = "Daily Weather Forecast"

        with smtplib.SMTP("smtp.qq.com", 587, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PWD)
            success = 0
            for to_email in TO_EMAIL_LIST:
                msg['To'] = to_email
                server.sendmail(SMTP_USER, to_email, msg.as_bytes())
                success += 1
        print(f"✅ Sent to {success} email(s)")
    except smtplib.SMTPAuthenticationError:
        print("❌ Email login failed, check SMTP_PWD")
    except Exception as e:
        print(f"❌ Send failed: {str(e)}")

def main():
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🔍 First run, trigger manually...")
    send_weather_email()
    # main()
