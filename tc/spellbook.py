import json,re
SKILL={'warrior':[26,256,257],'paladin':[594,267,184],'hunter':[50,163,51],'rogue':[253,38,39],
 'priest':[613,56,78],'shaman':[375,373,374],'mage':[237,8,6],'warlock':[355,354,593],'druid':[574,134,573]}
def num(x):
    v=float(x); return str(int(round(v))) if abs(v-round(v))<.05 or v>20 else f'{v:.1f}'
def clean(d):
    d=re.sub(r"\[<span class='q2'>[^<]*</span>: <span class='q9'>(.*?)</span>(?: / (.*?))?\]",lambda m:m.group(2) or '',d)
    d=re.sub(r'<!--.*?-->','',d)
    d=re.sub(r'<dfn title="[^"]*">(.*?)</dfn>',r'\1',d)
    d=re.sub(r'<br ?/?>','\n',d)
    d=re.sub(r'<[^>]+>','',d)
    def ev(m):
        e=m.group(1)
        if not re.search(r'\d\s*[-+*/]\s*[\d.]',e): return m.group(0) if m.group(0)[0]=='[' else e.strip()
        try: return num(eval(e))
        except Exception: return m.group(0)
    for _ in range(6):
        d=re.sub(r'\(([0-9.\s+\-*/]+)\)',ev,d)
        d=re.sub(r'\[([0-9.\s+\-*/]+)\]',ev,d)
    d=re.sub(r'\(\s*([0-9.]+)\s*\)',r'\1',d)
    d=re.sub(r'\[\((.*?)\)\s*\*\s*1\]',r'(\1)',d)
    d=re.sub(r'[ \t]{2,}',' ',d).replace(' .','.').strip()
    return d
def gen(cls):
    G=[]
    def a(n,ic,sub,desc,lv=None): G.append([n,ic,sub,desc,lv])
    a('Attack','inv_sword_04','','Starts and stops your melee auto-attack.')
    a('Dodge','spell_nature_invisibilty','Passive','Gives a chance to dodge enemy melee attacks.')
    if cls in ('warrior','paladin','rogue','hunter'): a('Parry','ability_parry','Passive','Gives a chance to parry enemy melee attacks.')
    if cls in ('warrior','paladin','shaman'): a('Block','ability_defend','Passive','Gives a chance to block enemy melee and ranged attacks.')
    if cls in ('warrior','rogue','hunter'): a('Dual Wield','ability_dualwield','Passive','Allows one-hand and off-hand weapons to be equipped in the off-hand.',10 if cls=='rogue' else 20)
    if cls in ('warrior','rogue'):
        a('Throw','ability_throw','','Hurl a thrown weapon at the target.')
        for w in ('Bow','Gun','Crossbow'): a('Shoot '+w,'ability_marksmanship','','Shoot a ranged weapon at the target.')
    if cls in ('priest','mage','warlock'): a('Shoot','ability_shootwand','','Attack with an equipped wand.')
    if cls in ('priest','mage','warlock'): arm=[('Cloth','inv_chest_cloth_21',None)]
    elif cls in ('rogue','druid'): arm=[('Leather','inv_chest_leather_09',None)]
    elif cls in ('hunter','shaman'): arm=[('Leather','inv_chest_leather_09',None),('Mail','inv_chest_chain_05',40)]
    else: arm=[('Mail','inv_chest_chain_05',None),('Plate Mail','inv_chest_plate01',40)]
    for n,ic,lv in arm: a(n,ic,'Armor Proficiency'+(f' · Level {lv}' if lv else ''),f'Allows the wearing of {n.lower()} armor.' if n!='Shield' else 'Allows the use of shields.',lv)
    return G
def norm(t): return re.sub(r'[^a-z#]','',re.sub(r'\d+(?:\.\d+)?','#',t.lower()))
def ranks(c,name,topdesc):
    e=RK.get(c,{}).get(name)
    if not e: return None
    rows=[]
    for rk,lv,v in e['r']:
        if rk<1: continue
        if 't' in e:
            nums=v.split(',') if v else []; it=iter(nums)
            d=re.sub('#',lambda m:next(it,'#'),e['t'])
        else: d=v
        rows.append((rk,lv,d))
    tn=norm(clean(topdesc))
    out={}
    for rk,lv,d in rows:
        cd=clean(d)
        if rk not in out or (norm(cd)==tn and norm(out[rk][2])!=tn): out[rk]=[rk,lv,cd]
    r=[out[k] for k in sorted(out)]
    pr=RKD.get(c,{}).get(name,{})
    for row in r:
        x=pr.get(str(row[0]))
        if x: row.append(x)
    return r if len(r)>1 else None
RK={}
RKD={}
# Season of Discovery leftovers in Wowhead's Forever data with no trainer source
DROP={'Aspect of the Falcon','Hammer of the Righteous','Portal of Summoning','Coup de Grace','Enchanted Flare','Lightwell'}
def build():
    global RK,RKD
    RK=json.load(open('ranks_raw.json', encoding='utf-8'))
    import os
    if os.path.exists('rank_tips.json'): RKD=json.load(open('rank_tips.json', encoding='utf-8'))
    raw=json.load(open('spells_raw.json', encoding='utf-8')); R=json.load(open('racials.json', encoding='utf-8'))
    out={}
    for c,sk in SKILL.items():
        sp=[]
        for n,ic,s,lv,rk,d,i in raw[c]:
            if n in DROP: continue
            sp.append([n,ic,sk.index(s) if s in sk else 0,lv,rk,clean(d),i,ranks(c,n,d)])
        out[c]={'spells':sp,'general':gen(c)}
    import os
    out['det']=json.load(open('details.json', encoding='utf-8')) if os.path.exists('details.json') else {}
    out['priestRacial']=sorted({p[0] for r in R for p in r['priest']})
    return out
if __name__=='__main__':
    o=build(); import sys
    for c in ('rogue','mage','warlock'):
        for s in o[c]['spells'][:60]:
            if any(ch in s[5] for ch in '[]$<'): print(c,s[0],'|',s[5][:200])
    print([s[5] for s in o['rogue']['spells'] if s[0] in('Eviscerate','Slice and Dice')])
    print([s[5] for s in o['mage']['spells'] if s[0] in('Frostbolt','Fire Ward')], [s[5] for s in o['warlock']['spells'] if s[0]=='Immolate'])
