# -*- coding: utf-8 -*-
import sys
import ssl
import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from datetime import datetime

# 强制编码，彻底杜绝ASCII问题
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# 过滤环境变量全角字符
def clean_env_var(var_str):
    var_str = var_str.replace('，', ',').replace('　', ' ').replace('：', ':')
    return var_str.strip()

# 环境变量配置
WEATHER_KEY = clean_env_var(str(os.getenv("WEATHER_KEY", "")))
WEATHER_HOST = clean_env_var(str(os.getenv("WEATHER_HOST", "")))
SMTP_USER = clean_env_var(str(os.getenv("SMTP_USER", "")))
SMTP_PWD = clean_env_var(str(os.getenv("SMTP_PWD", "")))
TO_EMAIL_STR = clean_env_var(str(os.getenv("TO_EMAIL", "")))
TO_EMAIL_LIST = [email.strip() for email in TO_EMAIL_STR.split(",") if email.strip()]
GITHUB_TOKEN = clean_env_var(str(os.getenv("GITHUB_TOKEN", "")))

# 纯英文城市配置
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
    api_limit = 10000
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
    for day in weather_data:
        text += f"{day['fxDate']}: {day['textDay']}, Temp {day['tempMin']}℃-{day['tempMax']}℃, Wind {day['windDirDay']} {day['windScaleDay']} Level\n"
    return text

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ Email Config Incomplete")
        return

    total_weather = "Daily Weather Forecast (3-Day)\n"
    for cid, cname in CITIES.items():
        total_weather += format_weather(cname, get_weather(cid))
    
    total_weather += "\n" + "="*30 + "\n"
    total_weather += "Quota Status:\n"
    total_weather += f"- {get_gh_actions_remaining()}\n"
    total_weather += f"- {estimate_weather_api_remaining()}\n"
    total_weather += f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    try:
        # 终极方案：自定义SSL上下文 + 跳过证书验证 + QQ邮箱标准端口
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        msg = MIMEText(total_weather.encode('utf-8'), 'plain', 'utf-8')
        msg['From'] = SMTP_USER
        msg['Subject'] = "Daily Weather Forecast"

        # QQ邮箱SSL端口：465，超时延长到60秒
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context, timeout=60) as server:
            server.login(SMTP_USER, SMTP_PWD)
            success = 0
            for to_email in TO_EMAIL_LIST:
                msg['To'] = to_email
                server.sendmail(SMTP_USER, to_email, msg.as_string().encode('utf-8'))
                success += 1
        print(f"✅ Sent to {success} email(s)")
    except smtplib.SMTPAuthenticationError:
        print("❌ 核心错误：授权码无效！SMTP_PWD必须是QQ邮箱的第三方授权码，不是登录密码！")
    except smtplib.SMTPConnectError:
        print("❌ 连接失败：检查网络或确认smtp.qq.com:465端口可访问")
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
    api_limit = 10000
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
    for day in weather_data:
        text += f"{day['fxDate']}: {day['textDay']}, Temp {day['tempMin']}℃-{day['tempMax']}℃, Wind {day['windDirDay']} {day['windScaleDay']} Level\n"
    return text

def send_weather_email():
    if not (SMTP_USER and SMTP_PWD and TO_EMAIL_LIST):
        print("❌ Email Config Incomplete")
        return

    total_weather = "Daily Weather Forecast (3-Day)\n"
    for cid, cname in CITIES.items():
        total_weather += format_weather(cname, get_weather(cid))
    
    total_weather += "\n" + "="*30 + "\n"
    total_weather += "Quota Status:\n"
    total_weather += f"- {get_gh_actions_remaining()}\n"
    total_weather += f"- {estimate_weather_api_remaining()}\n"
    total_weather += f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    try:
        # 核心修改：改用 SMTP_SSL + 465 端口，稳定性更高
        msg = MIMEText(total_weather, 'plain', 'utf-8')
        msg['From'] = SMTP_USER
        msg['Subject'] = "Daily Weather Forecast"

        # 启用调试模式（可选，排查问题用）
        # server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30)
        # server.set_debuglevel(1)
        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30) as server:
            server.login(SMTP_USER, SMTP_PWD)
            success = 0
            for to_email in TO_EMAIL_LIST:
                msg['To'] = to_email
                server.sendmail(SMTP_USER, to_email, msg.as_string().encode('utf-8'))
                success += 1
        print(f"✅ Sent to {success} email(s)")
    except smtplib.SMTPAuthenticationError:
        print("❌ Email Login Failed: Check SMTP_PWD (Foxmail授权码，不是登录密码)")
    except smtplib.SMTPConnectError:
        print("❌ SMTP Connection Failed: Check network or smtp.qq.com:465 port")
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
