import json, urllib.request, urllib.error
UA={"User-Agent":"Mozilla/5.0 (husjagt)","Accept":"application/json"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
B="https://api.boligsiden.dk/search/cases?"
for q in ["addressTypes=villa&zipCodes=9230&per_page=50","addressTypes=villa&zipCodes=9230,9530&per_page=50",
          "addressTypes=villa&zipCodes=9230&zipCodes=9530&per_page=50","addressTypes=villa&zipCodes=9230&priceMax=4000000&per_page=50",
          "addressTypes=villa&zipCodes=9230&per_page=50&page=2","addressTypes=villa&zipCodes=9230&per_page=100"]:
    s,d=get(B+q)
    if isinstance(d,dict):
        cs=d.get("cases") or []
        print("==",s,q,"total:",d.get("totalHits"),"n:",len(cs),"zips:",sorted({c.get("address",{}).get("zipCode") for c in cs})[:8],"maxpris:",max([c.get("priceCash") or 0 for c in cs] or [0]))
    else: print("==",s,q,d)
s,d=get(B+"addressTypes=villa&zipCodes=9230&per_page=1")
c=d["cases"][0]; c2={k:v for k,v in c.items() if k!="address"}
print(json.dumps(c2,ensure_ascii=False)[:3000])
