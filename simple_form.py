#!/usr/bin/env python
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

@route('/')
def root():
    vals = dict()
    vals['title'] = 'Notification System'
    get_entries = '''SELECT id, name, postdate, SUBSTR(message,1,72)
      FROM notices WHERE closedate IS NULL ORDER BY id DESC LIMIT 40'''
    current = db.execute(get_entries)
    rows = current.fetchall()
    vals['rows'] = rows
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
    chk = "SELECT id, name, postdate, message, closedate FROM notices WHERE id=?"
    row = db.execute(chk, (entry,))
    if row:
        row = row.fetchone()
        if row[4] is not None:
            return 'Entry %s was already closed on %s' % (row[0], row[4])
    else:
        return 'Bad entry: Cannot close'
    db.execute("UPDATE notices set closedate=DATETIME('NOW') WHERE id=?", (entry,))
    db.commit()
    return redirect('/')

@post('/confirmation')
def confirm():
    vals = dict()
    vals['title'] = 'Confirmation'
    vals['name'] = request.forms.get('name')
    vals['message'] = request.forms.get('message')
    newrow = db.execute("INSERT INTO notices (name, message) VALUES (:name,:message)", vals)
    vals['id'] = newrow.lastrowid
    db.commit()
    return template(html_confirmation, vals)

if __name__ == '__main__':
    db = sqlite3.connect('./notifications.db')
    prep_table = """
      CREATE TABLE IF NOT EXISTS notices
        (id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
         name TEXT NOT NULL,
         message TEXT NOT NULL,
         postdate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
         closedate DATETIME DEFAULT NULL)"""
    db.execute(prep_table)
    db.commit()
    existing = db.execute("SELECT * FROM notices")
    run(host='localhost', port=8080, debug=True) ### , reloader=True)

