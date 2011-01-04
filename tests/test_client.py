import os
import unittest
import datetime
try:
    import simplejson as json
except ImportError: 
    import json

from mock import Mock

import opendns

import mocked_responses

class TestOpenDNSClient(unittest.TestCase):
    
    def setUp(self):
        mock = Mock()
        self.client = opendns.Client('username', 'password', 123456, 
            skip_login=True)
        # TODO: currently no good way to test login using mock without
        # moving network calls out of constructor
        
        self.client._get_response = Mock()
        # override _get_response to not make any network calls but to use
        # the mocked data instead
        self.client._get_response.side_effect = self._custom_return_vals

    def test_read_functions(self):
        # test stats
        retval = self.client.get_stats('blocked', datetime.date.today())
        self.assertTrue(retval[0].has_key('Domain'))
        self.assertTrue(retval[0]['Domain'] == 'evilsite.com')

        # test get category info about domain
        retval = self.client.get_domain_categories('youtube.com')
        self.assertTrue(retval['rsp']['enabled']['26']['name'] == \
            'Video sharing')
        
        # test retrieval of category list
        retval = self.client.get_categories()
        self.assertTrue('Pornography' in retval.values())
        
        # test list of blacklisted domains
        retval = self.client.get_blacklist_domains()
        self.assertTrue('uncategorized-evilsite.com' in retval.values())

    def test_submit_functions(self):

        # test blacklisting a domain
        retval = self.client.add_blacklist_domain('evilsite.com', force=True)
        self.client._get_response.assert_called_with(
            opendns.DASHBOARD_URL + '/dashboard_ajax.php', 
            {'action': 'add_blocked_domain', 
                'blocked_domain': 'evilsite.com', 
                'step1': 'true', 
                'n': 123456}, 
            returns_json=True)
        self.assertEqual(retval, 1234)
        
        # test removing domains from blacklist
        retval = self.client.remove_blacklist_domains([1234, 5678])
        self.assertEqual(retval, True)
        self.client._get_response.assert_called_with(
            opendns.DASHBOARD_URL + '/dashboard_ajax.php', 
            {'action': 'delete_blocked_domains', 
                'bdomain_id[5678]': '5678', 
                'bdomain_id[1234]': '1234', 
                'n': 123456}, 
            returns_json=True)
            
        # test submit a domain w/ suggested category
        retval = self.client.submit_domain('evilsite.com', 64)
        self.assertEqual(retval, True)
        self.client._get_response.assert_called_with(
            opendns.DOMAIN_TAG_URL + '/contribute_ajax.php', 
            {'domain': 'evilsite.com', 'category_id': '64'}, 
            returns_json=True)
        
    def _custom_return_vals(self, *args, **kwargs):
        '''
        Get and return mocked data for use with mocked _get_response method
        '''
        val = None
        # TODO: there's GOT to be a more elegant way of determining which
        # method is being invoked
        if args[0] == opendns.DOMAIN_TAG_URL + '/submit/':
            f = '%s/mocked_html/%s' % \
                (os.path.dirname(__file__), 'domaintagging_submit.html')
            html = open(f, 'r')
            val = html.read()
        elif 'blocked.csv' in args[0]:
            val = mocked_responses.STATS
        elif 'youtube.com' in args[0]:
            val = mocked_responses.CATEGORY_INFO_YOUTUBE
        elif args[0] == opendns.DASHBOARD_URL + \
            '/settings/123456/content_filtering':
            f = '%s/mocked_html/%s' % \
                (os.path.dirname(__file__), 'dashboard_content_filtering.html')
            html = open(f, 'r')
            val = html.read()
        elif args[0] == opendns.DASHBOARD_URL + '/dashboard_ajax.php':
            if args[1]['action'] == 'add_blocked_domain':
                val = mocked_responses.BLACKLIST_DOMAIN
            elif args[1]['action'] == 'delete_blocked_domains':
                val = mocked_responses.REMOVE_BLACKLIST_DOMAIN
        elif args[0] == opendns.DOMAIN_TAG_URL + '/contribute_ajax.php':
            val = mocked_responses.SUBMIT_DOMAIN
            
        if kwargs.has_key('returns_json'):
            if kwargs['returns_json']:
                val = json.loads(val)

        return val
        
if __name__ == '__main__':
    unittest.main()

    
