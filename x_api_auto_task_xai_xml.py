# -*- coding: utf-8 -*-
"""
x_api_auto_task_xai_xml.py  v7.10 (出海搞钱版 - 降维反风控特化版)
Architecture: Whales/IndieHackers/Global Track -> Key Pool -> XML Parsing -> Clean UI
"""

import os
import re
import json
import time
import base64
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from requests.exceptions import ConnectionError, Timeout

# 🚨 引入官方 xAI SDK
from xai_sdk import Client
from xai_sdk.chat import user, system

TEST_MODE = os.getenv("TEST_MODE_ENV", "false").lower() == "true"

# ── 环境变量 ──────────────────────────────
JIJYUN_WEBHOOK_URL  = os.getenv("JIJYUN_WEBHOOK_URL", "")
SF_API_KEY          = os.getenv("SF_API_KEY", "")
XAI_API_KEY         = os.getenv("XAI_API_KEY", "")    
IMGBB_API_KEY       = os.getenv("IMGBB_API_KEY", "") 

# 🚨 动态密钥池装载机制
TWT_KEYS = []
for i in range(1, 10):
    k = os.getenv(f"TWTAPI_KEY_{i}")
    if k and k.strip(): TWT_KEYS.append(k.strip())

legacy_key = os.getenv("TWTAPI_KEY", "")
if legacy_key and legacy_key.strip() and legacy_key not in TWT_KEYS:
    TWT_KEYS.append(legacy_key.strip())

def get_random_twt_key():
    if not TWT_KEYS: return ""
    return random.choice(TWT_KEYS)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚨 RapidAPI 接口配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAPIDAPI_HOST = "twitter241.p.rapidapi.com"
SEARCH_PATH   = "/search-v2" 
URL_TWTAPI    = "https://" + RAPIDAPI_HOST + SEARCH_PATH
COMMENTS_PATH = "/comments-v2"
URL_COMMENTS  = "https://" + RAPIDAPI_HOST + COMMENTS_PATH

def D(b64_str):
    return base64.b64decode(b64_str).decode("utf-8")

URL_SF_IMAGE   = D("aHR0cHM6Ly9hcGkuc2lsaWNvbmZsb3cuY24vdjEvaW1hZ2VzL2dlbmVyYXRpb25z")
URL_IMGBB      = D("aHR0cHM6Ly9hcGkuaW1nYmIuY29tLzEvdXBsb2Fk")

# ── 巨鲸池 (10人)：流量巨大、容易霸屏的大V与媒体
WHALE_ACCOUNTS = [
    "kaifulee", "Fenng", "lidangzzz", "livid", "tualatrix", 
    "nishuang", "tinyfool", "evilcos", "jiqizhixin", "geekpark"
]

# ── 专家池 (70人)：硬核出海开发者、SaaS创始人、知识博主
EXPERT_ACCOUNTS = [
    "dotey", "op7418", "Gorden_Sun", "xiaohu", "shao__meng", "thinkingjimmy", "vista8", "lijigang", "WaytoAGI", "oran_ge", "AlchainHust", "haibun",
    "SamuelQZQ", "elliotchen100", "berryxia", "lxfater", "turingou", "virushuo", "fankaishuoai", "XDash", "idoubicc", "Cydiar404", "JefferyTatsuya",
    "CoderJeffLee", "tuturetom", "iamtonyzhu", "Valley101_Qi", "AIMindCo", "AlanChenFun", "AuroraAIDev", "maboroshii", "nicekateyes", "paborobot", "porkybun", "0xDragonMaster", "LittleStar",
    "luinlee", "seclink", "XiaohuiAI666", "gefei55", "AI_Jasonyu", "JourneymanChina", "dev_afei", "GoSailGlobal", "chuhaiqu", "daluoseo", "realNyarime", "DigitalNomadLC",
    "RocM301", "shuziyimin", "itangtalk", "guishou_56", "9yearfish", "OwenYoungZh", "waylybaye", "randyloop", "shengxj1", "FinanceYF5", "fkysly", "zhixianio",
    "hongming731", "penny777", "wshuy", "Web3Yolanda", "maboroshi", "CryptoMasterAI", "AIProductDaily", "aigclink", "founder_park", "pingwest"
]

if TEST_MODE:
    WHALE_ACCOUNTS = WHALE_ACCOUNTS[:2]
    EXPERT_ACCOUNTS = EXPERT_ACCOUNTS[:8]

def get_feishu_webhooks() -> list:
    urls = []
    for suffix in ["", "_1", "_2", "_3"]:
        url = os.getenv(f"FEISHU_WEBHOOK_URL{suffix}", "")
        if url: urls.append(url)
    return urls

def get_safe_yesterday() -> str:
    """获取安全的现实世界基准时间，防止环境时空错乱"""
    try:
        time_resp = requests.get("http://worldtimeapi.org/api/timezone/Asia/Shanghai", timeout=5).json()
        real_today = datetime.fromisoformat(time_resp["datetime"])
        return (real_today - timedelta(days=2)).strftime("%Y-%m-%d") # 放宽到2天内，保证有数据
    except:
        return (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")

def parse_twitter_date(date_str):
    try:
        if " " in date_str:
            parts = date_str.split()
            if len(parts) >= 3:
                m_map = {"Jan":"01", "Feb":"02", "Mar":"03", "Apr":"04", "May":"05", "Jun":"06", 
                         "Jul":"07", "Aug":"08", "Sep":"09", "Oct":"10", "Nov":"11", "Dec":"12"}
                mm = m_map.get(parts[1], "01")
                dd = parts[2].zfill(2)
                return f"{mm}{dd}"
    except: pass
    return datetime.now(timezone.utc).strftime("%m%d")

def safe_int(val):
    try:
        if isinstance(val, (int, float)): return int(val)
        v = str(val).lower().replace(',', '')
        if 'k' in v: return int(float(re.search(r'[\d\.]+', v).group()) * 1000)
        if 'm' in v: return int(float(re.search(r'[\d\.]+', v).group()) * 1000000)
        num = re.search(r'\d+', v)
        return int(num.group()) if num else 0
    except:
        return 0

# ==============================================================================
# 🚀 第一阶段：降维反风控抓取引擎
# ==============================================================================
def parse_rapidapi_tweets(data) -> list:
    all_tweets = []
    def recurse(obj):
        if isinstance(obj, dict):
            text = obj.get("full_text") or obj.get("text")
            if not text and obj.get("legacy"): text = obj["legacy"].get("full_text") or obj["legacy"].get("text")
            if text and isinstance(text, str):
                sn = None
                try: sn = obj.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                except: pass
                if not sn: sn = obj.get("screen_name")
                if not sn:
                    u = obj.get("user") or obj.get("author") or obj.get("user_info") or {}
                    sn = u.get("screen_name") or u.get("userName") or u.get("username")
                if not sn and obj.get("legacy"): sn = obj["legacy"].get("screen_name")
                if sn:
                    t_id = obj.get("rest_id") or obj.get("id_str") or obj.get("id") or obj.get("tweet_id")
                    if not t_id and obj.get("legacy"): t_id = obj["legacy"].get("id_str")
                    fav = obj.get("favorite_count") or obj.get("favorites") or obj.get("likes") or 0
                    if not fav and obj.get("legacy"): fav = obj["legacy"].get("favorite_count", 0)
                    rep = obj.get("reply_count") or obj.get("replies") or 0
                    if not rep and obj.get("legacy"): rep = obj["legacy"].get("reply_count", 0)
                    created_at = obj.get("created_at")
                    if not created_at and obj.get("legacy"): created_at = obj["legacy"].get("created_at", "")
                    reply_to = obj.get("in_reply_to_screen_name") or obj.get("reply_to") or obj.get("is_reply")
                    if not reply_to and obj.get("legacy"): reply_to = obj["legacy"].get("in_reply_to_screen_name")
                    if str(t_id):
                        all_tweets.append({
                            "tweet_id": str(t_id), "screen_name": sn, "text": text,
                            "favorites": safe_int(fav), "replies": safe_int(rep), 
                            "created_at": created_at, "reply_to": reply_to,
                        })
                        return 
            for v in obj.values(): recurse(v)
        elif isinstance(obj, list):
            for item in obj: recurse(item)
    recurse(data)
    seen, unique = set(), []
    for t in all_tweets:
        if t["tweet_id"] not in seen:
            seen.add(t["tweet_id"])
            unique.append(t)
    return unique

def fetch_user_tweets(accounts: list, chunk_size: int, label: str) -> list:
    """定向抓取，大幅降低 chunk_size，防止长尾查询算力超载"""
    if not TWT_KEYS: return []
    yesterday = get_safe_yesterday()
    chunks = [accounts[i:i + chunk_size] for i in range(0, len(accounts), chunk_size)]
    all_tweets = []
    consecutive_errors = 0  
    
    for i, chunk in enumerate(chunks, 1):
        if consecutive_errors >= 2: break
        current_key = get_random_twt_key()
        headers = {"x-rapidapi-key": current_key, "x-rapidapi-host": RAPIDAPI_HOST}
        
        print(f"\n⏳ [{label}扫盘] 第 {i}/{len(chunks)} 批 (密钥尾号: ...{current_key[-4:]})...", flush=True)
        query = " OR ".join([f"from:{acc}" for acc in chunk])
        
        # 降维请求：简单查询，防止触发推特并发防御
        params = {"query": f"({query}) since:{yesterday} -is:retweet", "type": "Latest", "count": "20"}
        
        success = False
        for attempt in range(3):
            try:
                resp = requests.get(URL_TWTAPI, headers=headers, params=params, timeout=25)
                if resp.status_code == 200:
                    raw_json = resp.json()
                    tweets = parse_rapidapi_tweets(raw_json)
                    if len(tweets) == 0:
                        print(f"    ⚠️ 此批次无发文，返回游标。", flush=True)
                    all_tweets.extend(tweets)
                    print(f"  ✅ 提取 {len(tweets)} 条。")
                    consecutive_errors = 0 
                    success = True
                    break
                elif resp.status_code in [403, 404]:
                    consecutive_errors += 1
                    time.sleep(2)
                    if consecutive_errors >= 2: break 
                else: 
                    time.sleep(2)
            except Exception as e:
                print(f"  ⚠️ 搜索接口异常: {e}", flush=True)
                time.sleep(2)
        if success: time.sleep(1.5)
        else: time.sleep(3)
    return all_tweets

def fetch_global_hot_tweets() -> list:
    """全网探测引擎，废除高级风控操作符，交由本地 Python 进行点赞提纯"""
    if not TWT_KEYS: return []
    yesterday = get_safe_yesterday()
    all_tweets = []
    print(f"\n📡 [全网探测] 启动降维扫描，锁定出海热点...", flush=True)
    
    # 🚨 破解地雷：去掉了引发风控的 min_faves:30，用最轻量的方式获取基础数据
    grok_queries = [
        f'(出海 OR 独立开发 OR indiehacker OR MRR OR 搞钱) since:{yesterday} -is:retweet'
    ]
    
    for idx, q in enumerate(grok_queries, 1):
        current_key = get_random_twt_key()
        headers = {"x-rapidapi-key": current_key, "x-rapidapi-host": RAPIDAPI_HOST}
        params_discovery = {"query": q, "type": "Top", "count": "40"}
        
        for attempt in range(3):
            try:
                resp = requests.get(URL_TWTAPI, headers=headers, params=params_discovery, timeout=25)
                if resp.status_code == 200:
                    raw_json = resp.json()
                    tweets = parse_rapidapi_tweets(raw_json)
                    all_tweets.extend(tweets)
                    print(f"    ✅ 探测成功，原始捕获 {len(tweets)} 条情报。")
                    break
                elif resp.status_code in [403, 404]: break 
                else: time.sleep(2)
            except Exception as e: time.sleep(2)
        time.sleep(1.5)
    return all_tweets

def fetch_top_comments(tweet_id: str) -> list:
    if not tweet_id or not TWT_KEYS: return []
    current_key = get_random_twt_key()
    headers = {"x-rapidapi-key": current_key, "x-rapidapi-host": RAPIDAPI_HOST}
    try:
        resp = requests.get(URL_COMMENTS, headers=headers, params={"pid": tweet_id, "rankingMode": "Relevance", "count": "20"}, timeout=25)
        if resp.status_code == 200:
            raw_comments = parse_rapidapi_tweets(resp.json())
            return [f"@{c['screen_name']}: {c['text'][:150]}" for c in raw_comments if len(c.get("text", "")) > 10][:5]
    except Exception as e: pass
    return []

# ==============================================================================
# 🚀 第二阶段：纯 XML 提示词与大模型调用
# ==============================================================================
def _build_xml_prompt(combined_jsonl: str, today_str: str) -> str:
    return f"""
你是一位顶级的中文互联网科技/出海领域投资分析师，拥有10年经验。
分析过去24小时内，中文圈AI创业者、出海开发者、独立开发者、SaaS创始人在X上的推文。
过滤掉日常闲聊，提炼出有"创业参考价值"和"出海实操价值"的犀利洞察。

【重要纪律】
1. 只允许输出纯文本内容，严格按照以下 XML 标签结构填入信息。不要缺漏闭合标签。禁止输出 Markdown 符号（如 #, *）。
2. 🚨【动态封面指令】COVER标签的prompt属性中，请务必根据今日最火爆、最核心的出海/开发话题，**自动决定最契合的英文美术风格（例如：Digital Nomad, Vaporwave, Cyberpunk, 3D render, Minimalist Tech等）**，并生成极具视觉冲击力的图生图提示词。
3. 🚨【翻译铁律】TWEET 标签内容必须以中文为主体翻译！严禁直接复制纯英文！保留圈内黑话（如 MRR, PMF, SaaS等）。

【输出结构规范】
<REPORT>
  <COVER title="5-10字中文爆款标题" prompt="100字英文图生图提示词（根据今日内容动态选择最佳画风）" insight="30字内核心洞察，中文"/>
  <PULSE>用一句话总结今日最核心的 1-2 个出海/搞钱动态信号。</PULSE>
  
  <THEMES>
    <THEME type="new" emoji="💰">
      <TITLE>主题标题：副标题</TITLE>
      <NARRATIVE>一句话核心判断，说清楚“什么在变化、为什么重要”（直接输出观点，不带前缀）</NARRATIVE>
      <TWEET account="X账号名" role="中文身份标签">具体行为 + 创业/出海视角解读（中文为主，限60字内）</TWEET>
      <TWEET account="..." role="...">...</TWEET>
      <OUTLOOK>对该现象的深度解读与未来变现展望</OUTLOOK>
      <OPPORTUNITY>具体的出海实操机会、变现路径或搞钱思路</OPPORTUNITY>
      <RISK>踩坑预警：可能面临的失败教训、封号、合规等风险</RISK>
    </THEME>
  </THEMES>

  <MONEY_RADAR>
    <ITEM category="变现快讯">具体的MRR增长、收入数据、被验证的商业模式等。</ITEM>
    <ITEM category="出海渠道">海外市场洞察、流量获取打法、增长黑客手段。</ITEM>
    <ITEM category="工具推荐">被多位开发者提及或强烈推荐的 AI 工具、SaaS、效率神器。</ITEM>
  </MONEY_RADAR>

  <RISK_AND_TRENDS>
    <ITEM category="踩坑预警">平台政策变化、被封禁的风险、开发过程中遇到的技术/运营大坑。</ITEM>
    <ITEM category="趋势判断">未来 1-3 个月的独立开发或出海赛道趋势。</ITEM>
  </RISK_AND_TRENDS>

  <TOP_PICKS>
    <TWEET account="..." role="...">实操价值最大或点赞极高的原味金句（中文精译）</TWEET>
  </TOP_PICKS>
</REPORT>

# 原始数据输入 (JSONL):
{combined_jsonl}
# 日期: {today_str}
"""

def llm_call_xai(combined_jsonl: str, today_str: str) -> str:
    api_key = XAI_API_KEY.strip()
    if not api_key: return ""
    prompt = _build_xml_prompt(combined_jsonl[:100000], today_str)
    model_name = "grok-4.20-beta-latest-non-reasoning" 
    client = Client(api_key=api_key)
    for attempt in range(1, 4):
        try:
            chat = client.chat.create(model=model_name)
            chat.append(system("You are a professional analytical bot. You strictly output in XML format as instructed. Do not ignore the translation rules."))
            chat.append(user(prompt))
            result = chat.sample().content.strip()
            print(f"[LLM/xAI] OK Response received ({len(result)} chars)", flush=True)
            return result
        except Exception as e: time.sleep(2 ** attempt)
    return ""

def parse_llm_xml(xml_text: str) -> dict:
    data = {"cover": {"title": "", "prompt": "", "insight": ""}, "pulse": "", "themes": [], "money_radar": [], "risk_and_trends": [], "top_picks": []}
    if not xml_text: return data

    cover_match = re.search(r'<COVER\s+title=[\'"“”](.*?)[\'"“”]\s+prompt=[\'"“”](.*?)[\'"“”]\s+insight=[\'"“”](.*?)[\'"“”]\s*/?>', xml_text, re.IGNORECASE | re.DOTALL)
    if not cover_match:
        cover_match = re.search(r'<COVER\s+title="(.*?)"\s+prompt="(.*?)"\s+insight="(.*?)"\s*/?>', xml_text, re.IGNORECASE | re.DOTALL)
    if cover_match: 
        data["cover"] = {"title": cover_match.group(1).strip(), "prompt": cover_match.group(2).strip(), "insight": cover_match.group(3).strip()}
        
    pulse_match = re.search(r'<PULSE>(.*?)</PULSE>', xml_text, re.IGNORECASE | re.DOTALL)
    if pulse_match: data["pulse"] = pulse_match.group(1).strip()
        
    for theme_match in re.finditer(r'<THEME([^>]*)>(.*?)</THEME>', xml_text, re.IGNORECASE | re.DOTALL):
        attrs = theme_match.group(1)
        theme_body = theme_match.group(2)
        
        emoji_m = re.search(r'emoji\s*=\s*[\'"“”](.*?)[\'"“”]', attrs, re.IGNORECASE)
        emoji = emoji_m.group(1).strip() if emoji_m else "💡"
        
        t_tag = re.search(r'<TITLE>(.*?)</TITLE>', theme_body, re.IGNORECASE | re.DOTALL)
        theme_title = t_tag.group(1).strip() if t_tag else ""
        
        narrative_match = re.search(r'<NARRATIVE>(.*?)</NARRATIVE>', theme_body, re.IGNORECASE | re.DOTALL)
        narrative = narrative_match.group(1).strip() if narrative_match else ""
        
        tweets = []
        for t_match in re.finditer(r'<TWEET\s+account=[\'"“”](.*?)[\'"“”]\s+role=[\'"“”](.*?)[\'"“”]>(.*?)</TWEET>', theme_body, re.IGNORECASE | re.DOTALL):
            tweets.append({"account": t_match.group(1).strip(), "role": t_match.group(2).strip(), "content": t_match.group(3).strip()})
        if not tweets:
            for t_match in re.finditer(r'<TWEET\s+account="(.*?)"\s+role="(.*?)">(.*?)</TWEET>', theme_body, re.IGNORECASE | re.DOTALL):
                tweets.append({"account": t_match.group(1).strip(), "role": t_match.group(2).strip(), "content": t_match.group(3).strip()})
        
        out_match = re.search(r'<OUTLOOK>(.*?)</OUTLOOK>', theme_body, re.IGNORECASE | re.DOTALL)
        outlook = out_match.group(1).strip() if out_match else ""
        opp_match = re.search(r'<OPPORTUNITY>(.*?)</OPPORTUNITY>', theme_body, re.IGNORECASE | re.DOTALL)
        opportunity = opp_match.group(1).strip() if opp_match else ""
        risk_match = re.search(r'<RISK>(.*?)</RISK>', theme_body, re.IGNORECASE | re.DOTALL)
        risk = risk_match.group(1).strip() if risk_match else ""
        
        data["themes"].append({
            "emoji": emoji, "title": theme_title, "narrative": narrative, "tweets": tweets,
            "outlook": outlook, "opportunity": opportunity, "risk": risk
        })
        
    def extract_items(tag_name, target_list):
        block_match = re.search(rf'<{tag_name}>(.*?)</{tag_name}>', xml_text, re.IGNORECASE | re.DOTALL)
        if block_match:
            for item in re.finditer(r'<ITEM\s+category=[\'"“”](.*?)[\'"“”]>(.*?)</ITEM>', block_match.group(1), re.IGNORECASE | re.DOTALL):
                target_list.append({"category": item.group(1).strip(), "content": item.group(2).strip()})

    extract_items("MONEY_RADAR", data["money_radar"])
    extract_items("RISK_AND_TRENDS", data["risk_and_trends"])

    picks_match = re.search(r'<TOP_PICKS>(.*?)</TOP_PICKS>', xml_text, re.IGNORECASE | re.DOTALL)
    if picks_match:
        for t_match in re.finditer(r'<TWEET\s+account=[\'"“”](.*?)[\'"“”]\s+role=[\'"“”](.*?)[\'"“”]>(.*?)</TWEET>', picks_match.group(1), re.IGNORECASE | re.DOTALL):
            data["top_picks"].append({"account": t_match.group(1).strip(), "role": t_match.group(2).strip(), "content": t_match.group(3).strip()})
            
    return data

# ==============================================================================
# 🚀 第三阶段：结构化渲染引擎
# ==============================================================================
def render_feishu_card(parsed_data: dict, today_str: str):
    webhooks = get_feishu_webhooks()
    if not webhooks or not parsed_data.get("pulse"): return

    elements = []
    elements.append({"tag": "markdown", "content": f"**▌ ⚡️ 今日看板 (The Pulse)**\n<font color='grey'>{parsed_data['pulse']}</font>"})
    elements.append({"tag": "hr"})

    if parsed_data["themes"]:
        elements.append({"tag": "markdown", "content": "**▌ 🧠 深度叙事追踪**"})
        for idx, theme in enumerate(parsed_data["themes"]):
            theme_md = f"**{theme['emoji']} {theme['title']}**\n"
            theme_md += f"<font color='grey'>💡 核心判断：{theme['narrative']}</font>\n"
            
            for t in theme["tweets"]:
                theme_md += f"🗣️ **@{t['account']} | {t['role']}**\n<font color='grey'>“{t['content']}”</font>\n"
            
            if theme.get("outlook"): theme_md += f"<font color='blue'>**🔭 深度展望：**</font> {theme['outlook']}\n"
            if theme.get("opportunity"): theme_md += f"<font color='green'>**🎯 潜在机会：**</font> {theme['opportunity']}\n"
            if theme.get("risk"): theme_md += f"<font color='red'>**⚠️ 踩坑预警：**</font> {theme['risk']}\n"
            
            elements.append({"tag": "markdown", "content": theme_md.strip()})
            if idx < len(parsed_data["themes"]) - 1: elements.append({"tag": "hr"})
        elements.append({"tag": "hr"})

    def add_list_section(title, icon, items):
        if not items: return
        content = f"**▌ {icon} {title}**\n\n"
        for item in items:
            content += f"👉 **{item['category']}**：<font color='grey'>{item['content']}</font>\n"
        elements.append({"tag": "markdown", "content": content.strip()})
        elements.append({"tag": "hr"})

    add_list_section("搞钱雷达 (Money Radar)", "💰", parsed_data["money_radar"])
    add_list_section("风险与趋势 (Risk & Trends)", "📊", parsed_data["risk_and_trends"])

    if parsed_data["top_picks"]:
        picks_md = "**▌ 📣 今日精选推文 (Top 5 Picks)**\n"
        for t in parsed_data["top_picks"]:
            picks_md += f"\n🗣️ **@{t['account']} | {t['role']}**\n<font color='grey'>\"{t['content']}\"</font>\n"
        elements.append({"tag": "markdown", "content": picks_md.strip()})

    card_payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "header": {"title": {"content": f"出海搞钱的中国人都在聊啥 | {today_str}", "tag": "plain_text"}, "template": "orange"},
            "elements": elements + [{"tag": "note", "elements": [{"tag": "plain_text", "content": "Powered by RapidAPI Key-Pool + xai-sdk"}]}]
        }
    }

    for url in webhooks:
        try:
            requests.post(url, json=card_payload, timeout=20)
            print(f"[Push/Feishu] OK Card sent...", flush=True)
        except Exception as e: print(f"[Push/Feishu] ERROR: {e}", flush=True)

def render_wechat_html(parsed_data: dict, cover_url: str = "") -> str:
    html_lines = []
    if cover_url: html_lines.append(f'<p style="text-align:center;margin:0 0 16px 0;"><img src="{cover_url}" style="max-width:100%;border-radius:8px;" /></p>')
    if parsed_data["cover"].get("insight"):
        html_lines.append(f'<div style="border-radius:8px;background:#FFF7E6;padding:12px 14px;margin:0 0 20px 0;color:#d97706;"><div style="font-weight:bold;margin-bottom:6px;">💡 Insight | 核心洞察</div><div>{parsed_data["cover"]["insight"]}</div></div>')

    def make_h3(title): return f'<h3 style="margin:24px 0 12px 0;font-size:18px;border-left:4px solid #f97316;padding-left:10px;color:#2c3e50;font-weight:bold;">{title}</h3>'
    def make_quote(content): return f'<div style="background:#f8f9fa;border-left:4px solid #8c98a4;padding:10px 14px;color:#555;font-size:15px;border-radius:0 4px 4px 0;margin:6px 0 10px 0;line-height:1.6;">{content}</div>'

    html_lines.append(make_h3("⚡️ 今日看板 (The Pulse)"))
    html_lines.append(make_quote(parsed_data.get('pulse', '')))

    if parsed_data["themes"]:
        html_lines.append(make_h3("🧠 深度叙事追踪"))
        for idx, theme in enumerate(parsed_data["themes"]):
            html_lines.append(f'<p style="font-weight:bold;font-size:16px;color:#1e293b;margin:16px 0 8px 0;">{theme["emoji"]} {theme["title"]}</p>')
            html_lines.append(f'<div style="background:#fff7ed; padding:10px 12px; border-radius:6px; margin:0 0 8px 0; font-size:14px; color:#c2410c;"><strong>💡 核心判断：</strong>{theme["narrative"]}</div>')
                
            for t in theme["tweets"]:
                html_lines.append(f'<p style="margin:8px 0 2px 0;font-size:14px;font-weight:bold;color:#2c3e50;">🗣️ @{t["account"]} <span style="color:#94a3b8;font-weight:normal;">| {t["role"]}</span></p>')
                html_lines.append(make_quote(f'"{t["content"]}"'))
            
            if theme.get("outlook"): html_lines.append(f'<p style="margin:6px 0; font-size:15px; line-height:1.6; background:#eef2ff; padding: 8px 12px; border-radius: 4px;"><strong style="color:#4f46e5;">🔭 深度展望：</strong>{theme["outlook"]}</p>')
            if theme.get("opportunity"): html_lines.append(f'<p style="margin:6px 0; font-size:15px; line-height:1.6; background:#f0fdf4; padding: 8px 12px; border-radius: 4px;"><strong style="color:#16a34a;">🎯 潜在机会：</strong>{theme["opportunity"]}</p>')
            if theme.get("risk"): html_lines.append(f'<p style="margin:6px 0; font-size:15px; line-height:1.6; background:#fef2f2; padding: 8px 12px; border-radius: 4px;"><strong style="color:#dc2626;">⚠️ 踩坑预警：</strong>{theme["risk"]}</p>')
            
            if idx < len(parsed_data["themes"]) - 1:
                html_lines.append('<hr style="border:none;border-top:1px dashed #cbd5e1;margin:24px 0;"/>')

    def make_list_section(title, items):
        if not items: return
        html_lines.append(make_h3(title))
        for item in items:
            html_lines.append(f'<p style="margin:10px 0;font-size:15px;line-height:1.6;">👉 <strong style="color:#2c3e50;">{item["category"]}：</strong><span style="color:#333;">{item["content"]}</span></p>')

    make_list_section("💰 搞钱雷达 (Money Radar)", parsed_data["money_radar"])
    make_list_section("📊 风险与趋势 (Risk & Trends)", parsed_data["risk_and_trends"])

    if parsed_data["top_picks"]:
        html_lines.append(make_h3("📣 今日精选推文 (Top 5 Picks)"))
        for t in parsed_data["top_picks"]:
             html_lines.append(f'<p style="margin:12px 0 4px 0;font-size:14px;font-weight:bold;color:#2c3e50;">🗣️ @{t["account"]} <span style="color:#94a3b8;font-weight:normal;">| {t["role"]}</span></p>')
             html_lines.append(make_quote(f'"{t["content"]}"'))

    return "<br/>".join(html_lines)


# ==============================================================================
# 附加工具 (生图、图床与推送)
# ==============================================================================
def generate_cover_image(prompt):
    if not SF_API_KEY or not prompt: return ""
    try:
        resp = requests.post(URL_SF_IMAGE, headers={"Authorization": f"Bearer {SF_API_KEY}", "Content-Type": "application/json"}, json={"model": "black-forest-labs/FLUX.1-schnell", "prompt": prompt, "n": 1, "image_size": "1024x576"}, timeout=60)
        if resp.status_code == 200: return resp.json().get("images", [{}])[0].get("url") or resp.json().get("data", [{}])[0].get("url")
    except Exception as e: print(f"  ⚠️ 生成封面警告: {e}", flush=True)
    return ""

def upload_to_imgbb_via_url(sf_url):
    if not IMGBB_API_KEY or not sf_url: return sf_url 
    try:
        img_resp = requests.get(sf_url, timeout=30)
        img_b64 = base64.b64encode(img_resp.content).decode("utf-8")
        upload_resp = requests.post(URL_IMGBB, data={"key": IMGBB_API_KEY, "image": img_b64}, timeout=45)
        if upload_resp.status_code == 200: return upload_resp.json()["data"]["url"]
    except Exception as e: print(f"  ⚠️ 图床上传警告: {e}", flush=True)
    return sf_url

def push_to_jijyun(html_content, title, cover_url=""):
    if not JIJYUN_WEBHOOK_URL: return
    try: 
        requests.post(JIJYUN_WEBHOOK_URL, json={"title": title, "author": "Prinski", "html_content": html_content, "cover_jpg": cover_url}, timeout=30)
        print(f"[Push/WeChat] OK Sent to Jijyun", flush=True)
    except Exception as e: print(f"  ⚠️ 推送机语警告: {e}", flush=True)

def save_daily_data(today_str: str, post_objects: list, report_text: str):
    data_dir = Path(f"data/{today_str}")
    data_dir.mkdir(parents=True, exist_ok=True)
    combined_txt = "\n".join(json.dumps(obj, ensure_ascii=False) for obj in post_objects)
    (data_dir / "combined.txt").write_text(combined_txt, encoding="utf-8")
    if report_text: (data_dir / "daily_report.txt").write_text(report_text, encoding="utf-8")

def main():
    print("=" * 60, flush=True)
    mode_str = "测试模式" if TEST_MODE else "全量模式"
    print(f"出海搞钱的中国人都在聊啥 v7.10 (降维反风控特化版 - {mode_str})", flush=True)
    print("=" * 60, flush=True)
    print(f"🔑 成功装载 {len(TWT_KEYS)} 把 RapidAPI 密钥，准备进入轮换并发", flush=True)

    today_str, _ = get_dates()
    all_raw_tweets = []
    
    # 🚨 第 1 步：巨鲸池（10人）- 每次只查 2 个，防超时
    all_raw_tweets.extend(fetch_user_tweets(WHALE_ACCOUNTS, chunk_size=2, label="巨鲸"))
    
    # 🚨 第 2 步：专家池（70人）- 每次查 3 个，化整为零
    all_raw_tweets.extend(fetch_user_tweets(EXPERT_ACCOUNTS, chunk_size=3, label="专家"))
    
    # 🚨 第 3 步：全网独立开发/搞钱热点扫描
    all_raw_tweets.extend(fetch_global_hot_tweets())
    
    if not all_raw_tweets:
        print("⚠️ 未能抓取推文，使用测试数据跳过...", flush=True)
        all_raw_tweets = [{"screen_name": "livid", "text": "刚刚部署了一个新版本的后端，速度快了三倍。", "favorites": 100, "created_at": "0101", "replies": 5}]
        
    all_posts_flat = []
    for t in all_raw_tweets:
        likes = t.get("favorites", 0)
        is_reply = bool(t.get("reply_to"))
        # 本地 Python 点赞提纯！不再依赖 API 端的 min_faves，彻底绕过风控
        if not is_reply and likes >= 5: 
            all_posts_flat.append({
                "a": t.get("screen_name", "Unknown"), 
                "tweet_id": t.get("tweet_id", ""),
                "l": likes, 
                "r": t.get("replies", 0),
                "t": parse_twitter_date(t.get("created_at", "")), 
                "s": re.sub(r'https?://\S+', '', t.get("text", "")).strip()[:600], 
                "qt": t.get("quote_text", "")[:200]
            })

    # 【三池配额、流量平权】
    all_posts_flat.sort(key=lambda x: x["l"], reverse=True)
    
    lower_whales = set(a.lower() for a in WHALE_ACCOUNTS)
    lower_experts = set(a.lower() for a in EXPERT_ACCOUNTS)
    
    whale_feed, expert_feed, global_feed = [], [], []
    account_counts = {}
    
    for t in all_posts_flat:
        if len(t.get("s", "")) <= 20: continue
        author = t.get("a", "Unknown").lower()
        if account_counts.get(author, 0) >= 3: continue
            
        account_counts[author] = account_counts.get(author, 0) + 1
        
        # 🚨 核心分流
        if author in lower_whales:
            whale_feed.append(t)
        elif author in lower_experts:
            expert_feed.append(t)
        else:
            global_feed.append(t)

    # 🚨 强制配额：巨鲸10条，搞钱专家50条，全网出海热点15条
    final_feed = whale_feed[:10] + expert_feed[:50] + global_feed[:15]

    top_3_tweets = [t for t in final_feed if t.get("tweet_id")][:3]
    print(f"\n[深挖] 锁定今日最具争议的 {len(top_3_tweets)} 大话题，开始抓取评论区...")
    for t in top_3_tweets:
        comments = fetch_top_comments(t["tweet_id"])
        if comments: t["hot_comments"] = comments 

    combined_jsonl = "\n".join(json.dumps(obj, ensure_ascii=False) for obj in final_feed)
    print(f"\n[Data] 组装完成：{len(final_feed)} 条推文 ready for LLM.")

    if combined_jsonl.strip():
        xml_result = llm_call_xai(combined_jsonl, today_str)
        if xml_result:
            print("\n[Parser] Parsing XML to structured data...", flush=True)
            parsed_data = parse_llm_xml(xml_result)
            
            cover_url = ""
            if parsed_data["cover"]["prompt"]:
                sf_url = generate_cover_image(parsed_data["cover"]["prompt"])
                cover_url = upload_to_imgbb_via_url(sf_url) if sf_url else ""
            
            render_feishu_card(parsed_data, today_str)
                
            if JIJYUN_WEBHOOK_URL:
                html_content = render_wechat_html(parsed_data, cover_url)
                wechat_title = parsed_data["cover"]["title"] or f"出海搞钱的中国人 | {today_str}"
                push_to_jijyun(html_content, title=wechat_title, cover_url=cover_url)
                
            save_daily_data(today_str, final_feed, xml_result)
            print("\n🎉 V7.10 运行完毕！", flush=True)
        else:
            print("❌ LLM 处理失败，任务终止。")

if __name__ == "__main__":
    main()
