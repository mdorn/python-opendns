STATS = '''Rank,Domain,Total,Blacklisted,Blocked by Category,Blocked by an Adult Category,Blocked as Phishing,Blocked as Malware,Resolved by SmartCache
1,evilsite.com,47,47,0,0,0,0,0,0
2,badsite.com,18,18,0,0,0,0,0,0
3,naughtysite.com,12,0,12,0,0,0,0,0
'''

CATEGORY_INFO_YOUTUBE = '''
{"stat":"ok","rsp":{"enabled":{"26":{"name":"Video sharing","description":"Sites for sharing video content.","ctrl_name":"dt_category[26]","category_id":"26"}},"partial":[],"disabled":[]}}
'''

BLACKLIST_DOMAIN = '''
{"domain":"evilsite.com","message":"Domain added to blocklist; will take effect in 3 minutes.","domain_id":"1234","success":true}
'''

REMOVE_BLACKLIST_DOMAIN = '''
{"message":"Domain(s) successfully removed from blocklist; will take effect in 3 minutes.","success":true,"blocked":{"domain_ids":{"1234":"1234","5678":"5678"}},"type":"blocked"}
'''

SUBMIT_DOMAIN_ALREADY_CATEGORIZED = '''
{"d":"google.com","err":"Already in category"}
'''

SUBMIT_DOMAIN = '''
{"d":"evilsite.com"}
'''