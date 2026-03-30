"""
fetch_data.py
GitHub Actions üzerinde çalışır, verileri çekip data.json olarak kaydeder.
"""

import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

TR_TZ = timezone(timedelta(hours=3))

def guncel_fiyat(ticker):
    try:
        h = yf.Ticker(ticker).history(period="2d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except:
        return None

def aylik_degisim_yuzde(ticker):
    try:
        h = yf.Ticker(ticker).history(period="35d")
        if len(h) < 5:
            return None
        son = float(h["Close"].iloc[-1])
        onceki = float(h["Close"].iloc[-22]) if len(h) >= 22 else float(h["Close"].iloc[0])
        return round((son / onceki - 1) * 100, 2)
    except:
        return None

def trend_yonu(ticker, gun=22):
    try:
        h = yf.Ticker(ticker).history(period="60d")
        if len(h) < gun:
            return ""
        pct = (float(h["Close"].iloc[-1]) / float(h["Close"].iloc[-gun]) - 1) * 100
        return "yukselis" if pct > 3 else "dusus" if pct < -3 else "yatay"
    except:
        return ""

def sp500_ma200():
    try:
        h = yf.Ticker("^GSPC").history(period="1y")
        if len(h) < 200:
            return ""
        return "ustunde" if float(h["Close"].iloc[-1]) > float(h["Close"].tail(200).mean()) else "altinda"
    except:
        return ""

def yield_spread_bps():
    try:
        h10 = yf.Ticker("^TNX").history(period="5d")
        h2  = yf.Ticker("^IRX").history(period="5d")
        if h10.empty or h2.empty:
            return None
        return round((float(h10["Close"].iloc[-1]) - float(h2["Close"].iloc[-1])) * 100, 1)
    except:
        return None

def bakir_altin_orani():
    try:
        b = guncel_fiyat("HG=F")
        a = guncel_fiyat("GC=F")
        return round(b / a, 6) if b and a and a > 0 else None
    except:
        return None

def move_endeksi():
    v = guncel_fiyat("^MOVE")
    if v:
        return round(v, 1)
    try:
        r = requests.get("https://www.investing.com/rates-bonds/ice-bofaml-move-index", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        el = soup.find("span", {"data-test": "instrument-price-last"})
        if el:
            return round(float(el.text.strip().replace(",", "")), 1)
    except:
        pass
    return None

def tr_cds():
    try:
        url = "http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        tablo = soup.find("table")
        if tablo:
            for satir in tablo.find_all("tr")[1:3]:
                hucreler = satir.find_all("td")
                if len(hucreler) >= 2:
                    try:
                        return round(float(hucreler[1].text.strip().replace(",", "")), 1)
                    except:
                        pass
    except:
        pass
    return None

def tcmb_faizi():
    try:
        import re
        r = requests.get(
            "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Para+Politikasi/Para+Politikasi+Kararlari",
            headers=HEADERS, timeout=10
        )
        metin = BeautifulSoup(r.text, "html.parser").get_text()
        for e in re.findall(r'yüzde\s+(\d+[\.,]?\d*)', metin, re.IGNORECASE):
            try:
                val = float(e.replace(",", "."))
                if 5 <= val <= 60:
                    return val
            except:
                pass
    except:
        pass
    return None

def tcmb_yonu():
    try:
        r = requests.get(
            "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Para+Politikasi/Para+Politikasi+Kararlari",
            headers=HEADERS, timeout=10
        )
        metin = BeautifulSoup(r.text, "html.parser").get_text().lower()
        if any(k in metin for k in ["düşür", "indirdi", "indirim"]):
            return "indirim"
        elif any(k in metin for k in ["artırdı", "artırım", "yükseltti"]):
            return "artis"
        return "sabit"
    except:
        return ""

def fed_indirim():
    try:
        url = "https://www.cmegroup.com/CmeWS/mvc/SmallInterestRates/getFedWatchToolData.json"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            data = r.json()
            meetings = data.get("meetings", [])
            if meetings:
                ease = meetings[0].get("probabilities", {}).get("LOWER", None)
                if ease is not None:
                    return round(float(ease), 1)
    except:
        pass
    return None

def abd_cpi():
    try:
        payload = {"seriesid": ["CUUR0000SA0"], "startyear": "2024", "endyear": "2026"}
        r = requests.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=payload, timeout=15)
        data = r.json()
        if data.get("status") == "REQUEST_SUCCEEDED":
            seriler = data["Results"]["series"][0]["data"]
            if len(seriler) >= 13:
                return round((float(seriler[0]["value"]) / float(seriler[12]["value"]) - 1) * 100, 1)
    except:
        pass
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", timeout=10)
        lines = [l for l in r.text.strip().split("\n")[1:] if "." not in l.split(",")[-1] or l.split(",")[-1].strip() != "."]
        vals = []
        for line in lines:
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() != ".":
                try:
                    vals.append(float(parts[1].strip()))
                except:
                    pass
        if len(vals) >= 13:
            return round((vals[-1] / vals[-13] - 1) * 100, 1)
    except:
        pass
    return None

def abd_issizlik():
    try:
        payload = {"seriesid": ["LNS14000000"], "startyear": "2025", "endyear": "2026"}
        r = requests.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=payload, timeout=15)
        data = r.json()
        if data.get("status") == "REQUEST_SUCCEEDED":
            seriler = data["Results"]["series"][0]["data"]
            if seriler:
                return float(seriler[0]["value"])
    except:
        pass
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE", timeout=10)
        for line in reversed(r.text.strip().split("\n")[1:]):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() != ".":
                try:
                    return float(parts[1].strip())
                except:
                    pass
    except:
        pass
    return None


def haber_cek():
    """
    Piyasa haberlerini RSS kaynaklardan çeker.
    Birden fazla kaynak denenir, ilk çalışan kullanılır.
    """
    haberler = []

    feeds = [
        # Yahoo Finance RSS (en güvenilir)
        ("Piyasa", "https://finance.yahoo.com/rss/topfinstories"),
        ("ABD Piyasa", "https://finance.yahoo.com/news/rssindex"),
        # Reuters alternatif endpoint
        ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
        ("Reuters Markets", "https://feeds.reuters.com/reuters/financials"),
        # CNBC
        ("CNBC Markets", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
        ("CNBC Economy", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
        # MarketWatch
        ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
        # Investing.com
        ("Investing", "https://www.investing.com/rss/news.rss"),
        ("Investing Emtia", "https://www.investing.com/rss/news_14.rss"),
        # Seekingalpha ücretsiz
        ("SeekingAlpha", "https://seekingalpha.com/market_currents.xml"),
    ]

    for kategori, url in feeds:
        if len(haberler) >= 20:
            break
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                print(f"  [{kategori}] HTTP {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item")
            if not items:
                # html.parser ile tekrar dene
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.find_all("item")
            print(f"  [{kategori}] {len(items)} haber bulundu")
            for item in items[:5]:
                title = item.find("title")
                link  = item.find("link")
                pub   = item.find("pubDate")
                source = item.find("source")
                if not title:
                    continue
                baslik = title.text.strip()
                if not baslik or len(baslik) < 10:
                    continue
                link_url = ""
                if link:
                    link_url = link.text.strip()
                    if not link_url.startswith("http"):
                        # Atom format - link next sibling olabilir
                        sib = link.next_sibling
                        if sib:
                            link_url = str(sib).strip()
                haberler.append({
                    "baslik":   baslik,
                    "link":     link_url,
                    "kaynak":   source.text.strip() if source else kategori,
                    "kategori": kategori,
                    "tarih":    pub.text.strip() if pub else "",
                })
        except Exception as e:
            print(f"  [{kategori}] hata: {e}")

    # Duplikat temizle
    gorulen = set()
    temiz = []
    for h in haberler:
        key = h["baslik"][:50].lower()
        if key not in gorulen:
            gorulen.add(key)
            temiz.append(h)

    print(f"  haberler: toplam {len(temiz)} tekil haber")
    return temiz[:20]


def fetch_all():
    print("Veri çekiliyor...")
    now_tr = datetime.now(TR_TZ)

    adimlar = [
        ("vix",          lambda: round(guncel_fiyat("^VIX"), 2) if guncel_fiyat("^VIX") else None),
        ("move",         move_endeksi),
        ("dxy",          lambda: round(guncel_fiyat("DX-Y.NYB"), 2) if guncel_fiyat("DX-Y.NYB") else None),
        ("usdtl_change", lambda: aylik_degisim_yuzde("TRY=X")),
        ("us10y",        lambda: round(guncel_fiyat("^TNX"), 2) if guncel_fiyat("^TNX") else None),
        ("spread",       yield_spread_bps),
        ("fed_cut",      fed_indirim),
        ("cds",          tr_cds),
        ("tcmb",         tcmb_faizi),
        ("tcmb_dir",     tcmb_yonu),
        ("gold",         lambda: round(guncel_fiyat("GC=F"), 1) if guncel_fiyat("GC=F") else None),
        ("brent",        lambda: round(guncel_fiyat("BZ=F"), 1) if guncel_fiyat("BZ=F") else None),
        ("cuau",         bakir_altin_orani),
        ("msci_dir",     lambda: trend_yonu("EEM")),
        ("sp500_dir",    lambda: trend_yonu("^GSPC")),
        ("sp500_ma",     sp500_ma200),
        ("unemployment", abd_issizlik),
        ("us_cpi",       abd_cpi),
    ]

    veriler = {}
    for anahtar, fn in adimlar:
        try:
            val = fn()
            veriler[anahtar] = val
            durum = f"✓ {val}" if val is not None and val != "" else "✗ boş"
            print(f"  {anahtar:<15} {durum}")
        except Exception as e:
            veriler[anahtar] = None
            print(f"  {anahtar:<15} ✗ hata: {e}")

    # Haberleri çek
    veriler["haberler"] = haber_cek()
    veriler["guncelleme"] = now_tr.strftime("%d.%m.%Y %H:%M")
    veriler["timestamp"]  = now_tr.isoformat()
    return veriler

if __name__ == "__main__":
    data = fetch_all()
    Path("data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print("\n✓ data.json kaydedildi")
    print(json.dumps(data, ensure_ascii=False, indent=2))
