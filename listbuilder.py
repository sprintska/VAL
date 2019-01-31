#!/usr/bin/env python3

import shutil
import sys
import os
import zipfile
import argparse
import sqlite3
import re
import time
import random
# import update_pieces

PWD = os.getcwd()
# GUID = time.time()
# VLOGFILENAME = "mtmtest2.vlog"
# VLBFILENAME = "mtmtest2.vlb"

parser = argparse.ArgumentParser()
parser.add_argument("-db", help="VLO DB to reference for pieces",type=str,default="vlb_pieces.vlo")
parser.add_argument("-wd", help="working directory to use with VLB",type=str,default=PWD)
parser.add_argument("-vlog", help=".vlog filename",type=str,default="vlb-out.vlog")
parser.add_argument("-vlb", help=".vlb filename",type=str,default="list.vlb")
parser.add_argument("-aff", help=".aff filename",type=str,default="test.aff")
parser.add_argument("-flt", help="fleet list location\r\nVAL will attempt to identify and ingest the list in the given format",type=str,default="list.flt")
parser.add_argument("--imp", help="use VL to import a .vlog to a .vlb",action="store_true")
parser.add_argument("--exp", help="use VL to export a .vlb to a .vlog",action="store_true")
args = parser.parse_args()

g_import_vlb = os.path.abspath(args.vlog)
g_vlb_path = os.path.abspath(args.vlb)
g_working_path = os.path.abspath(args.wd)
g_export_to = os.path.abspath(args.vlog)
g_import_aff = os.path.abspath(args.aff)
g_import_flt = os.path.abspath(args.flt)
g_database = os.path.abspath(args.db)

g_conn = sqlite3.connect(g_database)

    #first sorted list, Vassal is wrong;second, common listbuilders are wrong
nomenclature_translation = {\
    "arquitensclasscommandcruiser":"arquitenscommandcruiser",\
    "arquitensclasslightcruiser":"arquitenslightcruiser",\
    "coloneljendonlambdaclassshuttle":"coloneljendonlambdaclass",\
    "gladiatoriclassstardestroyer":"gladiatori",\
    "gladiatoriiclassstardestroyer":"gladiatorii",\
    "gozanticlassassaultcarriers":"gozantiassaultcarriers",\
    "gozanticlasscruisers":"gozanticruisers",\
    "greensquadronawing":"greensquadronywing",\
    "greensquadronawingsquadron":"greensquadronywingsquadron",\
    "hwk290":"hwk290lightfreighter",\
    "imperialiclassstardestroyer":"imperiali",\
    "imperialiiclassstardestroyer":"imperialii",\
    "imperialstardestroyercymoon1refit":"cymoon1refit",\
    "imperialstardestroyerkuatrefit":"kuatrefit",\
    "lieutenantblountz95headhuntersquadron":"lieutenantblountz95",\
    "mandaloriangauntletfighter":"mandaloriangauntletfightersquadron",\
    "modifiedpeltaclassassaultship":"peltaclassassaultship",\
    "modifiedpeltaclasscommandship":"peltaclasscommandship",\
    "nebulonbsupportrefit":"negulonbsupportrefit",\
    "quasarfireiclasscruisercarrier":"quasarfirei",\
    "quasarfireiiclasscruisercarrier":"quasarfireii",\
    "raidericlasscorvette":"raideri",\
    "raideriiclasscorvette":"raiderii",\
    "stardreadnoughtassaultprototype":"stardnassaultprototype",\
    "stardreadnoughtcommandprototype":"stardncommandprototype",\
    "vcx100freighter":"vcx100lightfreighter",\
    "victoryiclassstardestroyer":"victoryi",\
    "victoryiiclassstardestroyer":"victoryii",\
    "yt1300":"yt1300lightfreighter",\
    "yt2400":"yt2400lightfreighter",\
    "zertikstrom":"zetrikstrom",\
    "zertikstromtieadvancedsquadron":"zetrikstrom",\
    "assaultfrigatemk2a":"assaultfrigatemarkiia",\
    "assaultfrigatemk2b":"assaultfrigatemarkiib",\
    "cr90corelliancorvettea":"cr90corvettea",\
    "cr90corelliancorvetteb":"cr90corvetteb",\
    "lambdashuttle":"lambdaclassshuttle",\
    "lancerpursuitcraft":"lancerclasspursuitcraft",\
    "landocarissian":"landocalrissian",\
    "x17turbolasers":"xi7turbolasers"
    }

  
def unzipall(zip_file_path,tar_path):

    '''Unzips all of the files in the zip file at zip_file_path and
    dumps all those files into directory tar_path.'''

    zip_ref = zipfile.ZipFile(zip_file_path, 'r')
    zip_ref.extractall(tar_path)
    zip_ref.close()


def zipall(tar_path,zip_file_path):

    '''Creates a new zip file at zip_file_path and populates it with
    the zipped contents of tar_path.'''

    shittyname = shutil.make_archive(zip_file_path, 'zip', tar_path)
    shutil.move(shittyname,zip_file_path)


def ident_format(fleet_text):

    formats = {'fab': 0.0,
               'warlord': 0.0,
               'afd': 0.0,
               'kingston': 0.0,
               'aff': 0.0,
               'vlog': 0.0,
               'vlb': 0.0}

    format_names = {'fab': "Fab's Armada Fleet Builder",
                    'warlord': "Armada Warlords",
                    'afd': "Armada Fleets Designer for Android",
                    'kingston': "Ryan Kingston's Armada Fleet Builder",
                    'aff': "Armada Fleet Format",
                    'vlog': "VASSAL Log File",
                    'vlb': "VASSAL Armada Listbuilder"}

    # Fab's
    if ' • ' in fleet_text: formats['fab'] += 1.0
    if 'FLEET' in fleet_text.split('\n')[0]: formats['fab'] += 1.0
    if 'armada.fabpsb.net' in fleet_text.lower(): formats['fab'] += 5.0

    i = 0
    for line in fleet_text.split('\n'):
        try:
            if ' • ' in line:
                if int(line[0]) == i + 1: formats['fab'] += 1
                i += int(line[0])
        except: pass

    # Warlords

    ft = fleet_text.replace("â€¢",u"\u2022")
    if '[ flagship ]' in ft: formats['warlord'] += 3.0
    if 'Armada Warlords' in ft: formats['warlord'] += 5.0
    if 'Commander: ' in ft: formats['warlord'] += 2.0
    for line in ft.split('\n'):
        if "\t points)" in line: formats['warlord'] += 1
        if line.strip().startswith("-  "): formats['warlord'] += .5

    # Armada Fleets Designer
    if '+' in fleet_text: formats['afd'] += 1.0
    if '/400)' in fleet_text.split('\n')[0]: formats['afd'] += 2.0

    for lineloc, line in enumerate(fleet_text.split('\n')):
        if lineloc > 0:
            if (len(fleet_text.split('\n')[lineloc-1]) == line.count('=')+1) and \
               (line.count('=') > 3):
                formats['afd'] += 5.0
                
    # Kingston
    
    if 'Faction:' in ft: 
        formats['kingston'] += 1.0
    if 'Commander: ' in ft: 
        formats['kingston'] += 2.0
    for line in ft.split('\n'):
        # try:
        if line.strip().startswith("• ") or line.strip().startswith(u"\u2022"): 
            #~ print(line.strip())
            formats['kingston'] += 1
        # except: pass

    # AFF
    if fleet_text[0] == "{": formats['aff'] += 30.0
    if fleet_text.startswith("ship:"): formats['aff'] += 30.0
    if fleet_text.startswith("squadron:"): formats['aff'] += 30
    
    print(formats)
    return max(formats.keys(), key=(lambda x: formats[x]))
    

def import_from_list(import_from,output_to,working_path,conn):
    
    ingest_format = {\
        "fab":import_from_fabs,\
        "warlord":import_from_warlords,\
        "afd":import_from_afd,\
        "kingston":import_from_kingston,\
        "aff":import_from_aff,\
        "vlog":import_from_vlog
    }
    
    if os.path.exists(import_from):
        with open(import_from) as fleet_list:
            fleet_text = fleet_list.read()
    else:
        fleet_text = import_from
    
    fmt = ident_format(fleet_text)
    
    print(fmt)
    
    f = ingest_format[fmt](import_from,output_to,working_path,conn)
    
    # write out to .vlb
    
    with open(output_to,"w") as vlb:
        vlb.write("a1\r\nbegin_save{}\r\nend_save{}\r\n".format(chr(27),chr(27)))
        for s in f.ships:
            vlb.write(s.shipcard.content+chr(27))
            vlb.write(s.shiptoken.content+chr(27))
            [vlb.write(u.content+chr(27)) for u in s.upgrades]
        for sq in f.squadrons:
            vlb.write(sq.squadroncard.content+chr(27))
            vlb.write(sq.squadrontoken.content+chr(27))
    

def import_from_fabs(import_list,vlb_path,working_path,conn):

    '''Imports a Fab's Fleet Builder list into a Fleet object'''

    f = Fleet("Food",conn=conn)

    with open(import_list) as fab_in:
        for line in fab_in.readlines():
            
            # all of the lines with useful data are numbered
            
            if line[0].strip().isdigit():
                l = line.replace("â€¢",u"\u2022").strip()
                l = "".join("".join(l.split(" {} ".format(u"\u2022"))[1::]).split(" (")[:-1])
                
                # only ships and objs are broken up with " - ", and objs are labelled
                # otherwise, it's either a squadron or an unupgraded ship--indistinguishable
                
                if " - " in l:
                    if l.startswith("Objective"):
                        # print("=-"*25)
                        # print("Objectives: {}".format(l))
                        pass
                    else:
                        ll = l.split(" - ")
                        s = f.add_ship(ll[0].strip())
                        for u in ll[1::]:
                            s.add_upgrade(u.strip())
                
                else:
                    issquadron = False
                    isship = False
                    issquadronfancy = False
                    l = scrub_piecename(l)
                    if l in nomenclature_translation:
                        l = nomenclature_translation[l]
                                        
                    try: 
                        issquadron = conn.execute('''SELECT * FROM pieces
                                WHERE piecetype='squadroncard' 
                                AND piecename LIKE ?;''',("%"+scrub_piecename(l)+"%",)).fetchall()
                    except: pass
                    
                    try:
                        isship = conn.execute('''SELECT * FROM pieces
                                WHERE piecetype='shipcard' 
                                AND piecename LIKE ?;''',("%"+scrub_piecename(l),)).fetchall()
                    except: pass
                    
                    try: 
                        if l.lower()[-8::] == "squadron":
                            ltmp = l[0:-8]
                            issquadronfancy = conn.execute('''SELECT * FROM pieces
                                    WHERE piecetype='squadroncard' 
                                    AND piecename LIKE ?;''',("%"+scrub_piecename(ltmp)+"%",)).fetchall()
                    except: pass
                    
                    if bool(issquadron):
                        sq = f.add_squadron(l.strip())
                    elif bool(issquadronfancy):
                        sq = f.add_squadron(ltmp.strip())
                    elif bool(isship):
                        s = f.add_ship(l.strip())
                    else:
                        print("{}{} IS FUCKED UP, YO{}".format("="*40,l,"="*40))

    return f


def import_from_warlords(import_list,vlb_path,working_path,conn):

    '''Imports an Armada Warlords list into a Fleet object'''

    f = Fleet("Food",conn=conn)

    with open(import_list) as war_in:
        shipnext = False
        
        for line in war_in.readlines()[7::]:
            
            l = line.strip()
            
            if not l:
                shipnext = True
            
            elif l.split()[1] == "Objective:":
                objective = [l.split()[0],l.split(':')[1]]
                #~ print(objective)
                f.add_objective(objective[0],objective[1])
                shipnext = False
            
            elif l[0].isdigit():
                squadron = ("".join(l.split("(")[0].split()[1::]))
                #~ print(squadron)
                if squadron.lower()[-1] == "s" and not (squadron.lower()[-5:] == "jonus"):
                    squadron = squadron[:-1]
                sq = f.add_squadron(squadron)
                shipnext = False
            
            elif l[0] == "=":
                shipnext = True
                
            elif shipnext:
                ship = l.split("]")[-1].split("(")[0].strip(" -\t")
                #~ print(ship)
                s = f.add_ship(ship)
                shipnext = False
                
            elif l[0] == "-":
                upgrade = l.split("(")[0].strip(" -\t")
                #~ print(upgrade)
                u = s.add_upgrade(upgrade)
                shipnext = False
                        

    return f
    
    
def import_from_afd(import_list,vlb_path,working_path,conn):

    '''Imports an Armada Fleets Designer list into a Fleet object'''

    f = Fleet("Food",conn=conn)

    with open(import_list) as afd_in:
        shipnext = False
        
        for line in afd_in.readlines()[2::]:
            
            l = line.strip().split(" x ",1)[-1]
            
            if l[0] == "+":
                upgrade = l.split("(")[0].strip(" +\t")
                #~ print(upgrade)
                u = s.add_upgrade(upgrade)
            
            else:
                l = l.split(" (")[0]
                
                try: 
                    issquadron = conn.execute('''SELECT * FROM pieces
                            WHERE piecetype='squadroncard' 
                            AND piecename LIKE ?;''',("%"+scrub_piecename(l)+"%",)).fetchall()
                except: pass
                
                try:
                    isship = conn.execute('''SELECT * FROM pieces
                            WHERE piecetype='shipcard' 
                            AND piecename LIKE ?;''',("%"+scrub_piecename(l),)).fetchall()
                except: pass
                        
                if bool(issquadron):
                    sq = f.add_squadron(l.strip())
                elif bool(isship):
                    s = f.add_ship(l.strip())
                else:
                    print("{}{} IS FUCKED UP, YO{}".format("="*40,l,"="*40))

    return f
    
    
def import_from_kingston(import_list,vlb_path,working_path,conn):

    '''Imports an Armada Fleets Designer list into a Fleet object'''

    f = Fleet("Food",conn=conn)

    with open(import_list) as king_in:
        
        shipnext = True
        
        for line in king_in.readlines()[4::]:
            
            l = line.replace("â€¢",u"\u2022").strip()
            
            if l:
                if l.split(":")[0] in ["Assault","Defense","Navigation"]:
                    o = f.add_objective(l.split(":")[0].lower().strip(),\
                                    l.split(":")[1].lower().strip())
                elif shipnext:
                    if l.lower().strip() == "squadrons:":
                        #~ print("[!]SQUADRONS!")
                        shipnext = False
                    elif u"\u2022" in l:
                        #~ print(l)
                        u = s.add_upgrade(l.split(" (",1)[0].strip(u"\u2022"+" "))
                    elif l[0] == "=":
                        pass
                    else:
                        s = f.add_ship(l.split(" (",1)[0].strip())
                else:
                    if l[0] == "=" or not l:
                        pass
                    elif u"\u2022" in l:
                        l = l.split(" x ")[-1].split(" (",1)[0].strip(u"\u2022"+" ")
                        sq = f.add_squadron(l)

    return f


def import_from_aff(import_list,vlb_path,working_path,conn):
    
    '''Imports a .aff (Armada Fleet Format) file into a Fleet object'''
    
    f = Fleet("Food",conn=conn)

    with open(import_list) as aff_in:
        for line in aff_in.readlines():
            
            if line.lower().startswith("ship:"):
                s = f.add_ship(line.split(":")[-1].strip())
                
            elif line.lower().startswith("upgrade:"):
                u = s.add_upgrade(line.split(":")[-1].strip())
                
            elif line.lower().startswith("squadron:"):
                sq = f.add_squadron(line.split(":")[-1].strip())

    return f


def import_from_vlog(import_list,vlb_path,working_path,conn):

    '''Strips out all the compression and obfuscation from a VASSAL
    log/continution .vlog file at path import_from and creates an
    unobfuscated .vlb text file at path vlb_path.'''

    unzipall(import_from,working_path)

    with open(os.path.join(working_path,"savedGame"), 'r') as vlog:
        b_vlog = vlog.read()

    xor_key_str = b_vlog[5:7]
    # print(xor_key_str)
    xor_key = int(xor_key_str,16)
    # print(xor_key)
    obfuscated = b_vlog[6::]
    obf_pair = ""
    clear = ""
    for charloc,char in enumerate(obfuscated):
        obf_pair += char
        if not charloc%2:
            clearint = int(obf_pair,16)^xor_key
            clear += chr(clearint)
            obf_pair = ""
    
    clear = clear[1::].replace("\t","\t\r\n").replace(chr(27),chr(27)+"\r\n\r\n")
    
    with open(vlb_path,"w") as vlb:
        vlb.write(xor_key_str+"\r\n")
        vlb.write(clear)


def export_to_vlog(export_to,vlb_path,working_path=args.wd):

    '''Adds all the obfuscation and compression to turn a .vlb
    VASSAL listbuilder file (at vlb_path), along with boilerplate
    savedata and moduledata XML files in working_path, into a VASSAL-
    compatible .vlog replay file.'''

    out_path = os.path.join(working_path,"out")
    shutil.copyfile(os.path.join(working_path,"moduledata"),os.path.join(out_path,"moduledata"))
    shutil.copyfile(os.path.join(working_path,"savedata"),os.path.join(out_path,"savedata"))

    with open(vlb_path, 'r') as vlb:
        in_vlb = vlb.read()

    in_vlb = in_vlb.replace("\r","").replace("\n","")
    # print(in_vlb[0:2])
    xor_key = int(in_vlb[0:2],16)
    clear = in_vlb[2::]
    # print(in_vlb[0:2])
    # print(in_vlb[2:10])
    obf_out = "!VCSK"+(in_vlb[0:2])
    # print(obf_out)
    for char in clear:
        obfint = ord(char)^xor_key
        obf_out += hex(obfint)[2::]

    with open(os.path.join(out_path,"savedGame"),"w") as savedgame_out:
        savedgame_out.write(obf_out)

    zipall(out_path,os.path.abspath(export_to))


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


def calc_guid():

    return(str(round(random.random()*10**13)))



class Piece:

    '''Meant to be a prototype for the other pieces, not really to be used on its own'''

    def __init__(self,piecename,conn=g_conn):
    
        self.upgradename = scrub_piecename(str(pieceename))
        self.conn = conn
        self.content = conn.execute('''select content from pieces where piecename=?;''',(self.upgradename,)).fetchall()[0][0]

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords


class Fleet:
    
    def __init__(self,name,faction="",points=0,mode="",fleet_version="",description="",objectives={},ships=[],squadrons=[],author="",conn=g_conn):
    
        self.name = str(name)
        self.faction = str(faction)
        self.points = int(points)
        self.mode = str(mode)
        self.fleet_version = str(fleet_version)
        self.description = str(description)
        self.objectives = dict(objectives)
        self.ships = list(ships)
        self.squadrons = list(squadrons)
        self.author = str(author)
        self.conn = conn
        
        # simple piece locations calculations

        self.x = 300
        self.ship_y = 1000
        self.upgd_upper_y = 925
        
        self.sc_to_st_x_padding = 150
        self.sc_to_st_y_padding = 0
        self.s_to_u_padding = 80
        self.u_to_u_x_padding = 105
        self.u_to_u_y_padding = 175
        self.u_to_s_padding = 195
        self.u_to_sq_padding = 195
        self.upgd_lower_y = self.upgd_upper_y + self.u_to_u_y_padding
        self.sq_to_sq_x_padding = 175
        self.sq_to_sq_y_padding = 240
        
        self.sq_y_offset = -120
        self.sq_upper_y = self.ship_y + self.sq_y_offset
        self.sq_lower_y = self.sq_upper_y + self.sq_to_sq_y_padding
        self.sq_row = 1
        
        
    def set_name(self,name):
    
        self.name = str(name)
        
    def set_faction(self,faction):
        
        self.faction = str(faction)
        
    def set_points(self,points):
    
        self.points = int(points)
        
    def set_mode(self,mode):
    
        self.mode = str(mode)
    
    def set_fleet_version(self,fleet_version):
    
        self.fleet_version = str(fleet_version)
    
    def set_description(self,description):
    
        self.description = str(description)
    
    def set_objectives(self,objectives):
    
        self.objectives = dict(objectives)
    
    def add_ship(self,shipclass):
    
        shipclass = scrub_piecename(shipclass)
        #~ print("[+] Add ship: {}".format(shipclass))
        if shipclass in nomenclature_translation.keys():
            #~ print("Translating nomenclature for {}".format(shipclass))
            shipclass = nomenclature_translation[shipclass]
            
        s = Ship(shipclass,self,self.conn)
        self.x += self.u_to_s_padding
        s.set_coords([str(self.x),str(self.ship_y)])
        s.shipcard.set_coords([str(self.x),str(self.ship_y)])
        self.x += self.sc_to_st_x_padding
        s.shiptoken.set_coords([str(self.x),str(self.ship_y+self.sc_to_st_y_padding)])
        self.x += self.s_to_u_padding
        self.u_row = 1
        
        self.ships.append(s)
        return s
        
    def remove_ship(self,ship):
    
        self.ships.remove(ship)
        
    def add_squadron(self,squadronclass):
        
        squadronclass = scrub_piecename(squadronclass)
        if squadronclass in nomenclature_translation.keys():
            squadronclass = nomenclature_translation[squadronclass]
        
        #~ print(squadronclass)
        
        sq = Squadron(squadronclass,self,self.conn)
        if self.sq_row%2:
            self.x += self.sq_to_sq_x_padding
            sq.set_coords([str(self.x),str(self.sq_upper_y)])
            sq.squadroncard.set_coords([str(self.x),str(self.sq_upper_y)])
            sq.squadrontoken.set_coords([str(self.x),str(self.sq_upper_y)])
        else:
            sq.set_coords([str(self.x),str(self.sq_lower_y)])
            sq.squadroncard.set_coords([str(self.x),str(self.sq_lower_y)])
            sq.squadrontoken.set_coords([str(self.x),str(self.sq_lower_y)])
        self.sq_row += 1
        
        self.squadrons.append(sq)
        return sq

    def remove_squadron(self,squadron):
    
        self.squadrons.remove(squadron)
        
    def add_objective(self,category,objective):
        
        category = scrub_piecename(category)
        objective = scrub_piecename(objective)
        
        obj_categories = ["assault","defense","navigation","campaign","other"]
        if category.lower() in obj_categories:
            self.objectives[category] = str(objective)
        else:
            # except:
                # raise ValueError
            print("{} is not a valid objective type.".format(str(category)))
            print("Valid types are: {}".format(obj_categories))
        
    def remove_objective(self,category,objective):
    
        if category in self.objectives.keys:
            if self.objectives[category] == objective:
                del self.objectives[category]
        
    def __add__(self,ship):
    
        self.add_ship(ship)
        
    def __sub__(self,ship):

        self.remove_ship(ship)


class Ship:

    def __init__(self,shipclass,ownfleet,conn=g_conn):
    
        self.shipclass = scrub_piecename(str(shipclass))     # "name" in .AFF
        self.conn = conn
        self.content = ""
        self.coords = [0,0]
        self.physicalsize = [[0,0],[0,0]]           # amt of table space for shipcard, stack, and all upgrades
        self.shipcard = ShipCard(self.shipclass,self.conn)
        self.shiptoken = self.shipcard.shiptoken
        self.upgrades = []
        self.guid = calc_guid()
        
        self.ownfleet = ownfleet
        
    def set_content(self,content):
    
        self.content = str(content)
        
    def set_coords(self,coords):
    
        self.coords = list(coords)
    
    def set_shipcard(self,shipcard):
        
        self.shipcard = shipcard
        
    def set_shiptoken(self,shiptoken):
    
        self.shiptoken = shiptoken
        
    def set_upgrades(self,upgrades):
    
        self.upgrades = list(upgrades)
        
    def add_upgrade(self,upgradename):
        
        upgradename = scrub_piecename(upgradename)
        
        #~ print(upgradename)
        
        if upgradename in nomenclature_translation.keys():
            upgradename = nomenclature_translation[upgradename]
        u = Upgrade(upgradename,self)
        
        if self.ownfleet.u_row%2:
            self.ownfleet.x += self.ownfleet.u_to_u_x_padding
            u.set_coords([str(self.ownfleet.x),str(self.ownfleet.upgd_upper_y)])
        else:
            u.set_coords([str(self.ownfleet.x),str(self.ownfleet.upgd_lower_y)])
        self.ownfleet.u_row += 1
        
        self.upgrades.append(u)
        return u
        
    def remove_upgrade(self,upgrade):
    
        self.upgrades.remove(upgrade)
        
    def __add__(self,upgrade):
    
        self.add_upgrade(upgrade)
        
    def __sub__(self,upgrade):
    
        self.remove_upgrade(upgrade)
        
        
class ShipCard:

    '''A shipcard of type str(shipname) as defined in sqlitedb connection conn.'''

    def __init__(self,shipname,conn=g_conn):
    
        self.shipname = scrub_piecename(str(shipname))
        self.conn = conn
        [(self.content,self.shiptype)] = conn.execute('''select content,catchall from pieces where piecetype='shipcard' and piecename=?;''',(self.shipname,)).fetchall()

        self.shiptoken = ShipToken(self.shiptype,self.conn)

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords
            
    def set_guid(self,guid):
    
        self.content = self.content.replace("vlb_GUID",self.guid)
        
    def set_shiptoken(self,shiptype):
    
        self.shiptoken = ShipToken(shiptype,self.conn)


class ShipToken:

    def __init__(self,shiptype,conn=g_conn):
    
        self.shiptype = scrub_piecename(str(shiptype))
        self.conn = conn
        self.content = conn.execute('''select content from pieces where piecetype='ship' and piecename=?;''',(self.shiptype,)).fetchall()[0][0]

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords
            
            
class Upgrade:

    def __init__(self,upgradename,ownship,conn=g_conn):
    
        self.upgradename = scrub_piecename(str(upgradename))
        self.conn = conn
        self.content = conn.execute('''select content from pieces where piecetype='upgradecard' and piecename=?;''',(self.upgradename,)).fetchall()[0][0]

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
        self.ownship = ownship
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords
            

class Squadron:

    def __init__(self,squadronclass,ownfleet,conn=g_conn):
    
        self.squadronclass = scrub_piecename(str(squadronclass))     # "name" in .AFF
        self.conn = conn
        self.content = ""
        self.coords = [0,0]
        self.squadroncard = SquadronCard(self.squadronclass,self.conn)
        self.squadrontoken = self.squadroncard.squadrontoken
        self.upgrades = []
        self.guid = calc_guid()
        
        self.ownfleet = ownfleet
        
    def set_content(self,content):
    
        self.content = str(content)
        
    def set_coords(self,coords):
    
        self.coords = list(coords)
    
    def set_squadroncard(self,squadroncard):
        
        self.squadroncard = squadroncard
        
    def set_squadrontoken(self,squadrontoken):
    
        self.squadrontoken = squadrontoken
    

class SquadronCard:

    '''A squadroncard of type str(squadronname) as defined in sqlitedb connection conn.'''

    def __init__(self,squadronname,conn=g_conn):
    
        self.squadronname = scrub_piecename(str(squadronname))
        self.conn = conn
        # print("[*] Retrieving {}".format(self.squadronname))
        try:
            [(self.content,self.squadrontype)] = conn.execute('''select content,catchall from pieces where piecetype='squadroncard' and piecename like ?;''',(self.squadronname,)).fetchall()
        except:
            [(self.content,self.squadrontype)] = conn.execute('''select content,catchall from pieces where piecetype='squadroncard' and piecename like ?;''',("%"+self.squadronname+"%",)).fetchall()

        self.squadrontoken = SquadronToken(self.squadrontype,self.conn)

        # self.guid = str(round(time.time()*1000))
        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords
            
    def set_guid(self,guid):
    
        self.content = self.content.replace("vlb_GUID",self.guid)
        
    def set_squadrontoken(self,squadrontype):
    
        self.squadrontoken = SquadronToken(squadrontype,self.conn)
    
    
class SquadronToken:

    def __init__(self,squadrontype,conn=g_conn):
    
        self.squadrontype = scrub_piecename(str(squadrontype))
        self.conn = conn
        # print(squadrontype)
        self.content = conn.execute('''select content from pieces where piecetype='squadron' and piecename=?;''',(self.squadrontype,)).fetchall()[0][0]

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID",self.guid)
        self.content = self.content.replace("vlb_x_axis","0")
        self.content = self.content.replace("vlb_y_axis","0")
        self.coords = [0,0]
        
    def set_coords(self,coords):
    
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub("Table;\d{1,4};\d{1,4}","Table;{};{}".format(str(coords[0]),str(coords[1])),self.content)
            self.coords = coords
    

if __name__ == "__main__":
    if args.imp:
        import_from_list(import_from=g_import_flt,output_to=g_vlb_path,working_path=g_working_path,conn=g_conn)
    
    if args.exp:
        export_to_vlog(export_to=g_export_to,vlb_path=g_vlb_path)
    
