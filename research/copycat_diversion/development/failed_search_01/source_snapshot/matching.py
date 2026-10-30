"""Explicit ticker groups; semantic campaign membership is a separate variable."""
import unicodedata


def normalize(ticker,mode):
    if mode=="exact":return ticker
    if mode=="case":return ticker.casefold()
    t=unicodedata.normalize("NFKC",ticker).upper().replace("0","O")
    return "".join(c for c in t if not c.isdigit() and not c.isspace())


def near(a,b):
    if a==b:return True
    if abs(len(a)-len(b))>1:return False
    if len(a)==len(b):return sum(x!=y for x,y in zip(a,b))<=1
    if len(a)>len(b):a,b=b,a
    i=j=errors=0
    while i<len(a) and j<len(b):
        if a[i]==b[j]:i+=1;j+=1
        else:
            errors+=1;j+=1
            if errors>1:return False
    return True


class Matcher:
    def __init__(self,mode):
        if mode not in ("exact","case","fuzzy"):raise ValueError("Unknown matcher")
        self.mode=mode;self.anchors=[];self.groups={};self.token_group={}

    def admit(self,token,ticker):
        text=normalize(ticker,self.mode)
        key=None
        for j,anchor in enumerate(self.anchors):
            if text==anchor or (self.mode=="fuzzy" and near(text,anchor)):
                key=j;break
        if key is None:key=len(self.anchors);self.anchors.append(text);self.groups[key]=[]
        self.groups[key].append(token);self.token_group[token]=key
        return key
