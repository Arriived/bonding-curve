"""Checks for the executable fee/layout models, not deployed-program tests."""
import unittest

import account_sizes as A
import fee_model as F
import instruction_accounts as I


class FounderFeeTests(unittest.TestCase):
    def test_zero_default_preserves_legacy_rounding(self):
        self.assertEqual(F.FOUNDER_SHARE_BPS, 0)
        for fee in (*range(1024), 2**32-1, 2**64-1):
            door,founder,protocol=F.split_fee(fee)
            self.assertEqual((door,founder,protocol),(fee*3//5,0,fee-fee*3//5))

    def test_nonzero_share_conserves_fee_including_dust(self):
        self.assertEqual(F.split_fee(19,6000,3000),(11,5,3))
        for fee in (0,1,7,99,2**64-1):
            for door_bps,founder_bps in ((6000,1000),(6000,4000),(0,10000),(0,0)):
                parts=F.split_fee(fee,door_bps,founder_bps)
                self.assertEqual(sum(parts),fee)
                self.assertTrue(all(0<=part<=2**64-1 for part in parts))

    def test_invalid_allocations_cannot_create_negative_protocol_share(self):
        for door,founder in ((6000,4001),(-1,0),(0,-1),(10001,0),(0,10001)):
            with self.assertRaises(ValueError):F.split_fee(100,door,founder)
        for fee in (-1,2**64,1.5,True):
            with self.assertRaises(ValueError):F.split_fee(fee)

    def test_new_fields_preserve_existing_packed_prefix(self):
        config=A.LAYOUTS['Config'];room=A.LAYOUTS['Room']
        self.assertEqual(sum(size for _,size in config[:-1]),246)
        self.assertEqual(sum(size for _,size in room[:-4]),1265)
        self.assertEqual([size for _,size in room[-4:]],[32,8,8,2])
        self.assertTrue(config[-1][0].startswith('founder_share_bps: u16'))
        self.assertTrue(room[-1][0].startswith('founder_share_bps: u16'))
        self.assertEqual(A.rent(sum(size for _,size in room))-A.rent(1265),50*A.LAMPORTS_PER_BYTE)

    def test_claim_accounts_and_trade_account_sets(self):
        self.assertEqual(len(I.CLAIM_FOUNDER_FEES),7)
        self.assertTrue({'founder','room','fee_vault','fee_wsol','founder_wsol_ata','wsol_mint','spl_token_program'}==set(I.CLAIM_FOUNDER_FEES))
        for accounts in (I.CURVE_DOOR,I.CURVE_ROOM,I.POOL_EXTRA):
            self.assertNotIn('founder',accounts)


if __name__=='__main__':unittest.main()
