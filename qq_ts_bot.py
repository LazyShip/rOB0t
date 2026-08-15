import socket
import re
import time
import json
import urllib.request
from flask import Flask, request, jsonify
import logging

# 屏蔽 Flask 默认的访问日志
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# ==================== 配置区域 ====================
BOT_QQ =                              #  QQ
TS_API_KEY = ""  # TS ClientQuery API Key
LISTEN_PORT =                               # 本地端口
NAPCAT_API_URL = ""        # NapCat HTTP 接口
TRIGGER_WORDS = ["ts"] #触发词
# =================================================

def send_local_cmd(sock, cmd):
    sock.sendall((cmd + "\n").encode('utf-8'))
    response = ""
    while True:
        data = sock.recv(4096).decode('utf-8', errors='ignore')
        response += data
        if "error id=" in data:
            break
    return response

def parse_val(text, key):
    match = re.search(rf"{key}=([^\s]+)", text)
    if match:
        val = match.group(1)
        val = val.replace(r"\s", " ").replace(r"\/", "/").replace(r"\p", "|")
        return val
    return None

def get_ts_info():
    """获取 TS3 在线玩家列表，状态）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("127.0.0.1", 25639))
        time.sleep(0.1)
        sock.recv(4096)

        auth_res = send_local_cmd(sock, f"auth apikey={TS_API_KEY}")
        if "error id=0" not in auth_res:
            sock.close()
            return None, "TS 认证失败，请检查 API Key"

        send_local_cmd(sock, "use current")
        #抓取到麦克风和耳机的状态
        res = send_local_cmd(sock, "clientlist -voice")
        whoami_res = send_local_cmd(sock, "whoami")
        my_name = parse_val(whoami_res, "client_nickname")

        if "error id=0" in res:
            clients = res.split("|")
            real_players = []
            for c in clients:
                c_type = parse_val(c, "client_type")
                name = parse_val(c, "client_nickname")
                
                # 提取麦克风和耳机状态
                input_muted = parse_val(c, "client_input_muted")
                output_muted = parse_val(c, "client_output_muted")

                if c_type == "0" and name and name != my_name:
                    status_tags = []
                    # 判断状态并打上小尾巴标签
                    if output_muted == "1":
                        status_tags.append("🔇拒听")
                    elif input_muted == "1":
                        status_tags.append("🎙️闭麦")
                    
                    status_str = f" [{' '.join(status_tags)}]" if status_tags else ""
                    real_players.append(f"{name}{status_str}")
            
            send_local_cmd(sock, "quit")
            sock.close()
            return real_players, ""
        else:
            send_local_cmd(sock, "quit")
            sock.close()
            return None, "TS 列表读取异常"
    except Exception as e:
        return None, f"连接本地 TS 客户端失败 ({e})"

def send_qq_group_msg(group_id, message):
    """向 QQ 群发送消息"""
    url = f"{NAPCAT_API_URL}/send_group_msg"
    payload = json.dumps({
        "group_id": int(group_id),
        "message": message
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"  [>] ✅ 已成功向群 [{group_id}] 推送名单！")
    except Exception as e:
        print(f"  [X] ❌ 发送群消息失败: {e}")

@app.route('/', methods=['POST'])
def handle_qq_event():
    event = request.get_json(silent=True) or {}
    post_type = event.get("post_type", "")

    # 群消息
    if post_type != "message" or event.get("message_type") != "group":
        return jsonify({"status": "ok"})

    group_id = event.get("group_id")
    raw_msg = str(event.get("raw_message", "")).strip()
    sender = event.get("sender", {}).get("nickname", "群友")
    self_id = str(event.get("self_id", BOT_QQ))

    # 1.判断：艾特机器人
    is_at_bot = False
    at_cq_code = f"[CQ:at,qq={self_id}]"
    
    if at_cq_code in raw_msg:
        is_at_bot = True
    elif isinstance(event.get("message"), list):
        for seg in event.get("message"):
            if seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == self_id:
                is_at_bot = True
                break

    if not is_at_bot:
        return jsonify({"status": "ok"})

    # 2. 提取文本内容
    clean_msg = re.sub(r'\[CQ:[^\]]+\]', '', raw_msg).strip().lower()

    # 3. 逻辑判断：艾特文字包含了触发词执行查询
    if clean_msg != "" and any(w in clean_msg for w in TRIGGER_WORDS):
        print(f"\n🎯 收到指令！群 [{group_id}] {sender} @了机器人，内容: '{clean_msg}'")
        print("  [*] 正在抓取 TS 在线名单及状态...")
        
        players, err = get_ts_info()
        if players is None:
            reply = f"⚠️ TS 查询失败: {err}"
        elif len(players) == 0:
            reply = "📢 当前 TS 服务器暂无其他在线人员。"
        else:
            player_list_str = "\n".join([f"  {i+1}. {name}" for i, name in enumerate(players)])
            reply = f"🎮 当前 TS 在线人数: {len(players)} 人\n{player_list_str}"

        send_qq_group_msg(group_id, reply)
    else:
        # 如果只艾特机器人但没触发词，终端打印不回复
        print(f"\n👻 群 [{group_id}] {sender} @了机器人，但没有带有效指令: '{clean_msg}'，已忽略。")

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("=" * 55)
    print("懒羊羊 TS QQ 机器人（启动！)")
    print(f"📌 绑定机器人 QQ: {BOT_QQ}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=LISTEN_PORT, threaded=True)
