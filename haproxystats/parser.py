import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class HaproxyStats(object):
    """
    params:
     - servers(list) - List of haproxy instances defined as i
       hostname:port or ip:port
     - user(str) -  User to authenticate with via basic auth(optional)
     - user_pass(str) -  Password to authenticate with via basic auth(optional)
    """
    def __init__(self,servers,user=None,user_pass=None):
        self._auth = (user,user_pass)
        self.all_stats = { s.split(':')[0] : self._fetch_stats(s) \
                           for s in servers }

    def _fetch_stats(self,base_url):
        """
        Fetch and parse stats from a single haproxy instance
        """
    
        listeners = []
        local_stats = { 'frontends': {}, 'backends':  {} }
        haproxy_url = 'http://' +  base_url + '/;csv;norefresh'
    
        if None in self._auth:
            r = requests.get(haproxy_url)
        else:
            r = requests.get(haproxy_url, auth=self._auth)
    
        csv = r.text.strip(' #').split('\n')
        #read fields header to create keys
        fields = [ self._utf(f) for f in csv.pop(0).split(',') if f ]
        #zip field names and values
        stats = [ dict(zip(fields, self._read_stat(l))) for l in csv if l ]
    
        #populate frontends and backends first
        for stat in stats:
            name = stat['pxname']
    
            if stat['svname'] == 'FRONTEND':
                local_stats['frontends'][name] = stat
    
            elif stat['svname'] == 'BACKEND':
                stat['listeners'] = {}
                local_stats['backends'][name] = stat
    
            else:
                listeners.append(stat)
    
        #now add servers/listeners to corresponding backends
        for stat in listeners:
            name = stat['svname'] #use unique svname here
            iid = stat['iid']
            for bkname,bkend in local_stats['backends'].iteritems():
                if bkend['iid'] == iid:
                    bkend['listeners'][name] = stat
    
        return local_stats

    def _utf(self,u):
        return u.encode('utf8')

    def _read_stat(self,stat):
        """
        Read stat str, convert unicode to utf and string to int where needed
        and return as list
        """
        ret = []
        for s in stat.split(','):
            if s.isdigit():
                s = int(s)
            if isinstance(s,unicode):
                s = self._utf(s)
            ret.append(s)
    
        return ret