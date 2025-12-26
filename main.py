# -*- coding: utf-8 -*-
import sys
import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from email import charset

# 强制Python全局编码为UTF-8（终极方案）
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('utf-8')
# 强制邮件模块使用UTF-8，禁用ASCII
charset.add_charset('utf-8', charset.SHORTEST, charset.QP, 'utf-8')

# 环境变量配置
WEATHER_KEY = os.getenv("WEATHER_KEY", "")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PWD = os.getenv("SMTP_PWD", "")
WEATHER_HOST = os.getenv("WEATHER_HOST", "")
TO_EMAIL_STR = os.getenv("TO_EMAIL", "")
TO_EMAIL_LIST = [email.strip() for email in TO_EMAIL_STR.split(",") if email.strip()]

# 城市配置
CITIES = {
    "101281901": "潮州",
    "101281601": "东莞"
}

def get_weather(city_id):
    if not WEATHER_HOST or not WEATHER_KEY:
        return "API配置缺失,请检查Secrets"
    url = f"{WEATHER_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data["daily"] if data["code"] == "200" else f"错误码:{data['code']}"
    except Exception as e:
        return f"API请求失败:{str(e)}"

def format_weather(city_name, weather_data):
    if isinstance(weather_data, str):
        return f"{city_name}:{weather_data}\n"
    # 【重要】全部用英文标点，彻底删除全角逗号、括号
    text = f"\n[{city_name}今明后三天天气]\n"
    for day in weather_data:
        text += f"{day['fxDate']}:{day['textDay']},气温{day['tempMin']}℃-{day['tempMax']}℃,{day['windDirDay']}{day['windScaleDay']}级\n"
    return text

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ 邮箱配置不完整")
        return

    total_weather = "今日天气预报(今明后三天)\n"
    for city_id, city_name in CITIES.items():
        total_weather += format_weather(city_name, get_weather(city_id))

    try:
        # 直接传入UTF-8字节流
        msg = MIMEText(total_weather.encode('utf-8'), 'plain', 'utf-8')
        msg['From'] = SMTP_USER
        msg['Subject'] = "每日天气预报"
        # 发送字节流，跳过字符串编码
        with smtplib.SMTP("smtp.qq.com", 587, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PWD)
            success = 0
            for to_email in TO_EMAIL_LIST:
                msg['To'] = to_email
                server.sendmail(SMTP_USER, to_email, msg.as_bytes())
                success += 1
        print(f"✅ 成功向{success}个邮箱推送")
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮箱登录失败,检查授权码")
    except Exception as e:
        print(f"❌ 发送异常:{str(e)}")

def main():
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🔍 首次运行,手动触发推送...")
    send_weather_email()
    # main()
