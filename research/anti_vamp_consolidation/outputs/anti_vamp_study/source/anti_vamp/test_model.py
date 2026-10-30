import unittest
from dataclasses import replace
from collections import defaultdict
from model import Environment,Mechanism,Policy,World,make_tape,digest,M,Q
from ledger import Book

A=Mechanism()
O=Mechanism('original_first','original')
E=Mechanism('elected_2m','cap',120)

class AntiVampTests(unittest.TestCase):
    def run_world(self,e=Environment(),m=O,p=Policy(),seed=3000):
        w=World(e,m,make_tape(seed,e.opportunities,e.half_life),p);w.run();return w

    def test_common_budget_not_multiplied_by_copies(self):
        results=[]
        for n in (10,50,100):
            w=self.run_world(replace(Environment(),coins=n))
            results.append((w.b.initial,w.t['hash'],sum(r['budget'] for r in w.t['visits'])))
        self.assertEqual(len(set(results)),1)

    def test_no_creator_seed_or_free_redeemable_allocation(self):
        w=World(Environment(),O,make_tape(3000));w.b.time=0;w.launch(0)
        self.assertEqual(sum(w.b.q),0)
        self.assertEqual(w.b.cash.get('platform_launch',0),0)

    def test_no_copy_benchmark_keeps_same_world_funding(self):
        w=self.run_world(replace(Environment(),coins=1),A)
        self.assertEqual(w.b.initial,39100*M)
        self.assertEqual(w.observations[1]['original_share'],1)

    def test_original_is_first_in_default(self):
        w=self.run_world()
        self.assertEqual(w.lead,0)
        self.assertEqual(min(w.launch_time,key=w.launch_time.get),0)

    def test_preclaim_does_not_use_authenticity_oracle(self):
        w=self.run_world(replace(Environment(),preclaim=True))
        self.assertEqual(w.lead,1)
        self.assertEqual(w.launch_time[1],-1)

    def test_late_copy_cannot_replace_fixed_original(self):
        w=self.run_world(replace(Environment(),first_copy=600))
        self.assertEqual(w.lead,0)

    def test_zero_reach_matches_independent(self):
        e=replace(Environment(),reach=0)
        a,o=self.run_world(e,A),self.run_world(e,O)
        self.assertEqual(dict(a.b.cash),dict(o.b.cash));self.assertEqual(a.b.q,o.b.q)

    def test_no_consent_matches_independent(self):
        e=replace(Environment(),acceptance=0)
        a,o=self.run_world(e,A),self.run_world(e,O)
        self.assertEqual(dict(a.b.cash),dict(o.b.cash));self.assertEqual(a.b.q,o.b.q)

    def test_election_has_no_routing_before_close(self):
        w=self.run_world(m=E)
        self.assertTrue(all(t>=120 for t,source,target,gross in w.routes))

    def test_original_router_is_active_before_election(self):
        w=self.run_world(replace(Environment(),reach=1,acceptance=1))
        self.assertTrue(any(t<120 for t,source,target,gross in w.routes))

    def test_refused_order_keeps_its_received_mint(self):
        w=self.run_world(replace(Environment(),acceptance=0))
        self.assertEqual(len(w.routes),0)
        self.assertTrue(all(i==desired for t,i,principal,gross,desired in w.buys))

    def test_copy_redirect_does_not_burn_old_claims(self):
        w=self.run_world(replace(Environment(),reach=1,acceptance=1))
        self.assertTrue(all(target==0 for t,source,target,gross in w.routes))
        self.assertEqual(w.counter['redirected_original'],0)

    def test_sale_uses_only_associated_lot(self):
        w=World(Environment(),O,make_tape(3000));w.launch(0)
        x=w.buy('u:0',0,20*M);y=w.buy('u:0',0,20*M)
        w.lots={1:['u:0',0,x.quantity],2:['u:0',0,y.quantity]}
        before=w.b.q[0];w.exit_visit(dict(id=1,sell_fraction=.5))
        self.assertEqual(before-w.b.q[0],int(x.quantity*.5));self.assertEqual(w.lots[2][2],y.quantity)

    def test_invariants_under_attack(self):
        w=self.run_world(p=Policy(1,16,2000,900));self.assertTrue(w.b.invariant())
        self.assertEqual(w.observations[-1]['actor_residual'],0)

    def test_deterministic_replay(self):
        a,b=self.run_world(m=E),self.run_world(m=E)
        self.assertEqual(digest(a.observations),digest(b.observations))
        self.assertEqual(a.minutes,b.minutes)

    def test_unfunded_or_empty_election_uses_direct_markets(self):
        w=self.run_world(m=Mechanism('too_early','cap',0))
        self.assertIsNone(w.lead);self.assertEqual(len(w.routes),0)

    def test_optimized_invariant_agrees_with_reference(self):
        w=self.run_world()
        self.assertEqual(w.b.invariant(),Book.invariant(w.b))

    def test_flow_includes_missing_execution(self):
        w=self.run_world(replace(Environment(),rejection='leave',reach=1,acceptance=0))
        self.assertTrue(any(row['fill_to_latent'] is not None and row['fill_to_latent']<.9 for row in w.minutes))

    def test_true_original_and_elected_leader_are_separate(self):
        w=self.run_world(replace(Environment(),viral_copy=True),E,Policy(1,16,2000,900))
        for row in w.observations:
            self.assertIsNotNone(row['original_depth'])
            self.assertEqual(len(__import__('json').loads(row['depth_vector'])),10)

if __name__=='__main__':unittest.main()
