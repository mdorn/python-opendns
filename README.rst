Requirements
============

- `lxml`_ is required for several, but not all functions.
- The test suite requires the `mock`_ library

.. _lxml: http://codespeak.net/lxml/
.. _mock: http://www.voidspace.org.uk/python/mock/

Usage
=====

A few examples follow.

Example of getting stats for network with ID 1234567::

    >>> import datetime
    >>> from opendns import Client
    >>> client = Client('username', 'password', 1234567)
    >>> client.get_stats('blocked', datetime.date.today())
    [{
        'Domain': 'evilsite.com',
        'Blacklisted': '47',
        'Blocked by an Adult Category': '0',
        'Blocked as Phishing': '0',
        'Rank': '1',
        'Blocked as Malware': '0',
        None: ['0'],
        'Blocked by Category': '0',
        'Resolved by SmartCache': '0',
        'Total': '47'
    },
    {
        'Domain': 'badsite.com',
        'Blacklisted': '18',
        'Blocked by an Adult Category': '0',
        'Blocked as Phishing': '0',
        'Rank': '2',
        'Blocked as Malware': '0',
        None: ['0'],
        'Blocked by Category': '0',
        'Resolved by SmartCache': '0',
        'Total': '18'
    },
    {
        'Domain': 'naughtysite.com',
        'Blacklisted': '0',
        'Blocked by an Adult Category': '0',
        'Blocked as Phishing': '0',
        'Rank': '3',
        'Blocked as Malware': '0',
        None: ['0'],
        'Blocked by Category': '12',
        'Resolved by SmartCache': '0',
        'Total': '12'
    }]
    

Example of submitting a domain with recommended category::

    >>> client.submit_domain('badsite.com', 64)
    True
    
See source code and tests for more....