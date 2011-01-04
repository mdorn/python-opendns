"""
The MIT License

Copyright (c) 2011 Matt Dorn

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import urllib, urllib2, cookielib
import os, re, csv
from StringIO import StringIO

try:
    import simplejson as json
except ImportError: 
    import json

import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('opendns')
log.addHandler(NullHandler())

try:
    from lxml import etree
    has_lxml = True
except ImportError:
    log.warn("lxml not found -- some features will not be available")
    has_lxml = False

DASHBOARD_URL = "https://www.opendns.com/dashboard"
DOMAIN_TAG_URL = "http://www.opendns.com/community/domaintagging"

class OpenDNSException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return 'OpenDNS Error: %s' % (self.message)

class Client(object):
    '''
    Client for the non-existent OpenDNS Web Services API
    '''
    network_id = None
    opener = None
    
    def __init__(self, username, password, network_id, user_agent=None,
        skip_login=False):
        '''
        Login to OpenDNS, set network id and URL opener for 
        subsequent requests
        '''
        self.network_id = network_id
        
        if skip_login:
            self.opener = None
        else:
            cj = cookielib.CookieJar()
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        
            # get form token
            resp = self.opener.open(DASHBOARD_URL)
            html = resp.read()
            m = re.search('.*name="formtoken" value="([0-9a-f]*)".*', html)
            formtoken = m.group(1)
        
            # login
            post_vals = {
                'formtoken' : formtoken,
                'username' : username,
                'password' : password,
                'sign_in_submit': 'foo'
            }
            if user_agent:
                headers = {'User-Agent' : user_agent}
            else:
                headers = {}
            text = self._get_response(
                DASHBOARD_URL + '/signin', post_vals, headers)
            
            if has_lxml:
                parser = etree.HTMLParser()        
                tree = etree.parse(StringIO(text), parser)
                failed_login = tree.xpath('//*[@id="ac_error_login"]')
            else:
                find_error = text.find('ac_error_login')
                if find_error >= 0:
                    failed_login = True
                else:
                    failed_login = False
            if failed_login:
                raise OpenDNSException('Login failed')

    def get_stats(self, which, begin_date, end_date=None):
        '''
        Retrieve stats via CSV and return a dictionary.
        
        Can use either a single date or a date range (if ``end_date`` is 
        included). Dates must be of type ``datetime.date``.
        
        ``which`` can be one of the following: totalrequests, unique domains, 
        uniqueips, requesttypes, topdomains, or any subrequest of topdomains: 
        blocked, blacklist, category, phish, malware, smartcache.
        '''
        # TODO: currently only supports the first 200 records of any request 
        # (i.e. "page1")

        # format date
        if not end_date:
            date = begin_date.strftime('%Y-%m-%d')
        else:
            begin_date = begin_date.strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')
            date = "%sto%s" % (begin_date, end_date)
        
        # get data
        if which in ['blocked', 'blacklist', 'category', 'phish', 'malware', 
                    'smartcache']:
            url = DASHBOARD_URL + "/stats/%d/topdomains/%s/%s.csv" % \
                (self.network_id, date, which)
        else:
            url = DASHBOARD_URL + "/stats/%d/%s/%s.csv" % \
                (self.network_id, which, date)
        result = self._get_response(url)
        csv_reader = csv.DictReader(result.split(os.linesep))
        recs = []
        for i in csv_reader:
            recs.append(i)
        return recs

    def get_domain_categories(self, domain):
        '''
        Returns a dictionary of categories and category info for a given domain
        '''
        url = DASHBOARD_URL + "/stats/%s/topdomains_categories/%s" % \
            (self.network_id, domain)
        resp_dict = self._get_response(url, returns_json=True)
        if not resp_dict['rsp']['disabled'] and \
            not resp_dict['rsp']['partial'] and \
            not resp_dict['rsp']['enabled']:
            raise OpenDNSException('The requested domain appears not to ' \
                'have been categorized by OpenDNS yet.')
        else:
            return resp_dict

    def get_blacklist_domains(self):
        '''
        Returns a dictionary of individually blacklisted domains and their IDs
        '''
        url = DASHBOARD_URL + "/settings/%s/content_filtering" % \
            (self.network_id)
        text = self._get_response(url)
        parser = etree.HTMLParser()        
        tree = etree.parse(StringIO(text), parser)
        table = tree.xpath("//table[@id='always-block-table']")[0]
        domains = [(int(i.get('for')), i.text) 
            for i in table.iterdescendants() if i.tag=='label']
        return dict(domains)
        
    def add_blacklist_domain(self, domain, force=False):
        '''
        Add a domain to blacklist. Returns domain ID on success. An optional
        ``force`` argument adds the domain even if it's being blocked by
        a category
        '''
        url = DASHBOARD_URL + '/dashboard_ajax.php'
        post_vals = {
            'action' : 'add_blocked_domain',
            'n' : self.network_id,
            'blocked_domain': domain,
            'step1': 'true'
        }
        msg_dict = self._get_response(url, post_vals, returns_json=True)
        if msg_dict.has_key('errors'):
            if msg_dict['errors']:
                raise OpenDNSException(msg_dict['message'])

        if msg_dict.has_key('success'):
            if msg_dict['success']:
                return int(msg_dict['domain_id'])
            else:
                return False
        elif msg_dict.has_key('enabled_count'):
            if force:
                log.warn('Domain already being blocked by category. ' \
                    'Adding anyway.')
                post_vals['step2'] = post_vals.pop('step1')
                msg_dict = self._get_response(url, post_vals, returns_json=True)
                if msg_dict.has_key('success'):
                    if msg_dict['success']:
                        return int(msg_dict['domain_id'])
                    else:
                        return False
            else:
                log.warn('Domain already being blocked by category. ' \
                    'Skipping. Use force parameter if desired')
        return False
            
    def remove_blacklist_domains(self, domain_ids):
        '''
        Delete list of domain IDs (integers) from blacklist. Returns True 
        on success
        '''
        url = DASHBOARD_URL + '/dashboard_ajax.php'
        post_vals = {
            'action' : 'delete_blocked_domains',
            'n' : self.network_id,
        }        
        for i in domain_ids:
            post_vals['bdomain_id[%s]' % str(i)] = str(i)
        msg_dict = self._get_response(url, post_vals, returns_json=True)
        # NOTE: as of this writing, opendns always returns success regardless 
        # of what you feed it here
        if msg_dict['success']:
            return True
        else:
            return False

    def get_categories(self):
        '''
        Returns a dictionary of category IDs and category names
        '''
        url = DOMAIN_TAG_URL + '/submit/'
        text = self._get_response(url)
        parser = etree.HTMLParser()        
        tree = etree.parse(StringIO(text), parser)
        select = tree.xpath('//*[@id="cat_select"]')[0]
        categories = [(int(i.get('value')), i.text.strip())
            for i in select.iterchildren() if i.get('value') != '0']
        return dict(categories)    
        
    def submit_domain(self, domain, category_id):
        '''
        Submit a domain with recommended cateogory's ID (see 
        ``get_categories``)
        '''
        url = DOMAIN_TAG_URL + '/contribute_ajax.php'
        post_vals = {
            'category_id': str(category_id),
            'domain': domain
        }
        retval = self._get_response(url, post_vals, returns_json=True)
        if retval.has_key('err'):
            # NOTE: submitting a category for a domain when the category has 
            # already been suggested results in a "yes" vote, hence there's 
            # no separate "vote" method in this library.
            log.warn('Category ID %d has already been submitted for %s. ' \
            'This may have resulted in a "yes" vote.' % (category_id, domain))
        if retval.has_key('d'):
            return True
        else:
            raise OpenDNSException(
                'An unknown error occurred submitting a domain.'
            )

    def get_whitelist_domains(self):
        # TODO
        pass
        
    def add_whitelist_domain(self, domain, force=False):
        # TODO
        pass

    def remove_whitelist_domains(self, domain_ids):
        # TODO
        pass

    def get_blocked_custom_categories(self):
        # TODO
        pass
    
    def block_custom_category(self, category):
        # TODO
        pass
        
    def unblock_custom_category(self, category):
        # TODO
        pass
        
    def _get_response(self, url, post_vals=None, headers={}, 
        returns_json=False):
        optional_params = {}
        if post_vals:
            data = urllib.urlencode(post_vals)
        else:
            data = None
        req = urllib2.Request(url, data, headers)
        resp = self.opener.open(req)
        text = resp.read()
        if returns_json:
            msg_dict = json.loads(text)
            return msg_dict
        else:
            return text
