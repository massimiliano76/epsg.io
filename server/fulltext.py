#!/usr/bin/env python
# encoding: utf-8
"""
"""
from bottle import route, run, template, request
import urllib2
import urllib


import sys
import os
from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import *
from whoosh import sorting, qparser, scoring,index, highlight
import re
from pprint import pprint

@route('/',method="GET")
def index():
  
  # Front page without parameters
  if (len(request.GET.keys()) == 0):
    return template('search')
  
  class PopularityWeighting(scoring.BM25F):
     use_final = True
     def final(self, searcher, docnum, score):
       
       popularity = (searcher.stored_fields(docnum).get("popularity"))
       #print score, popularity
       return score * popularity
  
  ix = open_dir("../index")
  result = []
  
  with ix.searcher(closereader=False, weighting=PopularityWeighting()) as searcher:
  #with ix.searcher(closereader=False) as searcher:

         
    parser = MultifieldParser(["code","name","trans","code_trans","kind","area"], ix.schema) #,"wkt"
    parser.add_plugin(qparser.FuzzyTermPlugin()) #jtss~ #jtks~2 #page 40
    
    
    
    query = request.GET.get('q') # p43 - 1.9 The default query language
    query = query.replace("EPSG::","").replace("EPSG:","").replace("::"," ").replace("."," ").replace(":"," ").replace("-"," ").replace(",,"," ").replace(","," ").replace("   "," ").replace("  ", " ")
    select = request.GET.get('kind')
    status = request.GET.get('valid')
    
    if status == None:
      advance_query = query + " kind:" + select + " status:1"
    else:
      advance_query = query + " kind:" + select + " status:" + status
      
       
   # if query != "":
  #    query = query + "~"
      
    myquery = parser.parse(advance_query)
    url_query = urllib2.quote(query)
    
                             
    results = searcher.search(myquery, limit = 50, groupedby="kind", maptype=sorting.Count)   
    groups = results.groups()
    
    num_results = len(results)
    
    for r in results: #[:20]
    
      if r['primary'] == 0 and r['code_trans'] !=0:
        link = str(r['code']) + "-" + str(r['code_trans'])
    
      elif r['primary'] == 1 or r['code_trans'] == 0:
        link = str(r['code'])

      
      result.append({'r':r, 'link':link})
      
        
  return template('results',result=result, groups = groups,num_results=num_results,url_query=url_query,status=status)


@route('/<id:re:[\d]+(-[\d]+)?>/')
def index(id):
  ix = open_dir("../index")
  
  with ix.searcher(closereader=False) as searcher:
    parser = MultifieldParser(["code","code_trans"], ix.schema)
    
    code, code_trans = (id+'-0').split('-')[:2]
    print code_trans
          
    query = "code:" + code + " kind:CRS-*" 
    
    
    myquery = parser.parse(query)
            
    results = searcher.search(myquery)
    
    item = []
    trans = []
    num_results = 0
    url_area = ""
    for e in results:
      
      if code_trans == str(0) and e['primary']==1:
        code_trans = e['code_trans']
      
      if e['code_trans'] == int(code_trans):  
        status = int(e['status'])
      
    for r in results:
      link = str(r['code']) + u"-" + str(r['code_trans'])
      url_area = "/?q=" + urllib2.quote(r['area'].encode('utf-8')) + "&kind=*"
      url_area = url_area.replace(".","")
     
      if code_trans == str(0) and r['primary']==1:
        code_trans = r['code_trans']
      
      me=""
      default = ""
      if r['primary']==1: default = "DEFAULT" 
      if r['code_trans'] == int(code_trans):  
        item.append(r)
        me = 1
      elif status == int(r['status']):
        me = 0
      else:
        continue

      trans.append({
        'me':me,
        'link':link,
        'area_trans':r['area_trans'],
        'accuracy':r['accuracy'],
        'code_trans':r['code_trans'],
        'url_area': url_area,
        'trans_remarks':r['trans_remarks'],
        'default':default})
        
      num_results = len(trans)

  return template('detailed', item=item, trans=trans, num_results=num_results)  


@route('/<id:re:[\d]+(-[\w]+)>/')
def index(id):
  ix = open_dir("../index")

  with ix.searcher(closereader=False) as searcher:
    parser = QueryParser("code", ix.schema)
    myquery = parser.parse(id)
    results = searcher.search(myquery)
    item = []
    detail = []
    url_area = ""
    url_uom = ""
    url_children = ""
    url_prime = ""
    url_axis = []
    
    
    for r in results:
      url_area = "/?q=" + urllib2.quote(r['area'].encode('utf-8')) + "&kind=*"
      url_area = url_area.replace(".","")

      # REPAIR AFTER RELOAD WHOOSHPO : ANGLE->9191, METRE->9001, UNITY->9201
      if 'target_uom' in r:
        if r['target_uom'] != 0:
          if r['target_uom'] == 9102:
            url_uom = "/9101-units/"
          elif r['target_uom'] == 9101:
            url_uom = "/9101-units/"
          elif r['target_uom'] == 9001:
            url_uom = "/9001-units/"
          elif r['target_uom'] == 9201:
            url_uom = "/9201-units/"
     
      if 'prime_meridian' in r:
        if r['prime_meridian'] !=0:
          url_prime = str(r['prime_meridian'])+ "-primemeridian/"

      if 'children_code' in r:
        if r['children_code'] != 0:
          if r['kind'].startswith("Datum-"):
            url_children = str(r['children_code']) + "-ellipsoid/"
          elif r['kind'] == "Axis":
            url_children = str(r['children_code']) +"-coordsys/"
              
          elif r['kind'].startswith("CoordSys-"):
            for c in r['children_code']:
              url = str(c) + "-axis"
              url_axis.append(url)
              
      item.append(r)
      detail.append({'url_prime': url_prime, 'url_children':url_children,'url_axis':url_axis, 'url_uom':url_uom, 'url_area' : url_area})
      
 
  return template('detailed_word', item=item, detail=detail)  






@route('/<id:re:[\d]+(-[\d]+)?>/<format>')
def index(id, format):
  ix = open_dir("../index")
  result = []
  export = ""

  with ix.searcher(closereader=False) as searcher:
    parser = MultifieldParser(["code","code_trans"], ix.schema)

    code, code_trans = (id+'-0').split('-')[:2]
    print code
    print code_trans
    query = "code:"+ code +" code_trans:" + code_trans

    myquery = parser.parse(query)

    result = searcher.search(myquery)[0]

    from osgeo import gdal, osr, ogr
    ref = osr.SpatialReference()
    ref.ImportFromWkt(result['wkt'])

    if format == "esriwkt":
      export = ref.MorphToESRI().ExportToPrettyWkt()
    elif format == "prettywkt":
      export = ref.ExportToPrettyWkt()
    elif format == "usgs":
      export = str(ref.ExportToUSGS())
    elif format == "wkt":
      export = ref.ExportToWkt()
    elif format == "proj4":
      export = ref.ExportToProj4()

  return export

@route('/about')
def index():
  return template('about')

run(host='localhost', port=8080)
  