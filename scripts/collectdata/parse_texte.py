#!/usr/bin/python
# -*- coding=utf-8 -*-
"""Common law parser for AN/Sénat

Run with python parse_texte.py LAW_FILE
where LAW_FILE results from perl download_loi.pl URL > LAW_FILE
Outputs results to stdout

Dependencies :
html5lib, beautifulsoup4, simplejson"""

import sys, re, html5lib
import simplejson as json
from bs4 import BeautifulSoup

try:
    FILE = sys.argv[1]
    soup = BeautifulSoup(open(FILE,"r"), "html5lib")
except:
    sys.stderr.write("ERROR: Cannot open file", FILE)
    sys.exit(1)

if (len(sys.argv) > 2) :
    ORDER = "%02d_" % int(sys.argv[2])
else:
    ORDER = ''

url = re.sub(r"^.*/http", "http", FILE)
url = re.sub(r"%3A", ":", re.sub(r"%2F", "/", url))
texte = {"type": "texte", "source": url}
# Generate Senat or AN ID from URL
if re.search(r"assemblee-?nationale", url):
    m = re.search(r"/(\d+)/.+/(ta)?[\w\-]*(\d{4})[\.\-]", url)
    numero = int(m.group(3))
    texte["id"] = ORDER+"A" + m.group(1) + "-"
    if m.group(2) is not None:
        texte["id"] += m.group(2)
    texte["id"] += str(numero)
else:
    m = re.search(r"(ta)?s?(\d\d)-(\d{1,3})\.", url)
    numero = int(m.group(3))
    texte["id"] = ORDER+"S" + m.group(2) + "-"
    if m.group(1) is not None:
        texte["id"] += m.group(1)
    texte["id"] += "%03d" % numero

texte["titre"] = soup.title.string
texte["expose"] = ""

# Convert from roman numbers
romans_map = zip(
    (1000,  900, 500, 400 , 100,  90 , 50 ,  40 , 10 ,   9 ,  5 ,  4  ,  1),
    ( 'M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
)
def romans(n):
    i = res = 0
    for d, r in romans_map:
        while n[i:i + len(r)] == r:
            res += d
            i += len(r)
    return res

re_clean_bister = re.compile(r'(un|duo|tre|bis|qua|quint|quinqu|sex|oct|nov|non|dec|ter|ies)+|pr..?liminaire', re.I)

# Clean html and special chars
lower_inner_title = lambda x: x.group(1)+x.group(3).lower()
html_replace = [
    (re.compile(r" "), " "),
    (re.compile(r"œ", re.I), "oe"),
    (re.compile(r'(«\s+|\s+»)'), '"'),
    (re.compile(r'(«|»|“|”|„|‟|❝|❞|＂|〟|〞|〝)'), '"'),
    (re.compile(r"(’|＇|’|ߴ|՚|ʼ|❛|❜)"), "'"),
    (re.compile(r"(‒|–|—|―|⁓|‑|‐|⁃|⏤)"), "-"),
    (re.compile(r"(</?\w+)[^>]*>"), r"\1>"),
    (re.compile(r"(</?)em>", re.I), r"\1i>"),
    (re.compile(r"(</?)strong>", re.I), r"\1b>"),
    (re.compile(r"<(![^>]*|/?(p|br/?|span))>", re.I), ""),
    (re.compile(r"\s*\n+\s*"), " "),
    (re.compile(r"\s+"), " "),
    (re.compile(r"<[^>]*></[^>]*>"), ""),
    (re.compile(r"^<b><i>", re.I), "<i><b>"),
    (re.compile(r"</?sup>", re.I), ""),
    (re.compile(r'^((<[^>]*>)*"[A-Z])([A-ZÉ]+ )'), lower_inner_title)
]
def clean_html(t):
    for regex, repl in html_replace:
        t = regex.sub(repl, t)
    return t.strip()

re_clean_et = re.compile(r'(,|\s+et)\s+', re.I)
def pr_js(dic):
    # Clean empty articles with only "Supprimé" as text
    if not dic:
        return
    if 'alineas' in dic:
        if len(dic['alineas']) == 1 and dic['alineas']['001'].startswith("(Supprimé)"):
            dic['alineas'] = {'001': ''}
        elif dic['statut'].startswith('conforme') and not len(dic['alineas']):
            dic['alineas'] = {'001': '(Non modifié)'}
        multiples = re_clean_et.sub(',', dic['titre']).split(',')
        if len(multiples) > 1:
            for d in multiples:
                new = dict(dic)
                new['titre'] = d
                print json.dumps(new, sort_keys=True, ensure_ascii=False).encode("utf-8")
            return
    print json.dumps(dic, sort_keys=True, ensure_ascii=False).encode("utf-8")

re_cl_html = re.compile(r"<[^>]+>")
re_cl_par  = re.compile(r"(\(|\))")
re_cl_uno  = re.compile(r"(premier|unique?)", re.I)
re_mat_sec = re.compile(r"((chap|t)itre|volume|livre|tome|(sous-)?section)\s+(.+)e?r?", re.I)
re_mat_art = re.compile(r"articles?\s+([^(]*)(\([^)]*\))?$", re.I)
re_mat_ppl = re.compile(r"(<b>)?pro.* loi", re.I)
re_mat_tco = re.compile(r"\s*<b>\s*TEXTES?\s*DE\s*LA\s*COMMISSION")
re_mat_exp = re.compile(r"(<b>)?expos[eéÉ]", re.I)
re_mat_end = re.compile(r"(<i>Délibéré|Fait à .*, le|\s*©|\s*N.?B.?\s*:)", re.I)
re_mat_dots = re.compile(r"^[.…]+$")
re_mat_st  = re.compile(r"<i>\(?(non\s?-?)?(conform|modif|suppr|nouveau)", re.I)
re_mat_new = re.compile(r"\s*\(no(n[\-\s]modifié|uveau)\s*\)\s*", re.I)
re_clean_idx_spaces = re.compile(r'^([IVXLCDM0-9]+)\s*\.\s*')
re_clean_art_spaces = re.compile(r'^\s*"?\s+')
re_clean_conf = re.compile(r"^\s*\((conforme|non-?modifi..?)s?\)\s*$", re.I)
re_clean_supr = re.compile(r'\(suppr(ession|im..?s?)\s*(conforme|maintenue|par la commission mixte paritaire)?\)["\s]*$', re.I)
re_echec_com = re.compile(r" la commission n'a pas adopté de texte ", re.I)
re_echec_cmp = re.compile(r' ne .* parvenir à élaborer un texte commun', re.I)
re_rap_mult = re.compile(r'[\s<>/aimg]*N[°\s]*\d+\s*(,|et)\s*[N°\s]*\d+', re.I)
re_clean_mult_1 = re.compile(r'\s*et\s*', re.I)
re_clean_mult_2 = re.compile(r'[^,\d]', re.I)
re_sep_text = re.compile(r'\s*<b>\s*(article|titre|chapitre|tome|volume|livre)\s*(I|unique|liminaire|(1|prem)i?e?r?)\s*</b>\s*$', re.I)
re_art_uni = re.compile(r'\s*article\s*unique\s*$', re.I)
read = art_num = ali_num = 0
section_id = ""
article = None
indextext = -1
curtext = -1
section = {"type": "section", "id": ""}
for text in soup.find_all("p"):
    line = clean_html(str(text))
    #print read, curtext, indextext, line
    if indextext != -1 and re_sep_text.match(line):
        curtext += 1
    if re_rap_mult.match(line):
        line = re_cl_html.sub("", line)
        line = re_clean_mult_1.sub(",", line)
        line = re_clean_mult_2.sub("", line)
        for n_t in line.split(','):
            indextext += 1
            if int(n_t) == numero:
                break
    elif re_mat_ppl.match(line) or re_mat_tco.match(line):
        read = 0
        if "done" not in texte:
            pr_js(texte)
        texte["done"] = True
    elif re_mat_exp.match(line):
        read = -1 # Deactivate description lecture
    elif read == -1 or (indextext != -1 and curtext != indextext):
        continue
    # Identify section zones
    elif read != 0 and re_mat_sec.match(line):
        read = 1 # Activate titles lecture
        m = re_mat_sec.match(line)
        section["type_section"] = m.group(1).lower()
        section_typ = m.group(1).upper()[0]
        if m.group(3) is not None:
            section_typ += "S"
        section_num = re_cl_uno.sub("1", m.group(4).strip())
        if re.match(r"\D", m.group(4)):
            section_num = romans(section_num)
        # Get parent section id to build current section id
        section_par = re.sub(r""+section_typ+"\d.*$", "", section["id"])
        section["id"] = section_par + section_typ + str(section_num)
    # Identify titles and new article zones
    elif re_echec_cmp.search(line) or re_echec_com.search(line):
        pr_js({"type": "echec", "texte": re_cl_html.sub("", line).strip()})
        break
    elif re.match(r"(<i>)?<b>", line) or re_art_uni.match(line):
        line = re_cl_html.sub("", line).strip()
        # Read a new article
        if re_mat_art.match(line):
            if article is not None:
                pr_js(article)
            read = 2 # Activate alineas lecture
            art_num += 1
            ali_num = 0
            article = {"type": "article", "order": art_num, "alineas": {}, "statut": "none"}
            m = re_mat_art.match(line)
            article["titre"] = re_cl_uno.sub("1er", m.group(1).strip())
            if m.group(2) is not None:
                article["statut"] = re_cl_par.sub("", str(m.group(2)).lower()).strip()
            if section["id"] != "":
                article["section"] = section["id"]
        # Read a section's title
        elif read == 1:
            section["titre"] = line
            if article is not None:
                pr_js(article)
                article = None
            pr_js(section)
            read = 0
    # Read articles with alineas
    elif read == 2:
        if re_mat_end.match(line):
            break
        # Find extra status information
        elif re_mat_st.match(line):
            article["statut"] = re_cl_html.sub("", re_cl_par.sub("", line.lower()).strip())
            continue
        if re_mat_dots.match(line):
            continue
        line = re_clean_art_spaces.sub('', re_clean_idx_spaces.sub(r'\1. ', re_mat_new.sub(" ", re_cl_html.sub("", line)).strip()))
        # Clean low/upcase issues with BIS TER etc.
        line = re_clean_bister.sub(lambda m: m.group(0).lower(), line)
        # Clean different versions of same comment.
        line = re_clean_supr.sub('(Supprimé)', line)
        line = re_clean_conf.sub('(Non modifié)', line)
        # Clean comments (Texte du Sénat), (Texte de la Commission), ...
        if ali_num == 0 and line.startswith('(Texte d'):
            continue
        ali_num += 1
        article["alineas"]["%03d" % ali_num] = line
    else:
        #metas
        continue
pr_js(article)


