# -*- coding: utf-8 -*-
import sys
import base64
import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText

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

# 城市配置（纯英文标点）
CITIES = {
    "101281901": "Chaozhou",
    "101281601": "Dongguan"
}

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

    # 拼接内容（纯英文+英文标点）
    total_weather = "Daily Weather Forecast (3-Day)\n"
    for cid, cname in CITIES.items():
        total_weather += format_weather(cname, get_weather(cid))

    try:
        # Base64 编码内容，彻底绕开字符编码
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
