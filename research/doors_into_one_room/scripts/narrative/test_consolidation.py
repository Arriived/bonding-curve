"""Regression checks on real cached outcomes; no simulated market measurements."""
import contextlib
import hashlib
import io
import sys
import unittest
from unittest import mock

import collect_consolidation_outcomes as C
import collect_consolidation_balances as B
import measure_consolidation_value as V


class ConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups,cls.original,cls.launches=V.load_groups()

    def test_complete_cohort_units_and_partition(self):
        sol={r['mint'] for r in self.original if r.get('sol_quoted') is True}
        pooled=[m['mint'] for g in self.groups for m in g['members']]
        self.assertEqual(set(pooled),sol)
        self.assertEqual(len(pooled),len(sol))
        self.assertEqual(len(self.original),len(self.launches))
        self.assertEqual(sum(g['member_count'] for g in self.groups),len(sol))
        for g in self.groups:
            amounts=[m['real_sol_reserve_lamports'] for m in g['members']]
            self.assertEqual(g['sum_lamports'],sum(amounts))
            self.assertEqual(g['max_lamports'],max(amounts))
            self.assertGreaterEqual(g['nonlargest_lamports'],0)

    def test_completed_money_is_restored_without_creating_new_graduations(self):
        complete=[m for g in self.groups for m in g['members'] if m['complete']]
        self.assertTrue(complete)
        self.assertEqual(sum(m['curve_reserve_lamports'] for m in complete),0)
        self.assertGreater(sum(m['pool_reserve_lamports'] for m in complete),0)
        eligible=[g for g in self.groups if not g['any_completed']]
        trigger=int(V.R_STAR*V.LAMPORTS)+V.graduation_rent_lamports()
        for cut in (1,10**9,trigger):
            self.assertEqual(V.threshold_counts(self.groups,cut),V.threshold_counts(eligible,cut))
            counts=V.threshold_counts(self.groups,cut)
            self.assertEqual(counts['separate_current_max_above']+counts['additional_candidates'],counts['current_sum_above'])

    def test_missing_accounts_and_zero_totals_do_not_create_evidence(self):
        self.assertIsNone(C.decode(None)['real_quote_reserves_raw'])
        self.assertIsNone(B.decode_pool(None,None,'unused',{})['real_pool_quote_lamports'])
        zero=[g for g in self.groups if g['sum_lamports']==0]
        for g in zero:self.assertIsNone(g['copy_money_share'])
        stats=V.distribution(zero)
        self.assertIsNone(stats['weighted_mean'])
        self.assertIsNone(stats['median'])

    def test_pooled_weighting_conserves_money_across_both_completion_classes(self):
        first=[g for g in self.groups if g['any_completed']]
        second=[g for g in self.groups if not g['any_completed']]
        a,b,all_=map(V.distribution,(first,second,self.groups))
        self.assertEqual(a['reserve_lamports']+b['reserve_lamports'],all_['reserve_lamports'])
        self.assertEqual(a['nonlargest_lamports']+b['nonlargest_lamports'],all_['nonlargest_lamports'])
        weighted=(a['nonlargest_lamports']+b['nonlargest_lamports'])/(a['reserve_lamports']+b['reserve_lamports'])
        self.assertEqual(weighted,all_['weighted_mean'])

    def test_tail_exponent_is_invariant_to_reserve_units(self):
        values=[g['max_lamports'] for g in self.groups if not g['any_completed']]
        a=V.fit_tail(values)['fit']
        b=V.fit_tail([x*10**6 for x in values])['fit']
        self.assertEqual(a['n_tail'],b['n_tail'])
        self.assertAlmostEqual(a['alpha_survival'],b['alpha_survival'],places=9)
        self.assertAlmostEqual(a['ks_distance'],b['ks_distance'],places=9)
        self.assertAlmostEqual(a['xmin_sol']*10**6,b['xmin_sol'],places=7)

    def test_completed_collectors_resume_without_network_or_rewriting_timestamps(self):
        paths=[C.DATA,C.RUN,C.SOURCES,B.OUTPUT,B.RUN,B.SCHEMA]
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        with mock.patch.object(sys,'argv',['collector','--collect']),contextlib.redirect_stdout(io.StringIO()):
            with mock.patch.object(C,'request',side_effect=AssertionError('unexpected network')):
                C.main()
            with (mock.patch.object(B,'request',side_effect=AssertionError('unexpected network')),
                  mock.patch.object(B,'rpc',side_effect=AssertionError('unexpected RPC'))):
                B.main()
        self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in before.items()))


if __name__=='__main__':unittest.main()
