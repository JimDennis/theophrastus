#!/usr/bin/env python
'''Simple "message in a bottle" application
'''
from bottle import debug, post, redirect, request, response, route, run, template, static_file
import ConfigParser, sqlite3, subprocess, time
from urllib import quote as urlquote
import socket # to catch socket.error

HTML = '''<!DOCTYPE html><html><head><title>{{title}}</title></head>
<body>
%s
%%if defined('session') and session is not None:
  <form action="/logout"
  method="POST"><input type="submit" value="Logout"/>&nbsp;{{session}}</form>
%%end
</body>
</html>'''

FORM = '''<form action="/confirmation" method="POST">
Mesage posted from: {{session}}<br />
Who shall I notify:
<input type="text" name="name"><br />
Subject:
<input type="text" name="subject"><br />
What is your message:<br />
<textarea name="message" cols="80" rows="25">{{content}}</textarea><br />
<input type="submit" value="Notify">
</form>'''

HTML_FORM = HTML % FORM

CONFIRMATION = '''
<script type="text/javascript">
alert("{{name}} has sent message ID {{id}}")
window.location.replace("/")
</script>
<noscript>
<p>{{name}} has sent message ID {{id}}:
<blockquote>{{message}}
</blockquote>
<a href="/">Done</a>
</noscript>'''

HTML_CONFIRMATION = HTML % CONFIRMATION

DOCROOT = '''
%if defined('alert') and alert:
<script src="/static/notabene.js?arg={{alert}}"></script>
<noscript><p>Alert: {{alert}}</p></noscript>
%end
<p><h3>Current Notices:</h3></p>
<table>
<tr><th>Notice ID</th><th>From</th><th>Date</th><th>Subject</th></tr>
%for row in rows:
  %id=row[0]
  <tr>
  %for col in row:
    %this=str(col)[:width]
    <td><a href="/thread/{{id}}">{{this}}</a></td>
  %end
    <td>
    <form action="/close" method="POST">
    <input type="submit" value="Close" />
    <input name="entry" type="hidden" value="{{id}}" />
    </form></td>
  </tr>
%end
</table>
<p><h3>{{!prev}}<a href='/notify'>Send new notification</a>{{!next}}</h3></p>
{{!pages}}'''

HTML_ROOT = HTML % DOCROOT

VIEW_THREAD = '''
<p><h3>Thread for {{root_entry}}:</h3></p>
<p>
<table>
<tr><th>ID</th>
<th>Posted</th>
<th>Closed</th>
<th>From</th>
<th>Subject</th></tr>
%for row in rows:
  %id      = row[0]
  %posted  = row[1]
  %closed  = row[2] if row[2] is not None else ""
  %name    = row[3]
  %subj     = row[4][:width]
  %indent  = "&nbsp;" * min(row[5], 20)
<tr><td align="right">{{id}}</td><td>{{posted}}</td><td>{{closed}}</td>
    <td>{{name}}</td><td>{{!indent}}{{subj}}</td></tr>
%end
</table>
<h2>Message {{id}} Contents:</h2>
<blockquote>
{{message}}
</blockquote>
<br /></p>
'''

VIEW_THREAD = HTML % VIEW_THREAD

LOGIN_FORM = '''
<p>
<form action="/login" method="POST">
User name:
<input type="text" name="name"><br />
Password:
<input type="text" name="pass"><br />
<input type="submit" value="Login">
</form>'''

LOGIN_FORM = HTML % LOGIN_FORM

class Model(object):
    '''Maintain the DB for notifications
    '''
    schema_version = 2  # 2 add subject to schema

    def __init__(self, dbfile='./notifications.db'):
        '''Create table if necessary otherwise use existing data
        '''
        self.filename = dbfile
        self.db = sqlite3.connect(self.filename)
        prep_table = """
          CREATE TABLE IF NOT EXISTS notices
            (id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
             name TEXT NOT NULL,
             subject TEXT NOT NULL,
             message TEXT NOT NULL,
             postdate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
             closedate DATETIME DEFAULT NULL)"""
        self.db.execute(prep_table)
        self.db.commit()
        self.check_schema()

    def get_open_entry_count(self):
        '''Return count for all open entries'''
        qry = '''SELECT COUNT(id) FROM notices
                  WHERE parent_id IS NULL AND closedate IS NULL'''
        return self.db.execute(qry).fetchone()[0]

    def get_open_entries(self, count=20, offset=0):
        '''Get tails of some open threads and summary of the contents
           Defaults are suitable for the default index/root page
        '''
        offset = offset * count
        get_entries = '''
            WITH RECURSIVE tree (id, parent_id, postdate, name, subject, root_id ) AS (
                SELECT id, parent_id, postdate, name, subject, id AS root_id FROM notices
                  WHERE parent_id IS NULL AND closedate IS NULL
                UNION
                SELECT t1.id, t1.parent_id, t1.postdate, t1.name, t1.subject, root_id
                  FROM notices AS t1
                  JOIN tree on tree.id = t1.parent_id
            ) SELECT MAX(id), name, postdate, subject FROM tree GROUP BY root_id
            ORDER BY id DESC LIMIT ? OFFSET ?'''
        args = (count, offset)
        current = self.db.execute(get_entries, args)
        pagecount = int(self.get_open_entry_count() / count)
        return (current.fetchall(), pagecount)

    def create_entry(self, name, subject, message):
        '''Create a new "open" entry
        '''
        stmt = "INSERT INTO notices (name, subject, message) VALUES (?, ?, ?)"
        newrow = self.db.execute(stmt, (name, subject, message))
        self.db.commit()
        return newrow.lastrowid

    def get_thread_entries(self, entry):
        '''Get all messages IDs from one thread given any id therein
        '''
        qry_get_thread = '''
            WITH RECURSIVE tree
               (id, parent_id, postdate, closedate, name, subject,
                depth, path) AS (
              SELECT id, parent_id, postdate, closedate, name,
                subject, 1 AS depth, '' AS path FROM notices
              WHERE id = (
                WITH RECURSIVE t3 (id, parent_id) AS (
                  SELECT id, parent_id FROM notices WHERE id = ?
                  UNION ALL
                  SELECT t2.id, t2.parent_id FROM notices AS t2
                    JOIN t3 ON t3.parent_id=t2.id
                  ) SELECT id FROM t3 WHERE parent_id IS NULL
              ) UNION ALL
              SELECT t2.id, t2.parent_id, t2.postdate, t2.closedate,
               t2.name, t2.subject, depth + 1,
               path || '/' || CAST(t2.id AS VARCHAR) FROM notices AS t2
                JOIN tree ON tree.id = t2.parent_id
             ) SELECT id, postdate, closedate, name, subject, depth
               FROM tree ORDER BY path'''
        results = self.db.execute(qry_get_thread, (entry,))
        if results is not None:
            results = results.fetchall()
        else:
            results = list()
        return results

    def close_thread(self, entry):
        '''Mark a entry as "closed" (set a closing date on it)
        '''
        qry_chk = "SELECT id, name, postdate, subject, closedate FROM notices WHERE id=?"
        qry_close = "UPDATE notices SET closedate=DATETIME('NOW') WHERE id IN (%s)"
        ## SQLite doesn't parameterize IN sequences
        ## So we'll use this hack courtesy of Alex Martelli:
        ##  http://stackoverflow.com/a/1310001/149076
        row = self.db.execute(qry_chk, (entry,))
        if row:
            row = row.fetchone()
            if row[4] is not None:
                return 'Thread containing %s was already closed on %s' \
                   % (row[0], row[4])
        else:
            return 'Bad entry: Cannot close'
        entry_list = self.get_thread_entries(entry)
        if len(entry_list):
            entry_list = tuple([x[0] for x in entry_list])
            qry = qry_close % ','.join('?'*len(entry_list))
            self.db.execute(qry, entry_list)
        self.db.commit()
        return 'Thread closed: %s' % row[0]

    def get_message(self, entry):
        '''Get the message contents for a given entry
        '''
        qry = 'SELECT message FROM notices WHERE id=?'
        results = self.db.execute(qry, (entry,))
        if not results:
            ## TODO: What should I do here?
            results = '*** No such entry ***'
        else:
            results = results.fetchone()[0]
        return results

    def check_schema(self):
        '''Check schema against self
        '''
        mk_table = '''CREATE TABLE IF NOT EXISTS versions
                      (component TEXT UNIQUE NOT NULL, version INTEGER NOT NULL)'''
        self.db.execute(mk_table) # Fire and forget
        self.db.commit()
        chk_version = "SELECT version FROM versions WHERE component = 'schema'"
        ver = self.db.execute(chk_version).fetchall()
        if not ver:
            ver = 0
        else:
            ver = ver[0][0]
        if ver < Model.schema_version:
            self.migrate(ver)

    def migrate(self, ver):
        '''Upgrade DB schema
           (Must upgrade this and Model.schema_version for new schema)
           version is the version currently in the DB
        '''
        add_parent_col = 'ALTER TABLE notices ADD COLUMN parent_id INTEGER'
        add_subject_col = 'ALTER TABLE notices ADD COLUMN subject TEXT NOT NULL'
        set_new_version = '''INSERT OR REPLACE INTO versions (component, version)
                             VALUES ('schema', ?)'''
        try:
            if ver < 1:
                self.db.execute(add_parent_col)
            if ver < 2:
                self.db.execute(add_subject_col)
            self.db.execute(set_new_version, Model.schema_version)
            self.db.commit()
        except sqlite3.Error, e:
            return False, e  ## TODO: what do we do here?  Log error?
        return True


@route('/')
@route('/<page:int>')
def root(page=0):
    '''App/Doc Root page: show open incidents and link to new entry form'''
    if page is None:
        page = 0
    vals = dict()
    vals['title'] = 'Notification System'
    vals['session'] = request.get_cookie('session', None)
    vals['width'] = 72  ## TODO: consolidate this sort of thing
    vals['rows'], pagemax = model.get_open_entries(offset=page)
    vals['alert'] = request.get_cookie('alert', '')
    if pagemax > 0:
        vals['pages'] = '<p>%s of %s pages</p>' % (page+1, pagemax+1)
    else:
        vals['pages'] = ''
    if page < 1:
        vals['prev'] = '&lt;&lt;&nbsp;&nbsp;'
    else:
        prev = max(0, page - 1)
        vals['prev'] = '<a href="/%s">&lt;&lt;</a>&nbsp;&nbsp;' % (prev)
    if page > pagemax - 1:
        vals['next'] = '&nbsp;&nbsp;&gt;&gt;'
    else:
        nxt = min(pagemax, page + 1)
        vals['next'] = '&nbsp;&nbsp;<a href="/%s">&gt;&gt;</a>' % (nxt)
    return template(HTML_ROOT, vals)

@route('/notify')
def notify():
    '''New notification entry form'''
    vals = dict()
    vals['title'] = 'Notify'
    vals['session'] = request.get_cookie('session', None)
    vals['content'] = ''
    vals['alert'] = ''
    if not vals['session']:
        return template(LOGIN_FORM, vals)
    return template(HTML_FORM, vals)

@post('/close')
def close():
    '''Set closed date on some entry and return to app/doc root page'''
    entry = request.forms.get('entry')
    result = model.close_thread(entry)
    response.set_cookie('alert', urlquote(result))
    return redirect('/')

@route('/confirmation')
def redir():
    '''After confirmation, return to app/doc root page'''
    redirect('/')

@post('/confirmation')
def confirm():
    '''Interstial page to confirm new entry'''
    vals = dict()
    vals['title'] = 'Confirmation'
    vals['session'] = request.get_cookie('session', None)
    vals['name'] = request.forms.get('name')
    vals['subject'] = request.forms.get('subject')
    vals['message'] = request.forms.get('message')
    vals['id'] = model.create_entry(vals['name'], vals['subject'],
                                    vals['message'])
    vals['alert'] = ''
    return template(HTML_CONFIRMATION, vals)

@route('/thread/<entry:int>')
def view_thread(entry):
    '''View thread associated with some entry'''
    entries = model.get_thread_entries(entry)
    vals = dict()
    vals['id'] = entry
    vals['width'] = 72
    vals['root_entry'] = entries[0][0]
    vals['rows'] = entries[:]
    vals['message'] = model.get_message(entry)
    vals['title'] = 'View Thread %s' % vals['root_entry']
    vals['session'] = request.get_cookie('session', None)
    return template(VIEW_THREAD, vals)

@route('/static/<raw_file>')
def static(raw_file):
    '''Return static files
       Especially CSS, JS and such
    '''
    return static_file(raw_file, root='./static')

@route('/login')
@post('/login')
def login():
    '''Process Login and set a cookie'''
    authorized = False
    try:
        name = request.forms.get('name')
        pssd = request.forms.get('pass')
        if name: # No empty names allowed:
            authorized = authenticate(name, pssd)
    except Exception:
        authorized = False
    if authorized:
        response.set_cookie('session', str(authorized).strip())
    return redirect('/')

@route('/logout')
@post('/logout')
def logout():
    '''Process Logout: remove 'session' cookie'''
    session = request.get_cookie('session', None)
    if session:
        response.delete_cookie('session')
        alert = 'Logged out %s' % session
    else:
        alert = 'No session active'
        session = ''
    response.set_cookie('alert', str(alert))
    return redirect('/')


class Command(object):
    '''Collection of commands to be invoked from the command line
       These should all be static methods
    '''

    @staticmethod
    def call(cmd, *args, **opts):
        '''If it's a callable then call it'''
        if hasattr(Command, cmd):
            func = getattr(Command, cmd)
            if callable(func):
                return func(*args, **opts)
        return 'Unknown command'

    @staticmethod
    def backup(filename='notifications.db.bak'):
        '''Call sqlite3 .backup command to perform a backup of the DB'''
        filename = '%s.%s' % (filename, int(time.time()))
        cmd = ['sqlite3', '-batch', 'notifications.db', '.backup %s' % filename]
        try:
            retval = subprocess.call(cmd)
        except EnvironmentError, e:
            return (127, 'Unable to execute sqlite3: %s' % e)
        if retval:
            return (retval, 'Some error occurred: %s' % retval)
        else:
            return (retval, 'Success')


if __name__ == '__main__':
    import sys, os

    if not sqlite3.sqlite_version_info >= (3, 8, 3):
        print >> sys.stderr, 'Error: Must use SQLite version >= 3.8.3 for CTE Support'
        sys.exit(126)

    config = ConfigParser.ConfigParser()
    if 'BOTTLECFG' not in os.environ:
        ini = './settings.ini'
    else:
        ini = os.environ['BOTTLECFG']
    read = config.read(ini)
    if not read:
        print >> sys.stderr, 'Warning: no configuration read'
        print >> sys.stderr, 'No ./settings.ini or $BOTTLECFG not accessible'
        sys.exit(127)

    read = read[0]  # TODO: fix this to handle cascading .ini files?

    try:
        authmod = config.get('Auth', 'module')
        cookie_nonce = config.get('Auth', 'cookie_nonce')
    except ConfigParser.Error, e:
        print >> sys.stderr, 'Configuration Error in %s: %s' % (read, e)
        sys.exit(127)

    if authmod.endswith('.py'):
        authmod = authmod[:-3]

    try:
        auth = __import__(authmod, 'auth')
    except ImportError, e:
        print >> sys.stderr, 'Unable to import module %s: %s' % (authmod, e)
        sys.exit(127)

    if hasattr(auth, 'Auth') and callable(auth.Auth):
        session_mgr = auth.Auth(read)  # Called with the config file we have loaded
        authenticate = session_mgr.authenticate
    else:
        print >> sys.stderr, 'Warning: no Auth() in module %s' % authmod
        authenticate = lambda x, y: False

    arguments = sys.argv[1:]
    if not arguments:  # Start service
        try:
            model = Model()
            debug(True)
            run(host='localhost', port=8080)
        except socket.error, e:
            if e.errno == 48:
                print >> sys.stderr, "Something's already running on port 8080"
                sys.exit(125)
    else:
        command, line = arguments[0], arguments[1:]
        exitval, msg = Command.call(command, *line)
        print >> sys.stderr, msg
        sys.exit(exitval)

