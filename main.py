import requests
import smtplib
import os
import schedule
import time
from email.mime.text import MIMEText
from email.header import Header

# 从环境变量读取配置，添加默认值避免空值报错
WEATHER_KEY = os.getenv("WEATHER_KEY", "")
SMTP_USER = os.getenv("SMTP_USER", "")  # 你的Gmail邮箱
SMTP_PWD = os.getenv("SMTP_PWD", "")    # Gmail应用专用密码
# 处理邮箱列表，过滤空值避免split报错
TO_EMAIL_STR = os.getenv("TO_EMAIL", "")
TO_EMAIL_LIST = [email.strip() for email in TO_EMAIL_STR.split(",") if email.strip()]

# 配置城市（城市ID可在和风天气平台查询）
CITIES = {
    "101281901": "潮州",  # 潮州城市ID
    "101281601": "东莞"   # 东莞城市ID
}

def get_weather(city_id):
    """获取今明后三天的天气数据（使用专属API Host）"""
    # 修复URL语法错误，补全//并修正域名拼接
    url = f"https://kt487r9hy5.re.qweatherapi.com/v7/weather/3d?location={city_id}&key={WEATHER_KEY}"
    try:
        # 先检查API KEY是否配置
        if not WEATHER_KEY:
            return "API KEY未配置，请在Secrets中设置WEATHER_KEY"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["code"] != "200":
            return f"获取天气失败，错误码：{data['code']}"
        return data["daily"]  # 返回三天的天气数据
    except requests.exceptions.Timeout:
        return "API请求超时，请检查网络或和风天气服务状态"
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
    """发送天气预报邮件（适配Gmail SMTP）"""
    # 前置检查：验证邮箱配置
    if not SMTP_USER or not SMTP_PWD:
        print("❌ Gmail邮箱或密码未配置，请在Secrets中设置SMTP_USER和SMTP_PWD")
        return
    if not TO_EMAIL_LIST:
        print("❌ 接收邮箱未配置，请在Secrets中设置TO_EMAIL")
        return

    # 拼接所有城市的天气信息
    total_weather = "📅 今日天气预报（今明后三天）\n"
    for city_id, city_name in CITIES.items():
        weather_data = get_weather(city_id)
        total_weather += format_weather(city_name, weather_data)

    # 配置邮件内容
    try:
        msg = MIMEText(total_weather, "plain", "utf-8")
        msg["From"] = Header(f"天气预报<{SMTP_USER}>", "utf-8")
        msg["Subject"] = Header("每日天气预报（今明后三天）", "utf-8")

        # 发送邮件到多个接收邮箱
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PWD)
            for to_email in TO_EMAIL_LIST:
                msg["To"] = Header(to_email, "utf-8")
                server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"✅ 已成功向{len(TO_EMAIL_LIST)}个邮箱推送天气预报")
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail登录失败，请检查邮箱或应用专用密码是否正确")
    except smtplib.SMTPException as e:
        print(f"❌ 邮件发送失败：{str(e)}")
    except Exception as e:
        print(f"❌ 邮件发送异常：{str(e)}")

def main():
    """主函数：启动定时任务"""
    # 配置定时任务：每天8点、12点、22点推送
    schedule.every().day.at("08:00").do(send_weather_email)
    schedule.every().day.at("12:00").do(send_weather_email)
    schedule.every().day.at("22:00").do(send_weather_email)
    print("⏰ 天气预报定时推送服务已启动，将在每天8点、12点、22点推送")
    print("ℹ️  按Ctrl+C可停止服务")

    # 持续运行定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次任务

if __name__ == "__main__":
    # 运行时先手动触发一次邮件发送
    print("🔍 首次运行，手动触发一次天气预报推送...")
    send_weather_email()
    # 启动定时任务
    main()
