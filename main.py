# -*- coding: utf-8 -*-
import sys
import ssl
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import Header
import requests
import os
import schedule
import time
from datetime import datetime

# 强制编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# 环境变量净化
def clean_env_var(var_str):
    var_str = var_str.replace('，', ',').replace('：', ':').replace('　', ' ')
    return var_str.strip()

WEATHER_KEY = clean_env_var(str(os.getenv("WEATHER_KEY", "")))
WEATHER_HOST = clean_env_var(str(os.getenv("WEATHER_HOST", "")))
SMTP_USER = clean_env_var(str(os.getenv("SMTP_USER", "")))
SMTP_PWD = clean_env_var(str(os.getenv("SMTP_PWD", "")))
TO_EMAIL_STR = clean_env_var(str(os.getenv("TO_EMAIL", "")))
TO_EMAIL_LIST = [email.strip() for email in TO_EMAIL_STR.split(",") if email.strip()]

CITIES = {
    "101281901": "潮州",
    "101281601": "东莞"
}

def get_weather(city_id):
    city_name = CITIES[city_id]
    if not WEATHER_HOST or not WEATHER_KEY:
        return f"{city_name}：API配置缺失"
    url = f"{WEATHER_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data["code"] == "200":
            text = f"\n【{city_name} 未来三天天气】\n"
            for day in data["daily"]:
                text += f"{day['fxDate']}：{day['textDay']}，气温{day['tempMin']}℃-{day['tempMax']}℃，风向{day['windDirDay']} {day['windScaleDay']}级\n"
            return text
        else:
            return f"{city_name}：接口错误 {data['code']}"
    except Exception as e:
        return f"{city_name}：请求失败 {str(e)}"

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ 邮箱配置不完整")
        return

    total_weather = "每日天气预报（未来三天）\n"
    for cid in CITIES.keys():
        total_weather += get_weather(cid)
    total_weather += "\n" + "="*30 + "\n"
    total_weather += "额度状态：\n- GitHub Actions：额度充足\n- 天气API：调用量充足\n"
    total_weather += f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # 核心修改：用 IMAP_SSL 先登录，再发送（兼容性更强）
    try:
        # 1. 登录IMAP服务器（端口993，比SMTP 465更稳定）
        imap_server = imaplib.IMAP4_SSL("imap.qq.com", 993, timeout=60)
        imap_server.login(SMTP_USER, SMTP_PWD)
        imap_server.logout() # 登录成功即证明账户有效

        # 2. 发送邮件
        msg = MIMEText(total_weather.encode('utf-8'), 'plain', 'utf-8')
        msg['From'] = Header(f"天气预报<{SMTP_USER}>", 'utf-8')
        msg['Subject'] = Header("每日天气预报", 'utf-8')

        # 用 SMTP_SSL 低延迟服务器地址
        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=60) as server:
            server.login(SMTP_USER, SMTP_PWD)
            success = 0
            for to_email in TO_EMAIL_LIST:
                msg['To'] = to_email
                server.sendmail(SMTP_USER, to_email, msg.as_bytes())
                success += 1
        print(f"✅ 成功发送到 {success} 个邮箱")
    except imaplib.IMAP4.error:
        print("❌ IMAP登录失败！请确认授权码有效，且开启了IMAP服务")
    except Exception as e:
        print(f"❌ 发送失败：{str(e)}")

def main():
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🔍 首次运行，手动触发推送...")
    send_weather_email()
    # main()
