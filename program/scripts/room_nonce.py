"""Matcher/client room nonce. Sign its exact LE bytes in create_room's payload.

Print decimal as a string, not a JavaScript Number (which loses u64 precision).
On an occupied PDA request a new nonce AND fresh matcher/launcher signatures.
Never derive this value from a slug or maintain a sequential global allocator.
"""
import secrets
if __name__=='__main__':
    print(secrets.randbits(64))
