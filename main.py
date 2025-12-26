import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from email.header import Header

# 所有配置全部从环境变量读取，无任何硬编码
WEATHER_KEY = os.getenv("WEATHER_KEY", "")
SMTP_USER = os.getenv("SMTP_USER", "")  # Foxmail邮箱：xiaolin0108_2025@foxmail.com
SMTP_PWD = os.getenv("SMTP_PWD", "")    # Foxmail授权码：mchysbphpkpxbacg
WEATHER_HOST = os.getenv("WEATHER_HOST", "")  # API Host环境变量，必填
TO_EMAIL_STR = os.getenv("TO_EMAIL", "")
TO_EMAIL_LIST = [email.strip() for email in TO_EMAIL_STR.split(",") if email.strip()]

# 城市配置（如需动态修改也可改成环境变量）
CITIES = {
    "101281901": "潮州",
    "101281601": "东莞"
}

def get_weather(city_id):
    """获取今明后三天天气数据，API Host完全来自环境变量"""
    # 先校验API Host和KEY是否配置
    if not WEATHER_HOST:
        return "❌ API Host未配置，请在Secrets中设置WEATHER_HOST"
    if not WEATHER_KEY:
        return "❌ API KEY未配置，请在Secrets中设置WEATHER_KEY"
    
    # 拼接URL，完全依赖环境变量
    url = f"{WEATHER_HOST}/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["code"] != "200":
            return f"获取天气失败，错误码：{data['code']}"
        return data["daily"]
    except requests.exceptions.Timeout:
        return "API请求超时，请检查网络或服务状态"
    except requests.exceptions.RequestException as e:
        return f"API请求异常：{str(e)}"
    except Exception as e:
        return f"未知错误：{str(e)}"

def format_weather(city_name, weather_data):
    """格式化天气信息"""
    if isinstance(weather_data, str):
        return f"{city_name}天气获取失败：{weather_data}\n"

    weather_text = f"\n【{city_name}今明后三天天气】\n"
    for day in weather_data:
        date = day["fxDate"]
        temp = f"{day['tempMin']}℃-{day['tempMax']}℃"
        weather = day["textDay"]
        wind = f"{day['windDirDay']}{day['windScaleDay']}级"
        weather_text += f"{date}：{weather}，气温{temp}，风向{wind}\n"
    return weather_text

def send_weather_email():
    """发送邮件，适配Foxmail/QQ邮箱"""
    if not (SMTP_USER and SMTP_PWD):
        print("❌ 邮箱配置不完整，请检查SMTP_USER和SMTP_PWD")
        return
    if not TO_EMAIL_LIST:
        print("❌ 接收邮箱未配置，请检查TO_EMAIL")
        return

    total_weather = "📅 今日天气预报（今明后三天）\n"
    for city_id, city_name in CITIES.items():
        weather_data = get_weather(city_id)
        total_weather += format_weather(city_name, weather_data)

    try:
        msg = MIMEText(total_weather, "plain", "utf-8")
        msg["From"] = Header(f"天气预报<{SMTP_USER}>", "utf-8")
        msg["Subject"] = Header("每日天气预报（今明后三天）", "utf-8")

        # Foxmail SMTP配置
        with smtplib.SMTP("smtp.qq.com", 587, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PWD)
            for to_email in TO_EMAIL_LIST:
                msg["To"] = Header(to_email, "utf-8")
                server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"✅ 已成功向{len(TO_EMAIL_LIST)}个邮箱推送天气预报")
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮箱登录失败，请检查账号或授权码")
    except smtplib.SMTPException as e:
        print(f"❌ 邮件发送失败：{str(e)}")
    except Exception as e:
        print(f"❌ 邮件发送异常：{str(e)}")

def main():
    """定时任务主函数"""
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    print("⏰ 定时推送服务已启动")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🔍 首次运行，手动触发推送...")
    send_weather_email()
    # 注释掉main()，GitHub Actions用yml定时触发，无需本地循环
    # main()
