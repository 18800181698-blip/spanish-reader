import requests, os, json, re, datetime, time, random

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# ══════════════════════════════════════════════
# 1. 抓取真实新闻标题（多来源，含拉美）
# ══════════════════════════════════════════════
RSS_SOURCES = [
    # 西班牙
    ("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",         "news",          "新闻",  "#2980B9", "El País"),
    ("https://www.elmundo.es/rss/portada.xml",                                    "news",          "新闻",  "#2980B9", "El Mundo"),
    ("https://www.20minutos.es/rss/",                                             "news",          "新闻",  "#2980B9", "20minutos"),
    # 拉美
    ("https://www.lanacion.com.ar/arcio/rss/",                                    "news",          "新闻",  "#2980B9", "La Nación AR"),
    ("https://www.eltiempo.com/rss/colombia.xml",                                 "news",          "新闻",  "#2980B9", "El Tiempo CO"),
    ("https://www.eluniversal.com.mx/rss.xml",                                    "news",          "新闻",  "#2980B9", "El Universal MX"),
    ("https://feeds.bbci.co.uk/mundo/rss.xml",                                    "news",          "新闻",  "#2980B9", "BBC Mundo"),
    # 科普
    ("https://www.muyinteresante.es/rss",                                         "science",       "科普",  "#16A085", "Muy Interesante"),
    ("https://www.nationalgeographic.com.es/rss/todas-las-noticias",              "science",       "科普",  "#16A085", "National Geographic ES"),
    ("https://www.investigacionyciencia.es/rss",                                  "science",       "科普",  "#16A085", "Investigación y Ciencia"),
    # 影评文化
    ("https://www.fotogramas.es/rss",                                             "cinema",        "影评",  "#8E44AD", "Fotogramas"),
    ("https://www.sensacine.com/noticias/rss/",                                   "cinema",        "影评",  "#8E44AD", "SensaCine"),
    ("https://www.elmundo.es/cultura.xml",                                        "entertainment", "娱乐",  "#D35400", "El Mundo Cultura"),
    ("https://www.lavanguardia.com/rss/vida/ocio-y-cultura.xml",                  "entertainment", "娱乐",  "#D35400", "La Vanguardia"),
    # 文学
    ("https://www.letraslibres.com/rss.xml",                                      "literature",    "文学",  "#C0392B", "Letras Libres"),
    ("https://www.culturamas.es/feed/",                                           "literature",    "文学",  "#C0392B", "Culturamas"),
]

def fetch_rss_titles(url, max_items=3):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; SpanishReader/1.0)'}
        r = requests.get(url, headers=headers, timeout=12)
        r.encoding = 'utf-8'
        items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        results = []
        for item in items[:max_items]:
            title = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', item, re.DOTALL)
            desc  = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>', item, re.DOTALL)
            link  = re.search(r'<link>(.*?)</link>', item)
            t = (title.group(1) or title.group(2) or '').strip() if title else ''
            d = (desc.group(1)  or desc.group(2)  or '').strip() if desc  else ''
            l = link.group(1).strip() if link else ''
            t = re.sub(r'<[^>]+>', '', t).strip()
            d = re.sub(r'<[^>]+>', '', d).strip()
            if t and len(t) > 15 and t != '[Removed]':
                results.append({'title': t, 'desc': d[:300], 'url': l})
        return results
    except Exception as e:
        print(f"  RSS error {url}: {e}")
        return []

# ══════════════════════════════════════════════
# 2. 用 Gemini 生成完整文章+翻译+语法分析
# ══════════════════════════════════════════════
def gemini(prompt, max_tokens=2000):
    if not GEMINI_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
    }
    try:
        r = requests.post(url, json=body, timeout=30)
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None

def generate_article(raw, art_id, category, cat_label, cat_color, source_name):
    title = raw['title']
    desc  = raw['desc']

    # 根据分类定制提示词
    cat_instructions = {
        "news":          "un artículo periodístico sobre este tema de actualidad",
        "science":       "un artículo divulgativo científico sobre este tema",
        "cinema":        "una reseña o artículo cultural sobre cine, series o cultura audiovisual",
        "entertainment": "un artículo sobre cultura, música, arte o entretenimiento",
        "literature":    "un fragmento narrativo literario o reseña literaria relacionado con este tema",
    }
    style = cat_instructions.get(category, "un artículo periodístico")

    prompt = f"""Eres un periodista y escritor hispanohablante nativo. Tu tarea es escribir {style} basado en la siguiente noticia real:

TITULAR: {title}
CONTEXTO: {desc}

INSTRUCCIONES ESTRICTAS:
1. Escribe exactamente 6 oraciones en español. Cada oración debe terminar con punto y estar en una línea separada.
2. El nivel de dificultad debe ser B2-C1: vocabulario rico, estructuras gramaticales variadas y naturales.
3. El estilo debe sonar completamente natural y humano, como un periodista real. NADA de frases genéricas o clichés de IA.
4. Las oraciones deben estar conectadas y contar una historia o desarrollar una idea de forma coherente.
5. Usa conectores variados: sin embargo, no obstante, a pesar de ello, cabe destacar, lejos de, en cambio, etc.
6. DESPUÉS de las 6 oraciones, añade una línea en blanco y luego escribe:
   TITULO_ZH: [traducción del titular al chino mandarín, natural y fluida]
   SENTENCE_ZH_1: [traducción china de la oración 1]
   SENTENCE_ZH_2: [traducción china de la oración 2]
   SENTENCE_ZH_3: [traducción china de la oración 3]
   SENTENCE_ZH_4: [traducción china de la oración 4]
   SENTENCE_ZH_5: [traducción china de la oración 5]
   SENTENCE_ZH_6: [traducción china de la oración 6]
   PATTERN_SENT: [copia literal la oración más interesante gramaticalmente]
   PATTERN_ANALYSIS: [explica en chino mandarín la estructura gramatical B2-C1 más importante de esa oración, con ejemplos]
   PATTERN_FORMULA: [escribe en chino la fórmula o regla gramatical, formato: estructura = significado]

Responde SOLO con el formato indicado, sin títulos adicionales ni explicaciones."""

    response = gemini(prompt)
    if not response:
        return None

    # 解析响应
    lines = [l.strip() for l in response.split('\n') if l.strip()]
    
    es_sentences = []
    zh_sentences = {}
    titulo_zh = ""
    pattern_sent = ""
    pattern_analysis = ""
    pattern_formula = ""

    for line in lines:
        if line.startswith('TITULO_ZH:'):
            titulo_zh = line.replace('TITULO_ZH:', '').strip()
        elif line.startswith('SENTENCE_ZH_'):
            m = re.match(r'SENTENCE_ZH_(\d+):\s*(.*)', line)
            if m:
                zh_sentences[int(m.group(1))] = m.group(2).strip()
        elif line.startswith('PATTERN_SENT:'):
            pattern_sent = line.replace('PATTERN_SENT:', '').strip()
        elif line.startswith('PATTERN_ANALYSIS:'):
            pattern_analysis = line.replace('PATTERN_ANALYSIS:', '').strip()
        elif line.startswith('PATTERN_FORMULA:'):
            pattern_formula = line.replace('PATTERN_FORMULA:', '').strip()
        elif not any(line.startswith(k) for k in ['TITULO_ZH','SENTENCE_ZH','PATTERN_']):
            # 西班牙语句子
            if len(line) > 20 and len(es_sentences) < 6:
                es_sentences.append(line)

    if len(es_sentences) < 3:
        print(f"  Not enough sentences parsed, got {len(es_sentences)}")
        return None

    content = []
    for i, s in enumerate(es_sentences):
        content.append({
            "id": f"a{art_id}s{i}",
            "es": s,
            "zh": zh_sentences.get(i+1, "")
        })

    return {
        "id": art_id,
        "category": category,
        "level": "B2" if category in ["news","entertainment"] else "C1" if category == "literature" else "B2",
        "catLabel": cat_label,
        "catColor": cat_color,
        "source": source_name,
        "url": raw.get('url',''),
        "title": title,
        "subtitle": titulo_zh or title,
        "content": content,
        "patterns": [{
            "sent": pattern_sent,
            "analysis": pattern_analysis,
            "formula": pattern_formula
        }] if pattern_sent else [get_fallback_pattern(category)]
    }

def get_fallback_pattern(category):
    patterns = {
        "news": {"sent":"Según los expertos, la situación podría mejorar en los próximos meses",
                 "analysis":"【según + 名词】= 根据……，是引用消息来源的标准新闻句型。podría + infinitivo 是条件式，表示可能性推测，语气比直接陈述更谨慎。",
                 "formula":"según + 消息来源 = 据……，根据……"},
        "science": {"sent":"Los investigadores han descubierto que la capacidad del cerebro supera lo que se creía",
                    "analysis":"【superar lo que se creía】= 超过人们所认为的，是C1比较级的高级用法，lo que se creía 表达已有的普遍认知。",
                    "formula":"superar lo que se creía = 超过人们以为的"},
        "cinema": {"sent":"La película reivindica su lugar entre las grandes obras del cine contemporáneo",
                   "analysis":"【reivindicar + 名词】= 主张，捍卫……的地位，比 reclamar 更具力度，是C1影评语体常用动词。",
                   "formula":"reivindicar + 名词 = 主张，捍卫……的地位"},
        "entertainment": {"sent":"El artista ha demostrado una vez más su capacidad para reinventarse",
                          "analysis":"【reinventarse】= 自我重塑，现代娱乐报道高频反身动词。una vez más（再一次）副词短语强调重复性。",
                          "formula":"capacidad para + infinitivo = 做……的能力"},
        "literature": {"sent":"La narrativa construye un mundo donde lo real y lo imaginario coexisten sin contradicción",
                       "analysis":"【donde + 从句】引导地点关系从句，修饰前面的名词。coexistir（共存）是文学语体的高级动词，sin contradicción（毫无矛盾地）是副词短语。",
                       "formula":"donde + 从句 = 在……的世界里（地点关系从句）"},
    }
    return patterns.get(category, patterns["news"])

# ══════════════════════════════════════════════
# 3. 主程序
# ══════════════════════════════════════════════
def build_articles():
    # 先收集所有RSS标题
    all_raw = []
    for rss_url, category, cat_label, cat_color, source_name in RSS_SOURCES:
        print(f"Fetching {source_name}...")
        items = fetch_rss_titles(rss_url, max_items=2)
        for item in items[:2]:
            all_raw.append((item, category, cat_label, cat_color, source_name))
        time.sleep(0.3)

    # 每个分类选最多2篇，用Gemini生成
    cat_counts = {}
    articles = []
    art_id = 1

    random.shuffle(all_raw)

    for raw, category, cat_label, cat_color, source_name in all_raw:
        if cat_counts.get(category, 0) >= 2:
            continue
        if len(articles) >= 12:  # 总上限12篇
            break

        print(f"  Generating [{category}] {raw['title'][:50]}...")
        art = generate_article(raw, art_id, category, cat_label, cat_color, source_name)
        if art:
            articles.append(art)
            cat_counts[category] = cat_counts.get(category, 0) + 1
            art_id += 1
            print(f"  ✓ Done ({len(art['content'])} sentences)")
        else:
            print(f"  ✗ Failed")
        time.sleep(1)  # 避免API限流

    print(f"\nTotal articles: {len(articles)}")
    return articles

# ══════════════════════════════════════════════
# 4. 生成 HTML
# ══════════════════════════════════════════════
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
        <div class="bs">每日西语精读 · B2-C1 · 实时更新</div>
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
    <button class="cat" data-cat="cinema">&#127916; 影评</button>
    <button class="cat" data-cat="entertainment">&#127881; 娱乐</button>
    <button class="cat" data-cat="literature">&#128213; 文学</button>
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
var VOCAB_KEY='milector_vocab_v2';
var vocab=[];
try{{vocab=JSON.parse(localStorage.getItem(VOCAB_KEY)||'[]');}}catch(e){{vocab=[];}}
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
      '<div class="prev">'+(a.content[0]?a.content[0].es:'')+'</div>';
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
  if(currentArticle.patterns&&currentArticle.patterns[0]&&currentArticle.patterns[0].sent){{
    var pw=document.createElement('div');pw.className='pats';
    var ptitle=document.createElement('div');ptitle.className='pt';ptitle.textContent='重点句型 & 语法分析';pw.appendChild(ptitle);
    currentArticle.patterns.forEach(function(p){{
      if(!p.sent)return;
      var item=document.createElement('div');item.className='pi';
      var ps=document.createElement('div');ps.className='ps';ps.textContent=p.sent;item.appendChild(ps);
      var pa=document.createElement('div');pa.className='pa';pa.textContent=p.analysis;item.appendChild(pa);
      var pf=document.createElement('div');pf.className='pf';pf.textContent=p.formula;item.appendChild(pf);
      pw.appendChild(item);
    }});
    reader.appendChild(pw);
  }}
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
function saveVocab(){{try{{localStorage.setItem(VOCAB_KEY,JSON.stringify(vocab));}}catch(e){{}}}}
function doAdd(word,type,zh,sentence){{
  for(var i=0;i<vocab.length;i++){{if(vocab[i].word===word){{showToast('"'+word+'" 已在词库中');closePopup();return;}}}}
  vocab.unshift({{word:word,type:type,chinese:zh,sentence:sentence?sentence.es:'',sentenceZh:sentence?sentence.zh:'',addedAt:new Date().toLocaleDateString('zh-CN')}});
  saveVocab();updateVocabBadge();showToast('"'+word+'" 已加入词库！');closePopup();
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
  saveVocab();updateVocabBadge();renderVocab();showToast('已移除 "'+word+'"');
}}
var toastTimer=null;
function showToast(msg){{
  var t=document.getElementById('toast');t.textContent=msg;t.style.display='block';
  clearTimeout(toastTimer);toastTimer=setTimeout(function(){{t.style.display='none';}},2600);
}}
</script>
</body>
</html>"""

articles = build_articles()
today = datetime.date.today().strftime("%Y年%-m月%-d日")
html = build_html(articles, today)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"Done: {len(articles)} articles")
