"""Normalisation and evidence accounting regressions; fixtures are not sample measurements."""
import unittest

import calibrate_social as S


class SocialTests(unittest.TestCase):
    def parts(self, value, field='twitter'):
        parts, reason = S.normalize(value, field)
        self.assertIsNone(reason)
        return parts

    def test_x_alias_and_tracking(self):
        a = self.parts('https://WWW.Twitter.COM/ElonMusk/status/12345/?utm_source=a#photo')
        b = self.parts('https://x.com/i/status/12345')
        self.assertEqual(S.signals(a, 'twitter')['x_post'], S.signals(b, 'twitter')['x_post'])
        self.assertEqual(S.signals(a, 'twitter')['x_account'], 'x.com/elonmusk')

    def test_missing_placeholder_malformed_never_become_keys(self):
        for value in ('', '  ', None, False, [], 'N/A', '#', 'https://example.com',
                      'https://https://t.me/group', 'https://x.com', 'https://u:p@x.com/name',
                      'javascript:alert(1)', 'https://x.com.evil.test/a b'):
            self.assertIsNone(S.normalize(value, 'twitter')[0], repr(value))

    def test_specific_post_not_community_or_utility(self):
        for path in ('i/communities/12345', 'i/trending/12345', 'intent/tweet', 'user/status/not-a-number'):
            signals = S.signals(self.parts('https://x.com/'+path), 'twitter')
            self.assertNotIn('x_post', signals)
            self.assertNotIn('x_account', signals)

    def test_bare_handle_and_account_tier_excludes_same_post(self):
        self.assertEqual(S.signals(self.parts('@ElonMusk'), 'twitter')['x_account'], 'x.com/elonmusk')
        a = {'social': {'x_account': {'x.com/elonmusk'}, 'x_post': {'123'}}}
        b = {'social': {'x_account': {'x.com/elonmusk'}, 'x_post': {'123'}}}
        self.assertFalse(S.social_hit(a,b,'x_account',{'x.com/elonmusk'}))
        b['social']['x_post'] = {'456'}
        self.assertEqual(S.social_hit(a,b,'x_account',{'x.com/elonmusk'}), {'x.com/elonmusk'})

    def test_shortener_not_expanded_or_classified_as_post(self):
        value = self.parts('https://t.co/AbCd?tracking=yes#here')
        self.assertEqual(value['url'], 't.co/AbCd')
        self.assertEqual(S.signals(value,'twitter'), {})

    def test_telegram_case_and_invites(self):
        public = S.signals(self.parts('https://telegram.me/s/MyGroup/123', 'telegram'), 'telegram')
        self.assertEqual(public['telegram'], 't.me/mygroup')
        invite = S.signals(self.parts('https://t.me/joinchat/AbCd_123', 'telegram'), 'telegram')
        self.assertEqual(invite['telegram'], 't.me/+AbCd_123')
        self.assertNotEqual(invite['telegram'], invite['telegram'].lower())
        self.assertNotIn('telegram', S.signals(self.parts('https://t.me/share/url', 'telegram'), 'telegram'))

    def test_domain_is_host_not_path_or_public_suffix(self):
        p = self.parts('HTTPS://WWW.Shop.Example.co.uk/a/?utm=x#b','website')
        self.assertEqual(S.signals(p,'website')['website_domain'], 'shop.example.co.uk')
        self.assertNotIn('website_domain', S.signals(p,'twitter'))

    def test_missing_uri_does_not_define_same_narrative(self):
        a = {'uri':'', 'nk':'AAA', 'sk':'A'}
        b = {'uri':'', 'nk':'BBB', 'sk':'B'}
        self.assertEqual(S.judgement(a,b,{}), 'unlabelled')
        self.assertEqual(S.anchors([a,b]), (set(),set()))


if __name__ == '__main__':
    unittest.main()
