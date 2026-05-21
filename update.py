import requests, os, json, re, datetime, time, random

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# ── 简易西译中词典 ──────────────────────────────
ZH = {
    "el":"这","la":"这","los":"这些","las":"estas","un":"一个","una":"una",
    "y":"和","en":"在","de":"的","que":"的","se":"自身","no":"不","es":"是",
    "por":"因为","con":"和","del":"的","al":"到","le":"他",
    "ha":"已","han":"已","fue":"是","son":"是","están":"在",
    "nuevo":"新的","nueva":"新的","gran":"伟大的","grande":"大的",
    "primer":"第一","primera":"第一","último":"最后","última":"最后",
    "mundo":"世界","país":"国家","ciudad":"城市","gobierno":"政府",
    "presidente":"总统","ministro":"部长","partido":"党/比赛",
    "año":"年","años":"年","millones":"百万","personas":"人们",
    "tiempo":"时间","caso":"案例","parte":"部分","vez":"次",
    "puede":"可以","deben":"必须","tiene":"有","tienen":"有",
    "según":"根据","durante":"在……期间","después":"之后","antes":"之前",
    "también":"也","más":"更多","pero":"但是","sino":"而是","aunque":"虽然",
    "porque":"因为","cuando":"当","donde":"在哪里","como":"如同",
    "España":"西班牙","español":"西班牙语","europeo":"欧洲的",
    "fútbol":"足球","gol":"进球","campeón":"冠军","equipo":"球队",
    "partido":"比赛","jugador":"球员","entrenador":"教练",
    "Liga":"联赛","Champions":"欧冠","Real":"皇家","Madrid":"马德里",
    "Barcelona":"巴塞罗那","Barça":"巴萨",
    "película":"电影","cine":"电影院","director":"导演","actor":"演员",
    "actriz":"女演员","estreno":"首映","festival":"节日",
    "ciencia":"科学","científicos":"科学家","investigación":"研究",
    "salud":"健康","tecnología":"技术","inteligencia":"智能",
    "artificial":"人工","datos":"数据","digital":"数字的",
    "cultura":"文化","música":"音乐","arte":"艺术","libro":"书",
    "economía":"经济","crisis":"危机","inflación":"通货膨胀",
    "mercado":"市场","empresa":"企业","trabajo":"工作",
    "clima":"气候","cambio":"变化","energía":"能源","agua":"水",
    "guerra":"战争","paz":"和平","acuerdo":"协议","elecciones":"选举",
    "derechos":"权利","ley":"法律","justicia":"正义",
}

def translate_sentence(text):
    """逐词替换关键词，生成中文参考译文"""
    result = text
    # 替换专有名词和关键词
    for es, zh in sorted(ZH.items(), key=lambda x: -len(x[0])):
        pattern = r'(?<!\w)' + re.escape(es) + r'(?!\w)'
        result = re.sub(pattern, zh, result, flags=re.IGNORECASE)
    # 如果替换很少，加提示
    zh_chars = len(re.findall(r'[\u4e00-\u9fff]', result))
    if zh_chars < 3:
        return f"（{text[:60]}…的西班牙语原文）"
    return result

def fetch_rss(url, max_items=3):
    """抓取RSS feed获取文章"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; SpanishReader/1.0)'}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        content = r.text
        # 提取items
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        results = []
        for item in items[:max_items]:
            title = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', item, re.DOTALL)
            desc  = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>', item, re.DOTALL)
            link  = re.search(r'<link>(.*?)</link>', item)
            title_text = (title.group(1) or title.group(2) or '').strip() if title else ''
            desc_text  = (desc.group(1)  or desc.group(2)  or '').strip() if desc  else ''
            link_text  = link.group(1).strip() if link else ''
            # 清理HTML标签
            title_text = re.sub(r'<[^>]+>', '', title_text).strip()
            desc_text  = re.sub(r'<[^>]+>', '', desc_text).strip()
            if title_text and len(title_text) > 10:
                results.append({'title': title_text, 'desc': desc_text, 'url': link_text})
        return results
    except Exception as e:
        print(f"RSS error {url}: {e}")
        return []

def split_sentences(text):
    """把段落分成句子列表"""
    text = text.strip()
    # 先按句号分割
    raw = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 25:
            sentences.append(s)
    return sentences[:6]  # 最多6句

def make_article(raw, art_id, category, cat_label, cat_color, source_name):
    """把原始RSS数据做成文章对象"""
    title = raw['title']
    desc  = raw['desc']
    url   = raw['url']
    
    # 合并标题和描述，尽量凑够内容
    full_text = desc if len(desc) > len(title) else title + '. ' + desc
    sentences_raw = split_sentences(full_text)
    
    # 如果句子不够，把标题也加进去
    if len(sentences_raw) < 3:
        sentences_raw = split_sentences(title + '. ' + desc + '. ' + desc)
    
    # 至少保证3句
    while len(sentences_raw) < 3:
        sentences_raw.append(sentences_raw[-1] if sentences_raw else title)
    
    content = []
    for i, s in enumerate(sentences_raw[:6]):
        content.append({
            "id": f"a{art_id}s{i}",
            "es": s,
            "zh": translate_sentence(s)
        })
    
    # 根据分类选语法点
    patterns = get_pattern(category)
    
    return {
        "id": art_id,
        "category": category,
        "level": "B2",
        "catLabel": cat_label,
        "catColor": cat_color,
        "source": source_name,
        "url": url,
        "title": title,
        "subtitle": translate_sentence(title),
        "content": content,
        "patterns": patterns
    }

def get_pattern(category):
    all_patterns = {
        "news": [
            {"sent":"Según los expertos, la situación podría mejorar en los próximos meses",
             "analysis":"【según + 名词】= 根据……，据……，是引用消息来源的标准新闻句型。podría + infinitivo 是条件式（Condicional Simple），表示可能性推测，比直接陈述语气更谨慎客观。",
             "formula":"según + 消息来源 = 据……，根据……"},
            {"sent":"El gobierno anunció nuevas medidas para afrontar la situación",
             "analysis":"【anunciar + 名词/从句】= 宣布……，是新闻语体最常用动词之一。afrontar（应对）比 enfrentar 更书面化。para + infinitivo 表示目的状语。",
             "formula":"anunciar + 名词 = 宣布……"}
        ],
        "football": [
            {"sent":"El delantero marcó un doblete que resultó decisivo para la clasificación del equipo",
             "analysis":"【marcar un doblete】= 打进两球，是足球报道专用词组。que resultó decisivo 是关系从句，resultar + 形容词 = 结果是……，证明是……，比 ser 更强调结果性。",
             "formula":"resultar + 形容词 = 结果是……，证明是……"},
            {"sent":"El equipo remontó un marcador adverso gracias a la determinación de sus jugadores",
             "analysis":"【remontar】= 逆转，反超，是体育语境中的核心动词。gracias a（多亏了）引导原因状语，语义积极，与 a causa de（由于，消极）形成对比，是B2必须区分的介词短语。",
             "formula":"gracias a + 名词 = 多亏了……，得益于……"}
        ],
        "science": [
            {"sent":"Los investigadores han descubierto que el cerebro humano tiene una capacidad de adaptación mayor de lo que se creía",
             "analysis":"【mayor de lo que se creía】= 比人们以为的更……，是C1比较级的高级用法。lo que se creía（人们所认为的）用虚拟式背景下的陈述式，表达已有的普遍认知。",
             "formula":"mayor/menor de lo que se creía = 比人们以为的更……"},
            {"sent":"El estudio, publicado en una revista científica de prestigio, revela datos que podrían cambiar nuestra comprensión del fenómeno",
             "analysis":"【publicado en + 名词】是过去分词作插入性定语，修饰主语 el estudio，避免了繁琐的定语从句。podrían + infinitivo 表示推测性可能，是学术写作常见的谦虚表达方式。",
             "formula":"participio + en + 名词 = 在……上发表的（插入性定语）"}
        ],
        "cinema": [
            {"sent":"La película, aclamada por la crítica especializada, ha superado todas las expectativas de taquilla",
             "analysis":"【aclamado por + 名词】= 受到……的盛赞，是过去分词短语作插入性状语。superar las expectativas（超越预期）是影评和商业报道的固定搭配，反义为 decepcionar las expectativas。",
             "formula":"superar las expectativas = 超越预期，出乎意料地成功"},
            {"sent":"El director reivindica con esta obra su lugar entre los grandes cineastas de su generación",
             "analysis":"【reivindicar + 名词】= 主张，捍卫……的地位，比 reclamar 更具力度和情感色彩。entre los grandes（在……大师之列）是固定表达，用于表示某人达到某一群体水平。",
             "formula":"reivindicar + 名词 = 主张，捍卫……的地位"}
        ],
        "entertainment": [
            {"sent":"El artista ha demostrado una vez más su capacidad para reinventarse y sorprender al público",
             "analysis":"【reinventarse】= 自我重塑，是现代娱乐报道中的高频反身动词。una vez más（再一次）是副词短语，强调重复性。para + infinitivo 在这里表示能力的用途，接在 capacidad 之后是固定搭配。",
             "formula":"capacidad para + infinitivo = 做……的能力"},
        ],
        "story": [
            {"sent":"Había una vez un lugar donde el tiempo transcurría de manera distinta a como lo conocemos",
             "analysis":"【había una vez】是西班牙语故事的经典开头，相当于'从前'。donde 引导地点关系从句。de manera distinta a como（以与……不同的方式）是C1复合比较结构，连接两种不同的方式。",
             "formula":"de manera distinta a como = 以与……不同的方式"}
        ]
    }
    pats = all_patterns.get(category, all_patterns["news"])
    return [random.choice(pats)]

def build_articles():
    """从多个RSS源抓取文章"""
    sources = [
        # 新闻
        ("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "news", "新闻", "#2980B9", "El País"),
        ("https://www.20minutos.es/rss/", "news", "新闻", "#2980B9", "20minutos"),
        # 足球
        ("https://e00-marca.uecdn.es/rss/futbol/primera-division.xml", "football", "足球", "#27AE60", "Marca"),
        ("https://www.mundodeportivo.com/rss/futbol.xml", "football", "足球", "#27AE60", "Mundo Deportivo"),
        # 科普
        ("https://www.muyinteresante.es/rss", "science", "科普", "#16A085", "Muy Interesante"),
        ("https://www.nationalgeographic.com.es/rss/todas-las-noticias", "science", "科普", "#16A085", "National Geographic ES"),
        # 电影/娱乐
        ("https://www.fotogramas.es/rss", "cinema", "电影", "#8E44AD", "Fotogramas"),
        ("https://www.ecartelera.com/rss/noticias.xml", "cinema", "电影", "#8E44AD", "eCartelera"),
    ]
    
    articles = []
    art_id = 1
    
    for rss_url, category, cat_label, cat_color, source_name in sources:
        print(f"Fetching {source_name}...")
        items = fetch_rss(rss_url, max_items=2)
        for item in items:
            if not item['title'] or len(item['title']) < 10:
                continue
            art = make_article(item, art_id, category, cat_label, cat_color, source_name)
            articles.append(art)
            art_id += 1
        time.sleep(0.5)  # 礼貌等待
    
    # 如果RSS全部失败，用NewsAPI补充
    if len(articles) < 3 and NEWS_API_KEY:
        print("RSS failed, falling back to NewsAPI...")
        articles += fetch_newsapi_fallback(art_id)
    
    print(f"Total articles: {len(articles)}")
    return articles

def fetch_newsapi_fallback(start_id):
    """NewsAPI备用"""
    url = "https://newsapi.org/v2/everything"
    queries = [
        ("fútbol España", "football", "足球", "#27AE60"),
        ("ciencia tecnología", "science", "科普", "#16A085"),
        ("España política", "news", "新闻", "#2980B9"),
    ]
    arts = []
    for q, cat, label, color in queries:
        try:
            r = requests.get(url, params={"q":q,"language":"es","pageSize":1,"apiKey":NEWS_API_KEY}, timeout=10)
            items = r.json().get("articles", [])
            for a in items[:1]:
                title = (a.get("title") or "").split(" - ")[0]
                desc  = a.get("description") or a.get("content") or title
                raw   = {"title": title, "desc": desc, "url": a.get("url","")}
                arts.append(make_article(raw, start_id, cat, label, color, a.get("source",{}).get("name","")))
                start_id += 1
        except:
            pass
    return arts

def build_html(articles, today):
    arts_json = json.dumps(articles, ensure_ascii=False, separators=(',',':'))
    count = len(articles)
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MiLector · 每日西语阅读</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#F7F3EE;--primary:#C0392B;--gold:#C8860A;--navy:#1B2A4A;--teal:#2E86AB;--text:#1A1A2E;--muted:#6B7280;--border:#E8DDD0}}
body{{background:var(--bg);font-family:system-ui,-apple-system,sans-serif;color:var(--text);max-width:860px;margin:0 auto;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#1B2A4A,#2C3E6B,#1B2A4A);padding:20px 16px 16px;position:relative;overflow:hidden}}
.hdr::before{{content:'';position:absolute;top:-40px;right:-40px;width:160px;height:160px;background:rgba(200,134,10,.13);border-radius:50%}}
.hi{{position:relative;z-index:1}}
.ht{{display:flex;justify-content:space-between;align-items:flex-start}}
.bf{{font-size:24px;margin-bottom:3px}}
.bt{{font-size:22px;font-weight:900;color:#fff;line-height:1.15}}
.bs{{font-size:11px;color:rgba(255,255,255,.6);margin-top:2px;font-weight:600}}
.ds{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}
.bdg{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:800}}
.bg{{background:var(--gold);color:#fff}}
.bgh{{background:rgba(255,255,255,.1);color:rgba(255,255,255,.8);border:1px solid rgba(255,255,255,.2)}}
.tabs{{display:flex;background:#fff;border-bottom:2px solid var(--border);padding:0 14px}}
.tab{{padding:13px 15px;font-size:13px;font-weight:800;color:var(--muted);cursor:pointer;border:none;background:none;border-bottom:3px solid transparent;margin-bottom:-2px;font-family:inherit;transition:all .2s}}
.tab.on{{color:var(--primary);border-bottom-color:var(--primary)}}
.cats{{display:flex;gap:7px;padding:11px 14px;overflow-x:auto;background:#fff;border-bottom:1px solid var(--border);scrollbar-width:none}}
.cats::-webkit-scrollbar{{display:none}}
.cat{{white-space:nowrap;padding:5px 13px;border-radius:20px;font-size:12px;font-weight:800;cursor:pointer;border:2px solid var(--border);background:var(--bg);color:var(--muted);font-family:inherit;transition:all .2s}}
.cat.on{{background:var(--primary);color:#fff;border-color:var(--primary)}}
.list{{padding:14px;display:flex;flex-direction:column;gap:12px}}
.acard{{background:#fff;border-radius:15px;padding:16px;cursor:pointer;border:2px solid var(--border);transition:all .2s;box-shadow:0 3px 14px rgba(192,57,43,.07)}}
.acard:hover{{transform:translateY(-2px);border-color:#C0392B55}}
.acard-meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px}}
.ctag{{display:inline-block;padding:3px 10px;border-radius:9px;font-size:11px;font-weight:800;color:#fff}}
.ltag{{font-size:11px;font-weight:800;color:#fff;background:var(--navy);padding:3px 9px;border-radius:8px}}
.acard h3{{font-size:15px;font-weight:800;line-height:1.35;margin-bottom:3px}}
.acard .sub{{font-size:12px;color:var(--muted);font-weight:600}}
.acard .src{{font-size:11px;color:var(--teal);font-weight:700;margin-top:5px}}
.acard .prev{{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.rhd{{background:#fff;padding:14px 15px;border-bottom:2px solid var(--border);position:sticky;top:0;z-index:10}}
.back{{display:flex;align-items:center;gap:5px;background:none;border:none;color:var(--primary);font-size:13px;font-weight:800;cursor:pointer;margin-bottom:9px;font-family:inherit}}
.rhd h2{{font-size:19px;font-weight:900;line-height:1.3}}
.rhd .sub2{{font-size:12px;color:var(--muted);font-weight:600;margin-top:3px}}
.rhd .srctag{{font-size:11px;color:var(--teal);font-weight:700;margin-top:4px}}
.ctrls{{display:flex;gap:7px;margin-top:10px;flex-wrap:wrap}}
.ctrl{{padding:6px 13px;border-radius:20px;font-size:12px;font-weight:800;cursor:pointer;border:2px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;transition:all .2s}}
.ctrl.on{{background:var(--teal);color:#fff;border-color:var(--teal)}}
.hint{{font-size:11px;color:var(--muted);text-align:center;padding:8px 14px 2px;font-weight:600}}
.sentences{{padding:13px;display:flex;flex-direction:column;gap:12px}}
.sblock{{background:#fff;border-radius:13px;padding:14px;border:2px solid var(--border)}}
.snum{{font-size:10px;font-weight:900;color:var(--primary);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.est{{font-size:15px;font-weight:600;line-height:1.85;color:var(--text);user-select:none;cursor:default}}
.word{{cursor:pointer;border-radius:3px;padding:0 2px;transition:background .12s;display:inline}}
.word:hover{{background:#FFF3E0;color:var(--primary)}}
.word.pressing{{background:#FDEBD0;color:var(--primary)}}
.zht{{font-size:13px;color:var(--teal);margin-top:8px;padding-top:8px;border-top:1px dashed var(--border);line-height:1.65;font-weight:600}}
.pats{{margin:0 13px 22px;background:linear-gradient(135deg,#EEF2FF,#E0F2FE);border-radius:15px;padding:16px;border:2px solid #C7D2FE}}
.pt{{font-size:14px;font-weight:800;color:var(--navy);margin-bottom:12px}}
.pi{{margin-bottom:15px}}
.pi:last-child{{margin-bottom:0}}
.ps{{font-size:13px;font-weight:700;color:#1E40AF;background:rgba(255,255,255,.7);padding:8px 12px;border-radius:9px;margin-bottom:7px;border-left:3px solid var(--teal);font-style:italic;line-height:1.55}}
.pa{{font-size:12px;color:#374151;line-height:1.78}}
.pf{{display:inline-block;background:#F7C948;color:#1A1A2E;padding:3px 10px;border-radius:7px;font-size:11px;font-weight:800;margin-top:5px}}
.overlay{{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;display:none;align-items:flex-end;justify-content:center}}
.overlay.show{{display:flex}}
.popup{{background:#fff;width:100%;max-width:620px;border-radius:22px 22px 0 0;padding:20px 18px 34px;animation:slideUp .22s ease-out}}
.drag{{width:38px;height:4px;background:var(--border);border-radius:4px;margin:0 auto 16px}}
.pw{{font-size:30px;font-weight:900;color:var(--primary)}}
.pty{{font-size:12px;color:var(--muted);font-weight:700;margin:3px 0 9px}}
.pm{{font-size:20px;font-weight:800;margin-bottom:13px}}
.pctx{{background:var(--bg);border-radius:11px;padding:10px 13px;margin-bottom:7px;border-left:3px solid var(--primary)}}
.pctx.alt{{border-left-color:var(--teal)}}
.pctx .es{{font-size:13px;font-style:italic;font-weight:600;line-height:1.6;color:var(--text)}}
.pctx .zh{{font-size:12px;color:var(--muted);margin-top:4px}}
.pacts{{display:flex;gap:8px;margin-top:14px}}
.addbtn{{flex:1;background:var(--primary);color:#fff;border:none;padding:12px;border-radius:12px;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit}}
.clsbtn{{padding:12px 17px;border-radius:12px;border:2px solid var(--border);background:none;font-size:13px;font-weight:700;cursor:pointer;color:var(--muted);font-family:inherit}}
.vwrap{{padding:14px}}
.vhd{{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}}
.vcnt{{background:var(--primary);color:#fff;padding:4px 11px;border-radius:20px;font-size:12px;font-weight:800}}
.vsrch{{width:100%;padding:9px 14px;border-radius:11px;border:2px solid var(--border);font-size:14px;background:#fff;color:var(--text);margin-bottom:12px;outline:none;font-family:inherit}}
.vsrch:focus{{border-color:var(--primary)}}
.vcard{{background:#fff;border-radius:13px;padding:14px;margin-bottom:9px;border:2px solid var(--border)}}
.vrow{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px}}
.vw{{font-size:21px;font-weight:900;color:var(--primary)}}
.vt{{font-size:11px;color:var(--muted);font-weight:700;background:var(--bg);padding:2px 8px;border-radius:7px;margin-top:3px}}
.vmn{{font-size:16px;font-weight:800;margin-bottom:8px}}
.vsnt{{background:var(--bg);border-radius:9px;padding:9px 11px;border-left:3px solid var(--gold)}}
.vsnt .es{{font-size:12px;font-style:italic;line-height:1.55}}
.vsnt .zh{{font-size:12px;color:var(--muted);margin-top:4px}}
.vdt{{font-size:10px;color:var(--muted);text-align:right;margin-top:6px;font-weight:700}}
.vdel{{background:none;border:none;color:#EF4444;cursor:pointer;font-size:22px;line-height:1;padding:0 4px;flex-shrink:0}}
.empty{{text-align:center;padding:55px 18px;color:var(--muted)}}
.eico{{font-size:50px;margin-bottom:10px}}
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1A1A2E;color:#fff;padding:11px 20px;border-radius:22px;font-size:13px;font-weight:800;z-index:200;white-space:nowrap;display:none;box-shadow:0 7px 26px rgba(0,0,0,.28)}}
@keyframes slideUp{{from{{transform:translateY(28px);opacity:0}}to{{transform:translateY(0);opacity:1}}}}
</style>
</head>
<body>
<div class="hdr">
  <div class="hi">
    <div class="ht">
      <div>
        <div class="bf">&#127466;&#127480;</div>
        <div class="bt">MiLector Español</div>
        <div class="bs">每日西语精读 · B2-C1 · 实时新闻</div>
      </div>
    </div>
    <div class="ds">
      <span class="bdg bg">&#128197; {today}</span>
      <span class="bdg bgh">&#127919; B2-C1</span>
      <span class="bdg bgh">&#128196; {count}篇文章</span>
    </div>
  </div>
</div>
<div class="tabs">
  <button class="tab on" id="tabRead">&#128218; 阅读</button>
  <button class="tab" id="tabVocab">&#128214; 词库</button>
</div>
<div id="panelRead">
  <div class="cats">
    <button class="cat on" data-cat="all">全部</button>
    <button class="cat" data-cat="news">&#127758; 新闻</button>
    <button class="cat" data-cat="science">&#128300; 科普</button>
    <button class="cat" data-cat="football">&#9917; 足球</button>
    <button class="cat" data-cat="cinema">&#127916; 电影</button>
    <button class="cat" data-cat="entertainment">&#127881; 娱乐</button>
  </div>
  <div class="list" id="articleList"></div>
  <div id="articleReader" style="display:none"></div>
</div>
<div id="panelVocab" style="display:none">
  <div class="vwrap">
    <div class="vhd">
      <span style="font-weight:800;font-size:16px">我的词库</span>
      <span class="vcnt" id="vocabCount">0 个单词</span>
    </div>
    <input class="vsrch" id="vocabSearch" placeholder="搜索单词或中文...">
    <div id="vocabList"></div>
  </div>
</div>
<div class="overlay" id="overlay">
  <div class="popup"><div class="drag"></div><div id="popupBody"></div></div>
</div>
<div class="toast" id="toast"></div>
<script>
var ARTICLES={arts_json};
var vocab=[];
try{{vocab=JSON.parse(localStorage.getItem('es_vocab')||'[]');}}catch(e){{vocab=[];}}
var currentCat='all',currentArticle=null,showChinese=false,pressTimer=null;
(function(){{
  document.getElementById('tabRead').addEventListener('click',function(){{switchTab('read');}});
  document.getElementById('tabVocab').addEventListener('click',function(){{switchTab('vocab');}});
  document.getElementById('overlay').addEventListener('click',function(e){{if(e.target===document.getElementById('overlay'))closePopup();}});
  document.getElementById('vocabSearch').addEventListener('input',renderVocab);
  document.querySelectorAll('.cat').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      currentCat=btn.getAttribute('data-cat');
      document.querySelectorAll('.cat').forEach(function(b){{b.classList.remove('on');}});
      btn.classList.add('on');renderList();
    }});
  }});
  renderList();updateVocabBadge();
}})();
function switchTab(t){{
  document.getElementById('panelRead').style.display=t==='read'?'':'none';
  document.getElementById('panelVocab').style.display=t==='vocab'?'':'none';
  document.getElementById('tabRead').className='tab'+(t==='read'?' on':'');
  document.getElementById('tabVocab').className='tab'+(t==='vocab'?' on':'');
  if(t==='vocab')renderVocab();
}}
function renderList(){{
  var list=document.getElementById('articleList'),reader=document.getElementById('articleReader');
  reader.style.display='none';list.style.display='';list.innerHTML='';
  ARTICLES.filter(function(a){{return currentCat==='all'||a.category===currentCat;}}).forEach(function(a){{
    var card=document.createElement('div');card.className='acard';
    card.innerHTML='<div class="acard-meta"><span class="ctag" style="background:'+a.catColor+'">'+a.catLabel+'</span><span class="ltag">'+a.level+'</span></div>'+
      '<h3>'+a.title+'</h3><div class="sub">'+a.subtitle+'</div>'+
      '<div class="src">&#128240; '+a.source+'</div>'+
      '<div class="prev">'+a.content[0].es+'</div>';
    (function(aid){{card.addEventListener('click',function(){{openArticle(aid);}});}})(a.id);
    list.appendChild(card);
  }});
}}
function openArticle(id){{
  for(var i=0;i<ARTICLES.length;i++){{if(ARTICLES[i].id===id){{currentArticle=ARTICLES[i];break;}}}}
  if(!currentArticle)return;
  showChinese=false;
  document.getElementById('articleList').style.display='none';
  var reader=document.getElementById('articleReader');
  reader.style.display='';reader.innerHTML='';
  var hd=document.createElement('div');hd.className='rhd';
  var back=document.createElement('button');back.className='back';back.textContent='← 返回文章列表';
  back.addEventListener('click',backToList);hd.appendChild(back);
  var h2=document.createElement('h2');h2.textContent=currentArticle.title;hd.appendChild(h2);
  var s2=document.createElement('div');s2.className='sub2';s2.textContent=currentArticle.subtitle+' ['+currentArticle.level+']';hd.appendChild(s2);
  var st=document.createElement('div');st.className='srctag';st.textContent='来源：'+currentArticle.source;hd.appendChild(st);
  var ctrls=document.createElement('div');ctrls.className='ctrls';
  var zhBtn=document.createElement('button');zhBtn.className='ctrl';zhBtn.id='zhToggle';zhBtn.textContent='显示中文翻译';
  zhBtn.addEventListener('click',toggleChinese);ctrls.appendChild(zhBtn);hd.appendChild(ctrls);reader.appendChild(hd);
  var hint=document.createElement('p');hint.className='hint';hint.textContent='长按任意单词 → 查询释义 → 加入词库';reader.appendChild(hint);
  var sw=document.createElement('div');sw.className='sentences';
  currentArticle.content.forEach(function(s,i){{
    var block=document.createElement('div');block.className='sblock';
    var num=document.createElement('div');num.className='snum';num.textContent='第'+(i+1)+'句';block.appendChild(num);
    var esDiv=document.createElement('div');esDiv.className='est';buildSpans(s,esDiv);block.appendChild(esDiv);
    var zhDiv=document.createElement('div');zhDiv.className='zht';zhDiv.id='zh_'+s.id;zhDiv.style.display='none';zhDiv.textContent=s.zh;block.appendChild(zhDiv);
    sw.appendChild(block);
  }});
  reader.appendChild(sw);
  var pw=document.createElement('div');pw.className='pats';
  var ptitle=document.createElement('div');ptitle.className='pt';ptitle.textContent='重点句型 & 语法分析';pw.appendChild(ptitle);
  currentArticle.patterns.forEach(function(p){{
    var item=document.createElement('div');item.className='pi';
    var ps=document.createElement('div');ps.className='ps';ps.textContent=p.sent;item.appendChild(ps);
    var pa=document.createElement('div');pa.className='pa';pa.textContent=p.analysis;item.appendChild(pa);
    var pf=document.createElement('div');pf.className='pf';pf.textContent=p.formula;item.appendChild(pf);
    pw.appendChild(item);
  }});
  reader.appendChild(pw);
}}
function buildSpans(sentence,container){{
  sentence.es.split(/(\s+)/).forEach(function(tok){{
    if(/^\s+$/.test(tok)){{container.appendChild(document.createTextNode(tok));return;}}
    var clean=tok.replace(/[.,!?;:()¡¿«»—]/g,'');
    if(clean.length<2){{container.appendChild(document.createTextNode(tok));return;}}
    var span=document.createElement('span');span.className='word';span.textContent=tok;
    var cw=clean.toLowerCase(),cs=sentence;
    function onStart(){{span.classList.add('pressing');clearTimeout(pressTimer);
      pressTimer=setTimeout(function(){{span.classList.remove('pressing');showWordPopup(cw,cs);}},500);}}
    function onEnd(){{clearTimeout(pressTimer);span.classList.remove('pressing');}}
    span.addEventListener('mousedown',onStart);span.addEventListener('mouseup',onEnd);
    span.addEventListener('mouseleave',onEnd);span.addEventListener('touchstart',onStart,{{passive:true}});
    span.addEventListener('touchend',onEnd);span.addEventListener('touchcancel',onEnd);
    container.appendChild(span);
  }});
}}
function backToList(){{document.getElementById('articleReader').style.display='none';document.getElementById('articleList').style.display='';}}
function toggleChinese(){{
  showChinese=!showChinese;
  document.querySelectorAll('[id^="zh_"]').forEach(function(el){{el.style.display=showChinese?'':'none';}});
  var btn=document.getElementById('zhToggle');
  if(btn){{btn.textContent=showChinese?'隐藏中文翻译':'显示中文翻译';btn.className=showChinese?'ctrl on':'ctrl';}}
}}
function showWordPopup(word,sentence){{
  openPopup();
  var body=document.getElementById('popupBody');
  var ctxHtml='<div class="pctx"><div style="font-size:11px;color:var(--muted);font-weight:800;margin-bottom:4px">出处原句</div><div class="es">'+sentence.es+'</div><div class="zh">'+sentence.zh+'</div></div>';
  body.innerHTML='<div class="pw">'+word+'</div><div class="pty">西班牙语词汇</div><div class="pm" style="font-size:15px;color:var(--muted)">—</div>'+ctxHtml+'<div class="pacts"><button class="addbtn" id="addWordBtn">加入词库</button><button class="clsbtn" id="closeBtn">关闭</button></div>';
  document.getElementById('addWordBtn').addEventListener('click',function(){{doAdd(word,'—','—',sentence);}});
  document.getElementById('closeBtn').addEventListener('click',closePopup);
}}
function openPopup(){{document.getElementById('overlay').classList.add('show');}}
function closePopup(){{document.getElementById('overlay').classList.remove('show');}}
function doAdd(word,type,zh,sentence){{
  for(var i=0;i<vocab.length;i++){{if(vocab[i].word===word){{showToast('"'+word+'" 已在词库中');closePopup();return;}}}}
  vocab.unshift({{word:word,type:type,chinese:zh,sentence:sentence?sentence.es:'',sentenceZh:sentence?sentence.zh:'',addedAt:new Date().toLocaleDateString('zh-CN')}});
  try{{localStorage.setItem('es_vocab',JSON.stringify(vocab));}}catch(e){{}}
  updateVocabBadge();showToast('"'+word+'" 已加入词库！');closePopup();
}}
function updateVocabBadge(){{
  document.getElementById('tabVocab').textContent=vocab.length>0?'词库 ('+vocab.length+')':'词库';
  var c=document.getElementById('vocabCount');if(c)c.textContent=vocab.length+' 个单词';
}}
function renderVocab(){{
  var q=(document.getElementById('vocabSearch').value||'').toLowerCase();
  var c=document.getElementById('vocabCount');if(c)c.textContent=vocab.length+' 个单词';
  var filtered=vocab.filter(function(v){{return v.word.toLowerCase().indexOf(q)>-1||v.chinese.indexOf(q)>-1;}});
  var list=document.getElementById('vocabList');
  if(!filtered.length){{list.innerHTML='<div class="empty"><div class="eico">'+(vocab.length?'🔍':'📚')+'</div><p>'+(vocab.length?'没有匹配的单词':'词库还是空的<br>去阅读文章，长按单词加入词库！')+'</p></div>';return;}}
  list.innerHTML='';
  filtered.forEach(function(v){{
    var card=document.createElement('div');card.className='vcard';
    var sentHtml=v.sentence?'<div class="vsnt"><div class="es">'+v.sentence+'</div><div class="zh">'+v.sentenceZh+'</div></div>':'';
    card.innerHTML='<div class="vrow"><div><div class="vw">'+v.word+'</div><div class="vt">'+v.type+'</div></div><button class="vdel">×</button></div><div class="vmn">'+v.chinese+'</div>'+sentHtml+'<div class="vdt">加入时间：'+v.addedAt+'</div>';
    var cw=v.word;card.querySelector('.vdel').addEventListener('click',function(){{removeVocab(cw);}});
    list.appendChild(card);
  }});
}}
function removeVocab(word){{
  vocab=vocab.filter(function(v){{return v.word!==word;}});
  try{{localStorage.setItem('es_vocab',JSON.stringify(vocab));}}catch(e){{}}
  updateVocabBadge();renderVocab();showToast('已移除 "'+word+'"');
}}
var toastTimer=null;
function showToast(msg){{
  var t=document.getElementById('toast');t.textContent=msg;t.style.display='block';
  clearTimeout(toastTimer);toastTimer=setTimeout(function(){{t.style.display='none';}},2600);
}}
</script>
</body>
</html>"""

# ── 主程序 ──────────────────────────────────────
articles = build_articles()
today = datetime.date.today().strftime("%Y年%-m月%-d日")
html = build_html(articles, today)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"Done: {len(articles)} articles written to index.html")
