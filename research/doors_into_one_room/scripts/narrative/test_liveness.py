"""Boundary and adversarial checks for the routing/release gate. Run with Python directly."""
import copy
import unittest

import matcher as M

NOW = 100 * 86_400
P = M.DEFAULTS


def room(status=0):
    return {"status": status, "created_at": NOW - 3 * 86_400, "reserve": 500_000_000,
            "last_trade_at": NOW, "volume_gross": 5_000_000_000,
            "liveness_buckets": [{"start": NOW, "amount": 5_000_000_000}],
            "pool": {"token_b_amount": 0, "ckpt_ts": NOW, "ckpt_fee": 0,
                     "total_lp_b_fee": 0}}


class LivenessTests(unittest.TestCase):
    def live(self, r, now=NOW):
        return M.is_live(r, now, P)[0]

    def test_new_grace_is_strict_and_ignores_funding(self):
        r = room(); r.update(reserve=0, liveness_buckets=[], created_at=NOW - P['live_new_seconds'] + 1)
        self.assertTrue(self.live(r))
        r['created_at'] -= 1
        self.assertFalse(self.live(r))

    def test_one_hour_grace_replaces_two_hours(self):
        r = room(); r.update(reserve=0, liveness_buckets=[], created_at=NOW - 45 * 60)
        self.assertTrue(self.live(r))
        r['created_at'] = NOW - 75 * 60
        self.assertFalse(self.live(r))
        r.update(reserve=500_000_000, liveness_buckets=[{'start': NOW, 'amount': 5_000_000_000}])
        self.assertTrue(self.live(r))

    def test_mature_reserve_idle_volume_boundaries(self):
        for status in (0, 1):
            r = room(status)
            self.assertTrue(self.live(r))
            for key, value in [('reserve', 499_999_999),
                               ('last_trade_at', NOW - P['live_max_idle_seconds'] - 1),
                               ('liveness_buckets', [{'start': NOW, 'amount': 4_999_999_999}])]:
                bad = copy.deepcopy(r); bad[key] = value
                self.assertFalse(self.live(bad), key)
            r['last_trade_at'] = NOW - P['live_max_idle_seconds']
            self.assertTrue(self.live(r))

    def test_penny_refresh_cannot_revive_old_reserve(self):
        r = room(); r['liveness_buckets'] = []
        M.record_curve_trade(r, NOW, 10_000_000, P)
        self.assertFalse(self.live(r))

    def test_counter_is_trailing_and_conservative_at_partial_hour(self):
        r = room(); r['liveness_buckets'] = [{'start': NOW - 86_400, 'amount': 5_000_000_000}]
        self.assertTrue(self.live(r))
        self.assertFalse(self.live(r, NOW + 1))

    def test_ring_wrap_keeps_current_volume_and_bounds_storage(self):
        r = room(); r['liveness_buckets'] = []
        for hour in range(100):
            M.record_curve_trade(r, NOW + hour * 3600, 1_000_000_000, P)
        self.assertLessEqual(len(r['liveness_buckets']), 25)
        self.assertEqual(M.trailing_amount(r['liveness_buckets'], NOW + 99 * 3600 + 1, P),
                         24_000_000_000)

    def test_direct_pool_fees_survive_checkpoint_without_double_counting(self):
        r = room(2); r['liveness_buckets'] = []
        r['pool'].update(ckpt_ts=NOW - 3600, total_lp_b_fee=80_000_000)
        self.assertTrue(self.live(r))
        M.checkpoint_pool(r, NOW, P)
        self.assertTrue(self.live(r))
        self.assertEqual(M.trailing_amount(r['liveness_buckets'], NOW, P), 80_000_000)
        M.checkpoint_pool(r, NOW, P)
        self.assertEqual(M.trailing_amount(r['liveness_buckets'], NOW, P), 80_000_000)

    def test_stale_cumulative_pool_fees_cannot_be_relabelled_recent(self):
        r = room(2); r['liveness_buckets'] = []
        r['pool'].update(ckpt_ts=NOW - 3 * 86_400, total_lp_b_fee=1_000_000_000)
        self.assertFalse(self.live(r))
        M.checkpoint_pool(r, NOW, P)
        self.assertFalse(self.live(r))
        r['pool']['total_lp_b_fee'] += 80_000_000
        self.assertTrue(self.live(r))

    def test_release_is_exact_complement_for_all_statuses(self):
        for status in (0, 1, 2):
            for young in (True, False):
                r = room(status)
                if young:
                    r['created_at'] = NOW
                self.assertEqual(M.slug_releasable(r, NOW, P), not self.live(r))

    def test_invalid_creation_and_pool_counter_fail_closed(self):
        r = room(); del r['created_at']
        self.assertFalse(self.live(r))
        r['created_at'] = NOW + 1
        self.assertFalse(self.live(r))
        r = room(2); r['pool']['ckpt_fee'] = 1
        self.assertFalse(self.live(r))

    def test_shadow_image_hash_does_not_change_route_ties(self):
        rooms=[]
        for rid, reserve, phash in [(1,500_000_000,'0000000000000000'),
                                     (2,1_000_000_000,'ffffffffffffffff')]:
            r=room();r.update(room_id=rid,reserve=reserve,faces=[{'name':'Testcoin','symbol':'TEST','phash':phash}])
            rooms.append(r)
        out=M.decide({'now':NOW,'candidate':{'name':'Testcoin','symbol':'TEST','phash':'0000000000000000'},
                      'rooms':rooms,'params':{'image_routing':'shadow'}})
        self.assertEqual(out['room_id'],2)


if __name__ == '__main__':
    unittest.main()
