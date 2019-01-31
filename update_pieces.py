#!/usr/bin/env python3

import shutil
import sys
import os
import zipfile
import argparse
import re
import sqlite3

PWD = os.getcwd()

parser = argparse.ArgumentParser()

parser.add_argument("from_file", 
                    help="import listbuilder objects (vlo) from file",
                    type=str,default=os.path.abspath("test.vlb"))
parser.add_argument("--db", 
                    help="sqlite db location",
                    type=str,
                    default="vlb_pieces.vlo")
parser.add_argument("--purgedb",help="purge the database (BACKUP FIRST)",
                    action="store_true")
                    
args = parser.parse_args()

g_from_file = os.path.abspath(args.from_file)
g_db_path = os.path.abspath(args.db)
dopurge = args.purgedb


def create_db(db_path=g_db_path):
    
    '''Create the db at the path if it doesn't exist'''
    
    if not os.path.exists(db_path): 
        open(db_path,"w")
    
        conn = sqlite3.connect(db_path)
        
        conn.execute('CREATE TABLE pieces (piecetype text, piecename text, content text, catchall text)')
        conn.commit()
        conn.close()


def exists_piece(conn,piecetype,piecename):
    
    '''checks for existence of piece name/type.'''
    
    return bool(conn.execute('''SELECT * FROM pieces
                                WHERE piecetype=? 
                                AND piecename=?;''',(piecetype,piecename)).fetchall())
                                

def create_piece(conn,piecetype,piecename,content,catchall=""):
    
    '''Creates an piece entry of type in the conn db.
    
    conn takes a sqlite3.connect object.'''
    
    if not exists_piece(conn,piecetype,piecename):
                
        conn.execute('''INSERT INTO pieces VALUES (?,?,?,?)''',\
                     (piecetype,piecename,content,catchall))
        conn.commit()


def update_piece(conn,piecetype,piecename,content,catchall):

    '''updates the content of an existing entry'''

    conn.execute('''UPDATE pieces 
                    SET content=? ,
                        catchall=?
                    WHERE piecename=?
                    AND piecetype=?''',(content,catchall,piecename,piecetype))
    conn.commit()
    

def purge_db(db_path=g_db_path):
    
    '''Deletes the db.'''
    
    if not os.path.exists(db_path): return
    
    os.remove(db_path)
    
    
def scrub_piecename(piecename):
    piecename = piecename.replace("\/","")\
                         .split("/")[0]\
                         .split(";")[-1]\
                         .replace(" ","")\
                         .replace(":","")\
                         .replace("!","")\
                         .replace("-","")\
                         .replace("'","")\
                         .replace("(","")\
                         .replace(")","")\
                         .lower()
    return piecename
        

def import_vlo_from(from_file=g_from_file,to_db=g_db_path):

    '''Parses the ship definitions from a .vlb file.'''

    with open(from_file, 'r') as vlb:
        vlb_str = vlb.read()
        
    vlb_str = vlb_str.replace("\r","").replace("\n","")
    vlb_str = (chr(27)+"LOG").join(vlb_str.split(chr(27)+"LOG")[1::])
    
    signature = {
        "objective": "obj_back.png",
        "obstacle": "Actual Obstacle",
        "ship": \
            "Ship\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\"+\
            "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\t"+\
            "Capital\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\"+\
            "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\t",
        "shipcard": "shipcard_",
        "squadron": "squad_base.png",
        "squadroncard": "placemark;Spawn squadron",
        "upgradecard": "upgrade_back_"
        }
    
    piecetypes = list(signature.keys())
    piecetypes.append("other")
    create_db(to_db)
    
    conn = sqlite3.connect(to_db)
    
    for entry in vlb_str.split(chr(27)):
        
        piecetype = "other"
        piecename = ""
        content = re.sub("\d{13}","vlb_GUID",entry)
        content = re.sub("Table;\d{1,4};\d{1,4};","Table;vlb_x_axis;vlb_y_axis;",content)
        catchall = ""
        
        
        for key in signature:
            if signature[key] in entry:
                piecetype = key
        
        for piecenameloc in re.finditer('piece;;;',entry):
            
            startloc = piecenameloc.end()
            piecename = entry[startloc:startloc+100]
            piecename = scrub_piecename(piecename)
            
        if len(piecename) > 0:
        
            # associate the ship token to the ship card
            if piecetype == "shipcard":
                ship_token = ""
                if "quasar" in piecename: ship_token = "quasarfirecruisercarrier" # fuck the Quasar, I don't know why it can't be fucking normal
                else:
                    for line in entry.split("\t"):
                        if line.startswith("placemark;Spawn") and ("Capital Ships" in line):
                            ship_token = line.split("\\/VASSAL.build.widget.PieceSlot:")[-1]\
                                            .split(";")[0]
                            ship_token = scrub_piecename(ship_token)
                catchall = ship_token
                
            # associate the squadron token to the squadron card
            if piecetype == "squadroncard":
                sqd_token = ""
                for line in entry.split("\t"):
                    if line.startswith("placemark;Spawn squadron"):
                        sqd_token = line.split("\\/VASSAL.build.widget.PieceSlot:")[-1]\
                                        .split(";")[0]
                        sqd_token = scrub_piecename(sqd_token)
                catchall = sqd_token

                # testing
                if not exists_piece(conn,"squadron",catchall):
                    print("{} all fucked up".format(catchall))
                # /testing
        
            if exists_piece(conn,piecetype,piecename):
                print("[^]{} exists, updating it...".format(piecetype+"-"+piecename))
                update_piece(conn,piecetype,piecename,content,catchall)
            else:
                print("[+]{} does not exist, creating it...".format(piecetype+"-"+piecename))
                create_piece(conn,piecetype,piecename,content,catchall)
                


    out = conn.execute("SELECT piecetype, piecename, catchall FROM pieces").fetchall()
    
    conn.close()
    
    return sorted(out)


if __name__ == "__main__":
    if dopurge:  purge_db(g_db_path)
    else:  [print(x) for x in import_vlo_from(from_file=g_from_file,to_db=g_db_path)]
    
