"""Independent stochastic reference prices; cash/inventory/depth-limited quotes."""
import math
import numpy as np


class ReferenceDealer:
    def __init__(self,prices,depth,spread=.001):
        self.z=np.asarray(prices,dtype=float).copy()
        self.L=np.broadcast_to(np.asarray(depth,dtype=float),self.z.shape).copy()
        if np.any(self.z<=0) or np.any(self.L<=0) or not 0<=spread<1:
            raise ValueError("Invalid external market")
        self.spread=spread
        self.u=np.zeros_like(self.z)

    def refresh(self,prices):
        z=np.asarray(prices,dtype=float)
        if np.any(z<=0) or not np.all(np.isfinite(z)):raise ValueError("Invalid reference prices")
        self.z=z.copy()
        self.u.fill(0)

    def max_buy(self,i):return max(0.,self.L[i]/2-self.u[i])
    def max_sell(self,i):return max(0.,self.L[i]/2+self.u[i])

    def quote(self,i,d,side):
        if not math.isfinite(d) or d<=0 or side not in ("buy","sell"):raise ValueError("Invalid external trade")
        limit=self.max_buy(i) if side=="buy" else self.max_sell(i)
        if d>limit+1e-14:raise ValueError("External depth exhausted")
        sign=1 if side=="buy" else -1
        return self.z[i]*((1+self.u[i]/self.L[i])*d+sign*d*d/(2*self.L[i]))*(1+sign*self.spread)

    def trade(self,i,d,side):
        value=self.quote(i,d,side)
        self.u[i]+=(1 if side=="buy" else -1)*d
        return value

    def marginal(self,i,side):
        return self.z[i]*(1+self.u[i]/self.L[i])*(1+self.spread if side=="buy" else 1-self.spread)
