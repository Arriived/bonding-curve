"""Transaction-boundary elections; O(1) amortized first-address volume windows."""
from collections import deque
import numpy as np


class Election:
    def __init__(self,variant,matcher,launches,active,book):
        self.v=variant;self.matcher=matcher;self.launches=launches;self.active=active;self.book=book
        self.leaders={};self.changed={};self.champion={};self.since={}
        self.vol=np.zeros(len(active));self.distinct=np.zeros(len(active),dtype=int)
        self.queue=deque();self.wallets={};self.switches=0

    def record(self,t,token,wallet,gross,side="buy"):
        if self.v.rule!="volume" or (side!="buy" and self.v.volume_mode!="raw"):return
        if self.v.changes=="fixed" and self.leader(token) is not None:return
        key=(token,wallet)
        q=self.wallets.setdefault(key,deque())
        if not q:self.distinct[token]+=1;self.vol[token]+=gross
        elif self.v.volume_mode=="raw":self.vol[token]+=gross
        q.append((t,gross));self.queue.append((t,token,wallet,gross))

    def refresh(self,t):
        v=self.v
        if v.rule=="first":
            for group,members in self.matcher.groups.items():
                if self.leaders.get(group) is None:
                    self.leaders[group]=min(members,key=lambda i:(self.launches[i],i));self.changed[group]=t
            return
        if v.changes=="fixed" and self.matcher.groups and all(self.leaders.get(g) is not None for g in self.matcher.groups):return
        while self.queue and self.queue[0][0]<t-v.window:
            _,token,wallet,gross=self.queue.popleft();q=self.wallets[(token,wallet)]
            q.popleft();self.vol[token]-=gross
            if not q:self.distinct[token]-=1
            elif v.volume_mode!="raw":self.vol[token]+=q[0][1]
        q=self.book.q
        cap=(self.book.p0+self.book.k*q)*q
        for group,members in self.matcher.groups.items():
            old=self.leaders.get(group)
            if old is not None and v.changes=="fixed":continue
            candidate=None
            if v.rule=="first":candidate=min(members,key=lambda i:(self.launches[i],i))
            elif v.rule=="threshold":
                eligible=[i for i in members if cap[i]>=v.threshold]
                if eligible:candidate=max(eligible,key=lambda i:(cap[i],-self.launches[i],-i))
            elif v.rule=="held":
                eligible=[i for i in members if t-self.launches[i]>=v.min_age and q[i]>1e-12]
                champ=max(eligible,key=lambda i:(cap[i],-self.launches[i],-i)) if eligible else None
                if champ!=self.champion.get(group):self.champion[group]=champ;self.since[group]=t
                if champ is not None and t-self.since.get(group,t)>=v.window-1e-9:candidate=champ
                elif old is not None:continue # incumbent remains during challenger dwell
            else:
                eligible=[i for i in members if t-self.launches[i]>=v.min_age and self.distinct[i]>=3]
                if eligible:candidate=max(eligible,key=lambda i:(self.vol[i],-self.launches[i],-i))
            if candidate==old:continue
            if v.changes=="cooldown" and old is not None and t-self.changed.get(group,-1e9)<v.cooldown:continue
            if old is not None and candidate is not None:self.switches+=1
            self.leaders[group]=candidate;self.changed[group]=t

    def leader(self,token):return self.leaders.get(self.matcher.token_group.get(token))
