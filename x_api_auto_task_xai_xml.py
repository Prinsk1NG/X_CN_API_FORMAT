# -*- coding: utf-8 -*-
"""
x_api_auto_task_xai_xml.py  v13.0 (多智能体聚类版: 全网中文热点 + Grok-4.20-Multi-Agent)
Architecture: TwitterAPI.io -> PPLX -> xAI SDK -> Clean UI -> Stats Tracker
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

# 🚨 核心双引擎密钥
TWITTERAPI_IO_KEY   = os.getenv("twitterapi_io_KEY", "")
PPLX_API_KEY        = os.getenv("PPLX_API_KEY", "")

def D(b64_str):
    return base64.b64decode(b64_str).decode("utf-8")

URL_SF_IMAGE   = D("aHR0cHM6Ly9hcGkuc2lsaWNvbmZsb3cuY24vdjEvaW1hZ2VzL2dlbmVyYXRpb25z")
URL_IMGBB      = D("aHR0cHM6Ly9hcGkuaW1nYmIuY29tLzEvdXBsb2Fk")

# ── 巨鲸池 (15人)：流量巨大、容易霸屏的大V与媒体
WHALE_ACCOUNTS = [
    "kaifulee", "Fenng", "lidangzzz", "livid", "tualatrix", 
    "nishuang", "tinyfool", "evilcos", "jiqizhixin", "geekpark",
    "sspai_com", "ruanyf", "foxshuo", "pongba", "Svwang1"
]

# ── 专家池 (90+人)：涵盖各大核心领域的高质量信源
EXPERT_ACCOUNTS = list(set([
    # AI 领域
    "dotey", "op7418", "Gorden_Sun", "xiaohu", "shao__meng", "thinkingjimmy", "goocarlos", 
    "Tumeng05", "AxtonLiu", "haibun", "vista8", "lijigang", "WaytoAGI", "xicilion", 
    "oran_ge", "AlchainHust", "SamuelQZQ", "elliotchen100", "Hayami_kiraa", "berryxia",
    "MANISH1027512", "joshesye", "zstmfhy", "bozhou_ai", "CuiMao", "RookieRicardoR", "wlzh",
    
    # 创业者领域
    "lxfater", "nateleex", "yan5xu", "santiagoyoungus", "Cydiar404", "JefferyTatsuya", 
    "seclink", "turingou", "virushuo", "fankaishuoai", "XDash", "idoubicc", "CoderJeffLee", 
    "tuturetom", "iamtonyzhu", "hongjun60", "Valley101_Qian", "binghe", "yyyole", "0xkakarot888", "rionaifantasy", "Wujizhuzhu",
    
    # SaaS / APP 产品领域
    "indie_maker_fox", "HongyuanCao", "nextify2024", "readyfor2025", "weijunext", "yihui_indie", 
    "JinsFavorites", "xiongchun007", "Junyu", "luoleiorg", "Plidezus", "jesselaunz", "lewangx", 
    "luinlee", "yupi996", "servasyy_ai", "XiaohuiAI666", "dingyi", "yanhua1010",
    
    # 出海与流量领域
    "gefei55", "lyc_zh", "AI_Jasonyu", "JourneymanChina", "dev_afei", "luobogooooo", 
    "GoSailGlobal", "chuhaiqu", "daluoseo", "hezhiyan7", "imaxichuhai", "canghe", "Nicole_yang88",
    
    # 独立开发者领域
    "austinit", "guishou_56", "9yearfish", "benshandebiao", "hwwaanng", "OwenYoungZh", 
    "waylybaye", "randyloop", "shengxj1", "FinanceYF5", "liuyi0922", "fkysly", "zhixianio", "Pluvio9yte",
    "tangjinzhou", "IndieDevHailey", "nopinduoduo",
    
    # OpenClaw 与 Agent
    "abskoop", "stark_nico99", "hongming731", "penny777", "quarktalksss", "Khazix0918", "steipete", "AI_jacksaku",
    
    # 知识分享领域
    "kasong2048", "cellinlab", "wshuyi", "Francis_YAO_", "realNyarime", "DigitalNomadLC", 
    "RocM301", "EvaCmore", "shuziyimin", "itangtalk", "knowledgefxg", "cj3214567667", "MindfulReturn", "Tz_2022", "EvanWritesX", "yaohui12138",
    
    # 副业领域
    "Astronaut_1216", "ityouknows", "expatlevi", "ll777547099", "PandaTalk8", "catmangox", "indiehackercase"
]))

if TEST_MODE:
    WHALE_ACCOUNTS = WHALE_ACCOUNTS[:2]
    EXPERT_ACCOUNTS = EXPERT_ACCOUNTS[:5]

def get_feishu_webhooks() -> list:
    urls = []
    for suffix in ["", "_1", "_2", "_3"]:
        url = os.getenv(f"FEISHU_WEBHOOK_URL{suffix}", "")
        if url: urls.append(url)
    return urls

def get_dates() -> tuple:
    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz)
    yesterday = today - timedelta(days=1)
    return today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")

def get_safe_yesterday() -> str:
    """获取安全的现实世界基准时间"""
    try:
        time_resp = requests.get("http://worldtimeapi.org/api/timezone/Asia/Shanghai", timeout=5).json()
        real_today = datetime.fromisoformat(time_resp["datetime"])
        return (real_today - timedelta(days=2)).strftime("%Y-%m-%d")
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
# 🚀 外部情报检索：Perplexity (客观查数机器人)
# ==============================================================================
def fetch_macro_with_perplexity() -> str:
    """不再限定出海，扩大为科技圈全领域的客观事实补充"""
    if not PPLX_API_KEY: return ""
    print("\n🕵️ [宏观新闻官] 呼叫 Perplexity 获取全网硬核数据...", flush=True)
    try:
        prompt = """你是顶级科技与商业分析师。请检索过去 24 小时内全球科技、AI 或商业领域的【硬核客观数据】。
        🚨 最高指令：不要宽泛的行业趋势，只抓取以下两类具体事实，必须带具体媒体或官方来源：
        1. 💰 具体的重磅融资、并购案、或亮眼的公司财报/收入数据。
        2. 🎁 刚刚发布或突然爆火的科技产品、开源项目、或重要硬件（带具体名字和功能）。
        绝对禁止将 "Perplexity" 作为信息来源。"""
        
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "sonar-pro", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()["choices"][0]["message"]["content"]
            print(f"  ✅ Perplexity 客观数据收集完毕 ({len(data)} 字)", flush=True)
            return data
    except Exception as e: print(f"  ❌ Perplexity 抛出异常: {e}", flush=True)
    return ""

# ==============================================================================
# 🚀 第一阶段：TwitterAPI.io 原生抓取引擎
# ==============================================================================
def parse_tweets_recursive(data) -> list:
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

                t_id = obj.get("rest_id") or obj.get("id_str") or obj.get("id") or obj.get("tweet_id")
                if not t_id and obj.get("legacy"): t_id = obj["legacy"].get("id_str")
                
                fav = obj.get("favorite_count") or obj.get("favorites") or obj.get("likes") or obj.get("like_count") or 0
                if not fav and obj.get("legacy"): fav = obj["legacy"].get("favorite_count", 0)
                
                rep = obj.get("reply_count") or obj.get("replies") or 0
                if not rep and obj.get("legacy"): rep = obj["legacy"].get("reply_count", 0)
                
                created_at = obj.get("created_at")
                if not created_at and obj.get("legacy"): created_at = obj["legacy"].get("created_at", "")
                
                reply_to = obj.get("in_reply_to_screen_name") or obj.get("reply_to") or obj.get("is_reply")
                if not reply_to and obj.get("legacy"): reply_to = obj["legacy"].get("in_reply_to_screen_name")
                
                if str(t_id) and sn:
                    all_tweets.append({
                        "tweet_id": str(t_id), "screen_name": sn, "text": text,
                        "favorites": safe_int(fav), "replies": safe_int(rep), 
                        "created_at": created_at, "reply_to": reply_to,
                    })
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

def fetch_tweets_twitterapi_io(accounts: list, label: str) -> list:
    if not TWITTERAPI_IO_KEY: 
        print(f"⚠️ 未配置 twitterapi_io_KEY，跳过{label}抓取", flush=True)
        return []
    
    yesterday = get_safe_yesterday()
    all_tweets = []
    print(f"\n⏳ [{label}扫盘] 启动 TwitterAPI.io 点对点扫描，共 {len(accounts)} 人...", flush=True)
    headers = {"X-API-Key": TWITTERAPI_IO_KEY}
    url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
    
    chunk_size = 5
    chunks = [accounts[i:i + chunk_size] for i in range(0, len(accounts), chunk_size)]
    
    for i, chunk in enumerate(chunks, 1):
        print(f"  🔎 挖掘第 {i}/{len(chunks)} 批动态...", flush=True)
        query_str = " OR ".join([f"from:{acc}" for acc in chunk])
        query = f"({query_str}) since:{yesterday} -filter:retweets"
        params = {"query": query, "queryType": "Latest"}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=25)
            if resp.status_code == 200:
                tweets = parse_tweets_recursive(resp.json())
                for t in tweets: t["t"] = parse_twitter_date(t.get("created_at", ""))
                all_tweets.extend(tweets)
                print(f"    ✅ 成功提取 {len(tweets)} 条。")
            else:
                print(f"    ⚠️ HTTP {resp.status_code}")
        except Exception as e:
            pass
        time.sleep(1) 
        
    return all_tweets

def fetch_global_hot_tweets_twitterapi() -> list:
    """🚨 V13.0: 彻底放开领域限制，专门捕获 X 平台全网高赞的【中文推文】补充信息差"""
    if not TWITTERAPI_IO_KEY: return []
    yesterday = get_safe_yesterday()
    all_tweets = []
    
    print(f"\n📡 [全网探测] 扫描全球 X.com 高赞中文神仙打架与突发热点...", flush=True)
    
    # 策略 1: 扫描过去 24 小时全网任何点赞大于 300 的纯中文推文 (无视账号列表，发现盲区)
    # 策略 2: 适当降低门槛 (赞>100)，聚焦在包含“科技、创业、搞钱、AI”等泛商业词汇的中文帖
    queries = [
        f'lang:zh since:{yesterday} min_faves:300 -filter:retweets',
        f'(AI OR 科技 OR 创业 OR 商业 OR 搞钱 OR 独立开发 OR 马斯克 OR 开源) lang:zh since:{yesterday} min_faves:100 -filter:retweets'
    ]
    
    headers = {"X-API-Key": TWITTERAPI_IO_KEY}
    url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
    
    for idx, q in enumerate(queries, 1):
        params = {"query": q, "queryType": "Top"}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=25)
            if resp.status_code == 200:
                tweets = parse_tweets_recursive(resp.json())
                for t in tweets: t["t"] = parse_twitter_date(t.get("created_at", ""))
                all_tweets.extend(tweets)
                print(f"    ✅ 探测策略 {idx} 成功，捕获 {len(tweets)} 条全网中文大V情报。")
        except: pass
        time.sleep(1)
        
    return all_tweets


# ==============================================================================
# 🚀 第二阶段：纯 XML 提示词与大模型调用 (Grok-4.20-Multi-Agent 聚类版)
# ==============================================================================
def _build_xml_prompt(combined_jsonl: str, today_str: str, macro_info: str) -> str:
    return f"""
你是一个专业的 X（Twitter）话题分析师和主编。
目前你搭载了强大的 Multi-Agent 聚类分析能力。请基于下面过去 24 小时的账号更新（包括我们指定的 100 多位中文超级个体，以及全网热门的高赞中文推文），自动进行主题聚类。

【核心指令】
1. 不必局限于特定领域。只要是过去 24 小时内最值得关注、最有趣、最硬核或最有启发的话题（技术突破、大佬商业思考、大瓜、趋势等），都请提炼出来。
2. 从所有数据中，精心挑选出 3~5 个最有趣、最有讨论价值的话题作为 <THEMES>。
3. 🚨【翻译与评价铁律】：在 <COMMENTS> 中，请给出你的专家级点评（解释它为什么有趣、背后的数据/趋势支撑是什么、或对普通人有什么启示）。

【职权隔离铁律】
1. X平台一手推文（JSONL）是【绝对的主干】，用于生成 <THEMES> 和 <TOP_PICKS>。
2. Perplexity 提供的情报仅用于填充 <MARKET_RADAR> 中的客观数字事实，绝不能用二手媒体报道冲淡推特大佬的干货！

【输出结构规范】(必须且只能输出严格的 XML，不要包含 markdown 代码块如 ```xml)
<REPORT>
  <COVER title="10-20字极具吸引力的单主题爆款标题" prompt="100字英文图生图提示词" insight="30字内核心洞察，中文"/>
  <PULSE>用一句话总结今日最核心的 1-2 个全网科技/商业动态信号。</PULSE>
  
  <THEMES>
    <THEME type="new" emoji="🔥">
      <TITLE>话题名称：简短描述</TITLE>
      <NARRATIVE>一句话说明：到底发生了什么、什么在变化</NARRATIVE>
      <TWEET account="X账号名" role="中文身份标签">【严禁纯英文】以中文为主精练该话题下大佬的实战言论或爆料</TWEET>
      <TWEET account="..." role="...">...</TWEET>
      <COMMENTS>🔥 为什么有趣：深度剖析背后的逻辑、趋势支撑、或它带来的独特启示</COMMENTS>
      <OPPORTUNITY>可能带来的机会或红利</OPPORTUNITY>
      <RISK>争议点、风险或踩坑预警</RISK>
    </THEME>
  </THEMES>

  <MARKET_RADAR>
    <!-- 从 Perplexity 提取硬核事实 -->
    <ITEM category="硬核快讯">重磅融资、收入数据、财报等客观事实。</ITEM>
    <ITEM category="行业风向">巨头动作、市场大盘风向。</ITEM>
    <ITEM category="工具/项目">被提及或推荐的新开源项目、AI 工具。</ITEM>
  </MARKET_RADAR>

  <RISK_AND_TRENDS>
    <ITEM category="踩坑预警">平台政策变化、被封禁的风险、开发或创业大坑。</ITEM>
    <ITEM category="趋势判断">未来 1-3 个月的赛道趋势判断。</ITEM>
  </RISK_AND_TRENDS>

  <TOP_PICKS>
    <!-- 🚨 必须挑选出 3 到 5 条全网最精彩的精选推文！严禁只输出一条！ -->
    <TWEET account="..." role="...">【严禁纯英文】价值最大、最有趣或点赞极高的原味金句（中文精译）</TWEET>
    <TWEET account="..." role="...">...</TWEET>
    <TWEET account="..." role="...">...</TWEET>
  </TOP_PICKS>
</REPORT>

# 外部客观数据背景 (Perplexity):
{macro_info if macro_info else "未获取到宏观数据"}

# X平台一手原始数据输入 (包含指定账号与全网高赞盲区 JSONL):
{combined_jsonl}

# 日期: {today_str}
"""

def llm_call_xai(combined_jsonl: str, today_str: str, macro_info: str) -> str:
    api_key = XAI_API_KEY.strip()
    if not api_key: return ""

    max_data_chars = 100000 
    data = combined_jsonl[:max_data_chars] if len(combined_jsonl) > max_data_chars else combined_jsonl
    prompt = _build_xml_prompt(data, today_str, macro_info)
    
    # 🚨 升级为官方推荐的多智能体聚类模型 (适合长文本与主题提炼)
    model_name = "grok-4.20-multi-agent-beta-0309" 

    print(f"\n[LLM/xAI] Requesting {model_name} via Official xai-sdk...", flush=True)
    client = Client(api_key=api_key)
    
    for attempt in range(1, 4):
        try:
            chat = client.chat.create(model=model_name)
            chat.append(system("You are a professional X (Twitter) topic analyst. You strictly output in XML format as instructed. Do not ignore the translation rules."))
            chat.append(user(prompt))
            result = chat.sample().content.strip()
            
            # 清理可能的 Markdown 包装
            result = re.sub(r'^
