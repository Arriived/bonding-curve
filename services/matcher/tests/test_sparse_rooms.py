"""Sparse room layouts preserve exact hourly liveness volumes."""
import struct

import pytest

from matcher_service import layouts


def test_birth_room_decodes_without_allocated_volume_slots():
    data=bytearray(735)
    data[:8]=layouts.DISC['Room']
    assert layouts.decode_room(bytes(data))['buckets']==[]


def test_sparse_room_decodes_large_exact_volumes_and_ignores_capacity_padding():
    data=bytearray(1335)
    data[:8]=layouts.DISC['Room']
    struct.pack_into('<I',data,665,2)
    for i,(start,amount) in enumerate([(1_800_000_000,2**80+123),(1_800_003_600,999)]):
        struct.pack_into('<qQQ',data,669+24*i,start,amount&((1<<64)-1),amount>>64)
    assert layouts.decode_room(bytes(data))['buckets']==[(1_800_000_000,2**80+123),(1_800_003_600,999)]
    struct.pack_into('<I',data,665,26)
    with pytest.raises(layouts.LayoutError):layouts.decode_room(bytes(data))
