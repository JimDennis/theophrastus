#!/usr/bin/env python
'''Simple "message in a bottle" application
'''
from bottle import post, redirect, request, route, run, template
import sqlite3

html = '''<!DOCTYPE html><html><head><title>{{title}}</title></head>
<body>
%s
</body></html>'''

form = '''<form action="/confirmation" method="POST">
Who shall I notify:
<input type="text" name="name"><br />
What is your message:<br />
<textarea name="message" cols="80" rows="25">{{content}}</textarea><br />
<input type="submit" value="Notify">
</form>'''

html_form = html % form

confirmation = '''
<p>{{name}} has been been sent message ID {{id}}:
<blockquote>{{message}}
</blockquote>
<a href="/">Done</a>'''

html_confirmation = html % confirmation

docroot = '''
<p><h3>Current Notices:</h3></p>
<table>
<tr><th>Notice ID</th><th>Recipient</th><th>Date</th><th>Message</th></tr>
%for row in rows:
  %id=row[0]
  <tr>
  %for col in row:
    <td>{{col}}</td>
  %end
    <td>
    <form action="/close" method="POST">
    <input type="submit" value="Close" />
    <input name="entry" type="hidden" value="{{id}}" />
    </form></td>
  </tr>
%end
</table>
<p><h3><a href='/notify'>Send new notification</a></h3></p>'''

html_root = html % docroot

class Model(object):
    '''Maintain the DB for notifications
    '''
    def __init__(self, dbfile='./notifications.db'):
        '''Create table if necessary otherwise use existing data
        '''
        self.filename = dbfile
        self.db = sqlite3.connect(self.filename)
        prep_table = """
          CREATE TABLE IF NOT EXISTS notices
            (id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
             name TEXT NOT NULL,
             message TEXT NOT NULL,
             postdate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
             closedate DATETIME DEFAULT NULL)"""
        self.db.execute(prep_table)
        self.db.commit()
    def get_open_entries(self, count=20, offset=0, width=72):
        '''Get some of the open entries and summary of the contents
           Defaults are suitable for the default index/root page
        '''
        get_entries = '''SELECT id, name, postdate, SUBSTR(message, 1, ?)
          FROM notices WHERE closedate IS NULl ORDER BY id DESC
          LIMIT ? OFFSET ?'''
        args = (width, count, offset)
        current = self.db.execute(get_entries, args)
        return current.fetchall()
    def create_entry(self, name, message):
        '''Create a new "open" entry
        '''
        stmt = "INSERT INTO notices (name, message) VALUES (?, ?)"
        newrow = self.db.execute(stmt, (name, message))
        self.db.commit()
        return newrow.lastrowid
    def close_entry(self, entry):
        '''Mark a entry as "closed" (set a closing date on it)
        '''
        chk = "SELECT id, name, postdate, message, closedate FROM notices WHERE id=?"
        row = self.db.execute(chk, (entry,))
        if row:
            row = row.fetchone()
            if row[4] is not None:
                return 'Entry %s was already closed on %s' % (row[0], row[4])
        else:
            return 'Bad entry: Cannot close'
        self.db.execute("UPDATE notices set closedate=DATETIME('NOW') WHERE id=?", (entry,))
        self.db.commit()
        return 'Entry_%s_closed' % row[0]

@route('/')
def root():
    vals = dict()
    vals['title'] = 'Notification System'
    vals['rows'] = model.get_open_entries()
    return template(html_root, vals)

@route('/notify')
def notify():
    return template(html_form, title='Notify', content='')

@route('/confirmation')
def redir():
    redirect('/')

@post('/close')
def close():
    entry = request.forms.get('entry')
    result = model.close_entry(entry)
    return redirect('/?result=%s' % result)

@post('/confirmation')
def confirm():
    vals = dict()
    vals['title'] = 'Confirmation'
    vals['name'] = request.forms.get('name')
    vals['message'] = request.forms.get('message')
    vals['id'] = model.create_entry(vals['name'], vals['message'])
    return template(html_confirmation, vals)

if __name__ == '__main__':
    model = Model()
    run(host='localhost', port=8080, debug=True)

