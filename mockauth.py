#!/usr/bin/env python
import ConfigParser, hashlib, os, time
import base64
import sqlite3

decode = base64.decodestring
encode = base64.encodestring

class Auth(object):
    def __init__(self, cfgfile):
        config = ConfigParser.ConfigParser()
        config.read(cfgfile)
        try:
            dbfile = config.get('Auth', 'file')
        except ConfigParser.Error, e:
            print >> sys.stderr, 'Configuration Error: %s' % e
            sys.exit(125)

        self.db = sqlite3.connect(dbfile)
        create_table = '''CREATE TABLE IF NOT EXISTS auth (
            session INTEGER PRIMARY KEY ASC AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            pass TEXT NOT NULL)'''
        results = self.db.execute(create_table)
        self.db.commit()

    def authenticate(self, name, prop):
        '''Check proposed salted SHA1 for password 'prop' for entry 'name'
        '''
        res = self.db.execute('SELECT pass FROM auth WHERE name=?',
                              (name,))
        row = res.fetchone()
        if row is not None and len(row):
            pw = row[0]
        else:
            return False
        pw=decode(pw[6:])         # Base64 decode after stripping off {SSHA}
        digest = pw[:20]          # Split digest/hash of PW from salt
        salt = pw[20:]            # Extract salt
        chk = hashlib.sha1(prop)  # Hash the string presented
        chk.update(salt)          # Salt to taste:

        result = name if chk.digest() == digest else ''
        return result

    def add_account(self, name, pw):
        session = int(time.time()*100)
        salt = base64.b64encode(os.urandom(32))
        phash = base64.b64encode(hashlib.sha1(pw).digest())
        passwd = '{SSHA}%s%s' % (phash, salt)
        self.db.execute('INSERT OR REPLACE INTO auth (session, name, pass)'
                        + ' VALUES (?,?,?)', (session, name, passwd))
        self.db.commit()
        return passwd

if __name__ == '__main__':
    import sys, getpass

    if len(sys.argv) < 2:
        print >> sys.stderr, 'Must supply new username'
        sys.exit(126)

    if 'BOTTLECFG' not in os.environ:
        print >> sys.stderr, 'Warning: no configuration specified in environ'
        ini = './settings.ini'
    else:
        ini = os.environ['BOTTLECFG']

    auth = Auth(ini)
    name = sys.argv[1]
    p = getpass.getpass('Pass: ')
    pw = auth.add_account(name, p)
    assert auth.authenticate(name, p)

