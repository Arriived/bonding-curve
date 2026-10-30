import unittest
from dataclasses import replace
from open_model import Setting, Strategy, OpenWorld, tape_for, M
from upstream.ledger import reserve, Book, Refused, TOKEN as Q

class OpenLaunchTests(unittest.TestCase):
    def world(self, s=Setting(), arch='C', policy=Strategy(), seed=2001):
        w=OpenWorld(s,arch,tape_for(seed,s),policy)
        w.run()
        return w

    def test_funded_world(self):
        self.assertEqual(self.world().b.initial,39100*M)

    def test_no_dev_seed(self):
        s=Setting();w=OpenWorld(s,'A',tape_for(2001,s))
        for row in w.t['open_launches']:w.launch(row)
        self.assertEqual(sum(w.b.q),0)

    def test_free_still_pays_network(self):
        w=self.world()
        self.assertEqual(w.b.cash['platform_launch'],0)
        self.assertGreater(w.b.cash['network'],0)
        self.assertEqual(sum(v for k,v in w.b.cash.items() if k.startswith('account_deposit:')),200000)

    def test_no_cash_creation_by_spam(self):
        for n in (0,10,90):self.assertEqual(self.world(Setting(spam=n)).b.initial,39100*M)

    def test_zero_reach_is_control(self):
        s=Setting(reach=0)
        a,c=self.world(s,'A'),self.world(s,'C')
        self.assertEqual(dict(a.b.cash),dict(c.b.cash))
        self.assertEqual(a.b.q,c.b.q)

    def test_refusal_direct_is_control(self):
        s=Setting(acceptance=0,reject_preferred=1,reject_outside=0)
        a,c=self.world(s,'A'),self.world(s,'C')
        self.assertEqual(a.b.q,c.b.q)
        self.assertEqual(dict(a.b.cash),dict(c.b.cash))

    def test_sponsor_has_finite_balance(self):
        s=Setting(spam=90,sponsor_launch=True)
        w=self.world(s)
        self.assertEqual(w.b.cash['sponsor'],97*M)

    def test_unaffordable_launch_rejected_before_cost(self):
        s=Setting(launch_fee=6000*M,spam=1)
        w=OpenWorld(s,'C',tape_for(2001,s))
        w.launch(w.t['open_launches'][-1])
        self.assertEqual(w.b.cash['attacker'],5000*M)
        self.assertEqual(len(w.live),0)

    def test_late_entry_cannot_reopen_election(self):
        w=self.world(Setting(spam=90,late_spam=True))
        self.assertEqual(len(w.live),100)
        self.assertTrue(all(i<10 for i in w.members))

    def test_alias_budget_shared(self):
        w=self.world(policy=Strategy(3000,.85,1,32))
        self.assertGreaterEqual(min(w.b.cash.values()),0)
        self.assertEqual(w.snapshots[-1]['attacker_residual'],0)

    def test_daily_cap_holds(self):
        w=self.world(Setting(route_cap=.25))
        cap=w.close_backing//4
        self.assertTrue(all(v<=cap for v in w.daily.values()))

    def test_route_expiry(self):
        w=self.world(Setting(route_hours=0))
        self.assertEqual(w.count['routed'],0)

    def test_router_fee_funded(self):
        w=self.world(Setting(router_bps=45))
        self.assertEqual(w.b.cash['router_fees'],w.count['router_fee'])
        self.assertGreater(w.count['router_fee'],0)

    def test_observable_time_score(self):
        w=self.world(Setting(rule='timecap'))
        self.assertGreater(sum(w.score_area.values()),0)
        self.assertTrue(w.winner in w.members)

    def test_minimum_age(self):
        w=self.world(Setting(spam=10,min_age=2000))
        self.assertIsNone(w.winner)

    def test_deterministic_replay(self):
        a,b=self.world(Setting(spam=10)),self.world(Setting(spam=10))
        self.assertEqual(a.snapshots,b.snapshots)
        self.assertEqual(dict(a.b.cash),dict(b.b.cash))

    def test_reference_exit_witness(self):
        b=Book(1,0,0,0)
        b.fund('alice',30*M);b.fund('bob',30*M)
        total=1000*Q;half=total//2
        b.transfer('alice','market:0',30*M);b.transfer('bob','market:0',30*M)
        b.q[0]=total;b.hold['alice',0]=half;b.hold['bob',0]=half;b.holder_count[0]=2
        self.assertEqual(b.sell('alice',0,half).principal,42_500_000)
        self.assertEqual(b.sell('bob',0,half).principal,17_500_000)
        b.invariant()

    def test_outside_candidates_still_count_in_cohort(self):
        w=self.world(Setting(outside_creators=1))
        self.assertEqual(w.snapshots[-2]['platform_reserve'],0)
        self.assertGreater(w.snapshots[-2]['cohort_reserve'],0)

if __name__=='__main__':unittest.main()
