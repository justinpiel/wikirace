import re
import sqlite3
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup

# lets do this API stuff later and work on making race thing first

#wiki1 = input('Input first Wikipedia Prompt: ')
#wiki2 = input('Input second Wikipedia Prompt: ')

conn = sqlite3.connect('spider.sqlite')
cur = conn.cursor()

cur.executescript('''
                  DROP TABLE IF EXISTS Pages;
                  DROP TABLE IF EXISTS Sources;
                  CREATE TABLE IF NOT EXISTS Pages (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT UNIQUE, parent INTEGER, 
                  progress INT DEFAULT 0, linkgoal INT DEFAULT 0);
                  ''')

# smr 
initial = '/wiki/' + input('Initial? ')
goal = '/wiki/' + input('Goal? ')
progenitor = 0
WIKIORG = 'https://en.wikipedia.org'
goalies = []
goodpath = []
goals2goalies = {}
processcounter = 0

cur.execute('INSERT INTO Pages (url, parent) VALUES (?, ? )', (initial, progenitor ))
conn.commit()

def findlinksto(goal):
    #make page / prep / open 
    goal = goal.split('/')
    goal = goal[2]
    wiki = WIKIORG + '/w/index.php?title=Special:WhatLinksHere/'+goal+'&limit=500'
    opener = urllib.request.urlopen(wiki).read()
    text = BeautifulSoup(opener, 'html.parser')

    #find the area with what links then find a list of all a tags
    listbody = text.find('ul', id='mw-whatlinkshere-list')
    linkiesto = listbody.findAll('a')

    #find each href in link
    for link in linkiesto :
        url = link.get('href', None)
        if url.startswith('/w/') :
            continue

        #add each href to a list of them
        goalies.append(url)
    
    #print(goalies)

def longgoals():
    #get all current urls
    cur.execute('SELECT url FROM Pages')
    urls = cur.fetchall()

    #if any are in new findmorelinks, parse those
    for i in urls :
        for j in goals2goalies :
            for k in j :
                if i == k :
                    cur.execute('UPDATE Pages SET linkgoal=1 WHERE url= ?',[i])


def process_page():
    #see if this url is in db and if not, insert it and get the id
    cur.execute('SELECT id, url FROM Pages WHERE progress is 0 ORDER BY linkgoal DESC, parent LIMIT 1')
    result = cur.fetchall()
    for i in result :
        result = i[1]
        ident = i[0]
    #print(result)
    #print(ident)
    cur.execute('UPDATE Pages SET progress=1 WHERE id= ?', [ident])
    cur.execute('UPDATE Pages SET linkgoal=0 WHERE id= ?', [ident])


    #web request the page
    #prep page open and read it
    wiki = (WIKIORG + result)
    opener = urllib.request.urlopen(wiki).read()
    text = BeautifulSoup(opener, 'html.parser')
    
    #find all <p> tags which is main text
    body = text.find('div', id='mw-content-text')
    #print(body)

    #find all embedded anchor link tags
    try :
        linkies = body.findAll('a')
    except :
        pass

    #loop over the links
    for link in linkies : 
        url = link.get('href', None)
        if url == None :
            continue
        if url.startswith('/wiki/') :
            if url.endswith('.jpg') or url.endswith('.jpeg') or url.endswith('.png') or url.endswith('.svg'):
                continue
            if url.endswith('Citation_needed') or 'Special:Book' in url :
                continue

            #put the data into the database
            cur.execute('INSERT OR IGNORE INTO Pages (url, parent) VALUES (?, ?) ', (url, ident))

            #if we find the right thing get out and go to wincon dialog
            if url == goal :
                cur.execute('UPDATE Pages SET progress=2 WHERE url=?',[url])
                #print('OMG YAY')
                goodpath.append(url)
                break

            #if one of the goalies is found parse that next to find goal
            if url in goalies :
                #print(url)
                cur.execute('UPDATE Pages SET linkgoal=1 WHERE url= ?',[url])

            #once it does findmorelinks do longgoals
            if processcounter == 50 :
                longgoals()


        else : continue

    #mark as processed
    conn.commit()
    return

def findmorelinks():
    goals2counter = 0   

    #for each item in original linksto list 
    for i in goalies :
        tupp = ()
        i = i.split('/')
        i=i[2]
        wiki = WIKIORG + '/wiki/Special:WhatLinksHere/'+i

        #open and html it
        opener = urllib.request.urlopen(wiki).read()
        text = BeautifulSoup(opener, 'html.parser')

        #find the area with what links then find a list of all a tags
        listbody = text.find('ul', id='mw-whatlinkshere-list')
        linkiesto = listbody.findAll('a')

        #find each href in link
        for link in linkiesto :
            url = link.get('href', None)
            if url.startswith('/w/') :
                continue
            
            #keep adding stuff into a tuple
            tupp = tupp + (url,)

        #put key value pair in dict w/ value as tuple
        goals2goalies[i] = tupp

        #update counter so it doesn't go on for too long
        goals2counter = goals2counter + 1
        if goals2counter > 30 :
            break
    #print(goals2goalies)


findlinksto(goal)

testi = 0

#process pages until wincon true
while True :
    process_page()
    processcounter = processcounter + 1
    if goodpath != [] :
        break
    if processcounter == 50 :
        findmorelinks()


#get the first parent to set up for writing a link tree
cur.execute('SELECT parent FROM Pages WHERE progress=2')
parid = cur.fetchone()
parid = parid[0]

#make the link tree
while True :
    cur.execute('SELECT url, parent FROM Pages WHERE id = ?', [parid])
    urlpar = cur.fetchone()
    parid = urlpar[1]
    goodpath.append(urlpar[0])

    #when get to original page break
    if urlpar[0] == initial :
        break
goodpath.reverse()
print(goodpath)