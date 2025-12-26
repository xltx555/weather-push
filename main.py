# -*- coding: utf-8 -*-
import sys
import base64
import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from datetime import datetime

# 强制编码，杜绝ASCII fallback
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# 环境变量配置
WEATHER_KEY = str(os.getenv("WEATHER_KEY", "")).strip()
WEATHER_HOST = str(os.getenv("WEATHER_HOST", "")).strip()
SMTP_USER = str(os.getenv("SMTP_USER", "")).strip()
SMTP_PWD = str(os.getenv("SMTP_PWD", "")).strip()
TO_EMAIL_STR = str(os.getenv("TO_EMAIL", "")).strip()
TO_EMAIL_LIST = [x.strip() for x in TO_EMAIL_STR.split(",") if x.strip()]
GITHUB_TOKEN = str(os.getenv("GITHUB_TOKEN", "")).strip()

# 【关键】完全用英文，移除所有中文
CITIES = {
    "101281901": "Chaozhou",
    "101281601": "Dongguan"
}

def get_gh_actions_remaining():
    if not GITHUB_TOKEN:
        return "GitHub Token not set"
    url = "https://api.github.com/user/settings/billing/actions"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return f"GitHub Actions Remaining: {data['total_minutes_remaining']} min"
    except Exception as e:
        return f"Actions Quota Fetch Failed: {str(e)}"

def estimate_weather_api_remaining():
    daily_calls = len(CITIES) * 3
    monthly_calls = daily_calls * 30
    api_limit = 10000  # Modify to your actual API limit
    remaining = max(0, api_limit - monthly_calls)
    return f"Weather API Remaining (est): {remaining} calls"

def get_weather(city_id):
    if not WEATHER_HOST or not WEATHER_KEY:
        return "API Config Missing"
    url = f"{WEATHER_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data["daily"] if data["code"] == "200" else f"Error Code: {data['code']}"
    except Exception as e:
        return f"API Request Failed: {str(e)}"

def format_weather(city_name, weather_data):
    if isinstance(weather_data, str):
        return f"{city_name}: {weather_data}\n"
    text = f"\n[{city_name} 3-Day Weather]\n"
    # 【关键】只用英文标点，无全角字符
    for day in weather_data:
        text += f"{day['fxDate']}: {day['textDay']}, Temp {day['tempMin']}℃-{day['tempMax']}℃, Wind {day['windDirDay']} {day['windScaleDay']} Level\n"
    return text

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ Email Config Incomplete")
        return

    # 拼接内容，全英文+英文标点
    total_weather = "Daily Weather Forecast (3-Day)\n"
    for cid, cname in CITIES.items():
        total_weather += format_weather(cname, get_weather(cid))
    
    # 额度信息，全英文
    total_weather += "\n" + "="*30 + "\n"
    total_weather += "Quota Status:\n"
    total_weather += f"- {get_gh_actions_remaining()}\n"
    total_weather += f"- {estimate_weather_api_remaining()}\n"
    total_weather += f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    try:
        # Base64 编码，彻底绕开字符编码
        content_bytes = total_weather.encode('utf-8')
        content_b64 = base64.b64encode(content_bytes).decode('ascii')
        msg_content = base64.b64decode(content_b64).decode('utf-8')
        
        msg = MIMEText(msg_content, 'plain', 'utf-8')
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
        print("❌ Email Login Failed, Check SMTP_PWD")
    except Exception as e:
        print(f"❌ Send Failed: {str(e)}")

def main():
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🔍 First Run, Trigger Manually...")
    send_weather_email()
    # main()
