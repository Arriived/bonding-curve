"""Evidence checks prevent missing/non-trade snapshots becoming fabricated observations."""
import unittest

from matcher import DEFAULTS
from recall_bounds import mature_proxy_status


class RecallEvidenceTests(unittest.TestCase):
    def status(self, **fields):
        read = {'mint': 'member', 'sig': 'recorded-signature', 'slot': 100, 'time': 1000,
                'is_trade': True, 'real_sol_reserves': 0, **fields}
        return mature_proxy_status([{'mint': 'member', 'launch_time': 900}], [read],
                                   {'member': 'So11111111111111111111111111111111111111112'}, 1100, DEFAULTS)

    def test_non_trade_zero_is_unknown(self):
        result = self.status(is_trade=False)
        self.assertIsNone(result['without_volume'])
        self.assertIsNone(result['with_volume'])

    def test_complete_confirmed_empty_curve_rejects_proxy(self):
        result = self.status()
        self.assertIs(result['without_volume'], False)
        self.assertIs(result['with_volume'], False)

    def test_confirmed_reserve_and_idle_do_not_invent_volume(self):
        result = self.status(real_sol_reserves=500_000_000)
        self.assertIs(result['without_volume'], True)
        self.assertIsNone(result['with_volume'])


if __name__ == '__main__':
    unittest.main()
