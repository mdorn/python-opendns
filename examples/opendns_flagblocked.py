from optparse import OptionParser
import datetime
import time
import cPickle as pickle
import logging
import sys
import smtplib

from opendns import Client

SMTP_SERVER = ''
SMTP_PORT = 587
SMTP_USER = SMTP_FROM = ''
SMTP_TO = ''
SMTP_PASSWORD = ''
LOG_FILENAME = '/tmp/opendns_flagblocked.log'
USER_AGENT = None

logging.basicConfig(filename=LOG_FILENAME, 
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s")
log=logging.getLogger('opendns_flagblocked')

def main(username, password, network_id, category_ids):
    client = Client(username, password, network_id, user_agent=USER_AGENT)
    stats = client.get_stats('blocked', datetime.date.today())
    domains = [i['Domain'] for i in stats]
    
    # write domains to a pickle for persistence
    filename = "/tmp/domains%s.pickle" % \
        datetime.date.today().strftime('%Y%m%d')    
    try:
        pickled_domains = pickle.load(open(filename))
        if domains == pickled_domains:
            # no new domains have been added to the report
            sys.exit()
        else:
            # new domain names added -- let's see if any of them
            # are in flagged categories
            log.info('New domains found.')
    except IOError:
        # either first time use, or a day has passed
        log.info('New domains found.')        
        pickle.dump(domains, open(filename, "w" ))
        pickled_domains = []
    
    bad_domains = []
    
    for i in domains:
        # check if it's a flagged category domain
        if i not in pickled_domains: # make sure you don't do any unnecessary 
                                     # network calls
            cat_info = client.get_domain_categories(i)
            cat_info = cat_info['rsp']['enabled']        
            if type(cat_info) == dict: # non-dict items are blacklisted 
                                       # specifically, not by category
                keys = [int(j) for j in cat_info.keys()]
                for cat_id in category_ids:
                    if cat_id in keys:
                        bad_domains.append(i)
                        log.info('New domain in flagged category %d found: %s' \
                            % (cat_id, i))
            time.sleep(2) # don't abuse "API"

    if bad_domains:
        msg = "User in OpenDNS network %d attempted to access the following " \
            "flagged domains: %s" % \
            (network_id, ', '.join(set(bad_domains)))
        try:
            send_mail('[OpenDNS Blocked Request Notification]', msg)
            log.info('Email sent to %s.' % SMTP_TO)
        except:
            log.warn('Could not send email.')
            pass
    
    pickle.dump(domains, open(filename, "w" ))

def send_mail(subject, body):
    conn = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)    
    conn.ehlo()
    conn.starttls()
    conn.ehlo()
    conn.login(SMTP_USER, SMTP_PASSWORD)
    msg = 'To: %s\nFrom: %s\nSubject: %s\n\n%s' % \
        (SMTP_TO, SMTP_FROM, subject, body)
    conn.sendmail(SMTP_FROM, [SMTP_TO], msg)
    conn.quit()
    
    
if __name__=='__main__':
    usage = "usage: %prog username password network_id cat_id cat_id ..."
    parser = OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    if not args:
        print '%s -h for help' % __file__ 
        sys.exit()
    username = args[0]
    password = args[1]
    network_id = int(args[2])
    category_ids = [int(i) for i in args[-(len(args)-3):]]
    main(username, password, network_id, category_ids)

