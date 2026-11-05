"""Regenerate build-spec account tables and packet counts from the executable schemas."""
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

import account_sizes as A
import instruction_accounts as I
import fee_model as F

ROOT = Path(__file__).resolve().parent.parent


def replace(document, name, content):
    start=f'<!-- BEGIN GENERATED {name} -->';end=f'<!-- END GENERATED {name} -->'
    before,tail=document.split(start,1);_,after=tail.split(end,1)
    return before+start+'\n'+content.strip()+'\n'+end+after


def capture(main):
    output=io.StringIO()
    with contextlib.redirect_stdout(output):
        main()
    return output.getvalue()


def main():
    sizes={name:sum(n for _,n in fields) for name,fields in A.LAYOUTS.items()}
    account_output=capture(A.main)
    instructions=capture(I.main)
    (ROOT/'outputs/account_sizes.md').write_text(account_output,encoding='utf-8',newline='\n')
    (ROOT/'outputs/instruction_accounts.md').write_text(instructions,encoding='utf-8',newline='\n')
    curve=subprocess.run([sys.executable,str(ROOT/'scripts/curve_identities.py'),'--json',
                          str(ROOT/'outputs/curve_quantities.json')],check=True,capture_output=True,encoding='utf-8').stdout
    fees=capture(F.main)
    (ROOT/'outputs/curve_identities.md').write_text(curve,encoding='utf-8',newline='\n')
    (ROOT/'outputs/fee_model.md').write_text(fees,encoding='utf-8',newline='\n')
    subprocess.run([sys.executable,str(ROOT/'scripts/graduation_scenarios.py')],check=True,capture_output=True)
    quantities=json.loads((ROOT/'outputs/curve_quantities.json').read_text(encoding='utf-8'))
    room_mint=A.meme_mint(32,10,200,A.ROOM_MINT_META)
    door_mint=A.meme_mint(32,10,200,A.DOOR_MINT_META_MAX)
    accounts=[('Config','["config"]',sizes['Config']),('Room','["room", room_id u64 LE]',sizes['Room']),
              ('ReserveVault','["reserve", room]',0),('FeeVault','["fees", room]',0),
              ('GradPayer (System-owned)','["grad_payer", room]',0),
              ('SlugLock','["slug", derived_identity_hash]',sizes['SlugLock']),
              ('NameLock (when the launch has a name key)','["name", name_key]',sizes['NameLock']),
              ('RoomMint','["room_mint", room]',room_mint),('RoomVault','["room_vault", room]',165),
              ('RetiredVault','["retired", room]',165),('FeeWsol','["fee_wsol", room]',165)]
    doors=[('Door (door 0: nonce 0)','["door", room, door_nonce u64 LE]',sizes['Door']),
           ('DoorMint (max metadata)','["door_mint", room, door_nonce]',door_mint),
           ('DoorVault','["door_vault", door]',165),('DoorRoomVault','["door_room_vault", door]',165),
           ("trader's Token-2022 ATA",'ATA program',170)]
    def table(rows):
        return '\n'.join(['| account | seeds / derivation | data bytes | rent (lamports) |',
                          '|---|---|---|---|']+
                         [f'| {name} | `{seeds}` | {n} | {A.rent(n):,} |' for name,seeds,n in rows])
    totals=[('per room, excluding door accounts',A.per_room_rent_lamports()),
            ('per door, max metadata',A.per_door_rent_lamports()),
            ('per door, minimum metadata',A.rent(sizes['Door'])+A.rent(A.meme_mint(1,1,0,A.DOOR_MINT_META_MIN))+2*A.rent(165)),
            ('launch room + door 0, max metadata',A.per_room_rent_lamports()+A.per_door_rent_lamports()),
            ('graduation rent, paid from reserve',A.graduation_rent_lamports())]
    total_table='\n'.join(['| item | lamports | SOL | USD at assumed $150/SOL |','|---|---|---|---|']+
                           [f'| {name} | {v:,} | {v/A.SOL:.6f} | ${v/A.SOL*A.USD_PER_SOL:.2f} |' for name,v in totals])
    path=ROOT/'PERMANENT_CURVE_SPEC.md';document=path.read_text(encoding='utf-8')
    for name,content in [('ROOM ACCOUNTS',table(accounts)),('DOOR ACCOUNTS',table(doors)),
                         ('RENT TOTALS',total_table),('INSTRUCTION ACCOUNTS',instructions),
                         ('CURVE FIGURES',curve),('FEE FIGURES',fees),
                         ('GRADUATION SNAPSHOTS',(ROOT/'outputs/graduation_scenarios.md').read_text(encoding='utf-8')),
                         ('RENT FORMULA',f'Rent model verified in `outputs/narrative/rent_confirmation.json`: '
                          f'`(128 + data_bytes) × {A.LAMPORTS_PER_BYTE:,}` lamports. '
                          'Runtime instructions use the rent sysvar; this coefficient is a recorded calibration.'),
                         ('DEFAULT TRIGGER',f"Current **Config default**: `{quantities['trigger']:,}` lamports, "
                          f"pool seed `{quantities['r_star']:,}` plus graduation rent `{quantities['graduation_rent']:,}`. "
                          'Existing rooms retain their copied trigger and calculate the seed from their own sold state.')]:
        document=replace(document,name,content)
    path.write_text(document,encoding='utf-8',newline='\n')
    print('Regenerated account sizes, rent, curve, fees, snapshot scenarios, instruction lists and packet margins.')


if __name__=='__main__':
    main()
