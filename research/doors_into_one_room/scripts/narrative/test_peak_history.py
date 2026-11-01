"""Arithmetic/order regression fixtures; these are not market observations."""
import unittest

from measure_peak_consolidation import reserve_fields, trajectory


def event(mint, slot, signature, reserve, buy=True, inner=0):
    return {'mint':mint,'slot':slot,'signature':signature,'reserve_lamports':reserve,
            'is_buy':buy,'outer':0,'inner':inner,'quoted_amount':None}


class PeakHistoryTests(unittest.TestCase):
    def test_disjoint_member_peaks_are_not_added(self):
        rows=[event('a',1,'a1',100),event('a',2,'a2',0,False),
              event('b',3,'b1',100),event('b',4,'b2',0,False)]
        result=trajectory(rows,['a','b'],lambda _:self.fail('unneeded block read'))
        self.assertEqual(result['peak_pooled_lamports'],100)
        self.assertEqual(sum(result['individual_peak_lamports'].values()),200)
        self.assertEqual(result['gross_inflow_lamports'],{'a':100,'b':100})

    def test_cross_member_same_slot_uses_block_order(self):
        rows=[event('a',1,'a1',100),event('a',2,'a2',0,False),event('b',2,'b1',100)]
        seen=[]
        def order(slot):seen.append(slot);return {'a2':0,'b1':1}
        result=trajectory(rows,['a','b'],order)
        self.assertEqual(result['peak_pooled_lamports'],100)
        self.assertEqual(seen,[2])
        result=trajectory(rows,['a','b'],lambda _:{'b1':0,'a2':1})
        self.assertEqual(result['peak_pooled_lamports'],200)

    def test_member_order_and_instruction_order_preserve_gross(self):
        rows=[event('a',1,'sell',20,False),event('a',1,'buy',100),
              event('a',2,'roundtrip',80,True,1),event('a',2,'roundtrip',30,False,2)]
        result=trajectory(rows,['a'],lambda _:{'buy':0,'sell':1})
        self.assertEqual(result['gross_inflow_lamports']['a'],160)
        self.assertEqual(result['sell_outflow_lamports']['a'],130)
        self.assertEqual(result['terminal_lamports']['a'],30)

    def test_pruning_cannot_replace_a_measured_peak(self):
        rows=[event('a',1,'a1',100),event('a',2,'a2',0,False),
              event('a',3,'a3',10),event('b',3,'b1',10)]
        result=trajectory(rows,['a','b'],lambda _:self.fail('slot bound is already below measured peak'))
        self.assertEqual(result['peak_pooled_lamports'],100)
        self.assertEqual(result['ambiguous_slots_pruned'],1)

    def test_conflicting_quote_reserve_aliases_fail(self):
        with self.assertRaises(AssertionError):
            reserve_fields({'real_sol_reserves':1,'real_quote_reserves':2})
        self.assertEqual(reserve_fields({'real_sol_reserves':0,'real_quote_reserves':2}),2)


if __name__=='__main__':unittest.main()
