import json, urllib.request, urllib.error
UA={"User-Agent":"Mozilla/5.0 (husjagt)","Accept":"application/json"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
    except Exception as e: return 0, str(e)
for u in ["https://api.boligsiden.dk/search/cases?addressTypes=villa&zipCodes=9230&per_page=2",
          "https://api.boligsiden.dk/search/cases?addressTypes=villa&zipCode=9230&per_page=2",
          "https://api.boligsiden.dk/search/cases?zipCodes=9230&per_page=2",
          "https://api.boligsiden.dk/search/cases?municipalities=aalborg&addressTypes=villa&per_page=2"]:
    s,b=get(u); print("==",s,u); 
    try:
        d=json.loads(b); print("keys:",list(d)[:10]); c=(d.get("cases") or [None])[0]
        print(json.dumps(c,ensure_ascii=False)[:2500] if c else b[:400])
    except Exception: print(b[:400])
s,b=get("https://api.boliga.dk/api/v2/search/results?zipCodes=9230&propertyType=1&pageSize=1")
i=json.loads(b)["results"][0]["id"]
for u in [f"https://api.boliga.dk/api/v2/estate/{i}"]:
    s,b=get(u); print("==",s,u)
    try:
        d=json.loads(b); print("keys:",list(d)); print({k:v for k,v in d.items() if 'bath' in k.lower() or 'toilet' in k.lower() or 'bad' in k.lower()})
    except Exception: print(b[:400])
