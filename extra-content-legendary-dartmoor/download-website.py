from lxml import html , etree
from more_itertools import unique_everseen
import nltk.data
import numpy as np
import requests
import re
import sys

def filter_images( img ):
  if re.match( ".*paypalobjects.com.*" , img ): return False
  if re.match( ".*/Head.*" , img ): return False
  if re.match( ".*Button.*" , img ): return False
  if re.match( ".*Ancient.gif" , img ): return False
  if re.match( ".*Findme.gif" , img ): return False
  if re.match( ".*/Home", img): return False
  if re.match( ".*/Readlist.*", img): return False
  if re.match( ".*/Ancmon.*", img): return False
  if re.match( ".*Facebook.*", img): return False
  if re.match( ".*OSGrid.*", img): return False
  if re.match( ".*/Private.*", img): return False
  if re.match( ".*/Textref.*", img): return False
  if re.match( ".*/Contact.*", img): return False
  if re.match( ".*/Location[1-9].*", img): return False
  if re.match( ".*/Copyright.*", img): return False
  if re.match( ".*/Return.*", img): return False
  return True

def filter_urls ( url , onlyexternal=True ):
  if onlyexternal and not( re.match("http:.*", url) ): return False
  if re.match( ".*http:.*", url ): return False
  if re.match( ".*\.gif" , url ): return False
  if re.match( ".*\.jpg" , url ): return False
  if re.match( ".*\.jpeg" , url ): return False
  if re.match( ".*php echo.*", url ): return False
  if re.match( ".*web_cost.htm", url ): return False
  if re.match( ".*Reading_list.htm", url ): return False
  return True

tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
page = requests.get('http://www.legendarydartmoor.co.uk')
maintree = html.fromstring(page.content)
print "<dataset>"
for category in np.array( maintree.xpath('//table//a[.//img]/@href') )[4:]:
  page = requests.get("http://www.legendarydartmoor.co.uk/" + category)
  tree = html.fromstring(page.content)  
  category_title = re.sub(" +", " ", re.sub("&", "&amp;" , re.sub("\.$", "", tree.xpath('//title/text()')[0] ) ) ) 
  category_text	= re.sub("\n\n+" , "\n" , re.sub("  *", " ", re.sub( "\n\t\t+", " ", re.sub("  *", " ", "\n".join( [ txt.strip( ) for txt in tree.xpath('//p[.//font]//text()') ] ).strip( ) ) ) ) )
  category_text = re.sub("\nIf you have found this website helpful please.*", "", category_text , flags=re.MULTILINE|re.DOTALL ).strip( )
  category_text = re.sub("\nContact me.*", "", category_text , flags=re.MULTILINE|re.DOTALL ).strip( )
  category_text = re.sub(">", "&gt;", re.sub("<", "&lt;", re.sub("&", "&amp;", re.sub("\nHERE.*", "", category_text , flags=re.MULTILINE|re.DOTALL ).strip( ) ) ) )
  category_text = "\n".join( tokenizer.tokenize( re.sub("\n" , " ", category_text ) ) )
  category_urls = list( unique_everseen( [ re.sub("&" , "&amp;" , url ) for url in tree.xpath('//tr//td//a[.//font]/@href') if filter_urls(url , onlyexternal=False ) ] ) )
  category_items = list( unique_everseen( [ item.text_content().strip( ) for item in tree.xpath('//tr//td//a[.//font]') if len( item.text_content().strip( ) ) > 0 ] ) )
  images = set( [ re.sub("&" , "&amp;" , "http://www.legendarydartmoor.co.uk/" + img ) for img in tree.xpath('//img/@src') if filter_images(img) ] )
  urls = set( [ re.sub("&" , "&amp;" , url ) for url in tree.xpath('//a/@href') if filter_urls(url) ] )
  print "<category title='" + category_title +  "' url='http://www.legendarydartmoor.co.uk/" + category + "' >"
  print "<text>\n" + category_text.encode("utf-8") + "\n</text>"
  print "<images>"
  for img in images: print "<image>" + img + "</image>"
  print "</images>"
  print "<urls>"
  for url in urls: print "<url>" + url + "</url>"  
  print "</urls>"
  print "<content_list>"
  for i in range( len( category_urls ) ):
    content_title = re.sub(" +", " ", re.sub("&", "&amp;" , re.sub("\.$", "", re.sub( " +", " ", re.sub("'" , '`', re.sub("\n" , " ", category_items[i].encode("utf-8").strip() ) ) ) ) ) )
    content_url = "http://www.legendarydartmoor.co.uk/" + category_urls[i].encode("utf-8").strip()
    print "<content title='" + content_title +  "' url='" + content_url + "'>"
    page_content = requests.get(content_url)
    tree_content = html.fromstring(page_content.content)    
    images = set( [ re.sub("&" , "&amp;" , "http://www.legendarydartmoor.co.uk/" + img ) for img in tree_content.xpath('//img/@src') if filter_images(img) ] )
    urls = set( [ re.sub("&" , "&amp;" , url ) for url in tree.xpath('//a/@href') if filter_urls(url) ] )
    coordinates = re.sub("&" , "&amp;" , " ; ".join( [ txt.strip() for txt in tree_content.xpath('//p//text()') if re.match("^SX [0-9& ]+$" , txt.strip()) ] ) )
    content_text = [ txt.text_content().strip() for txt in tree_content.xpath('//p') if len( txt.text_content().strip() ) > 0 ]

    content_text = [ txt for txt in content_text if not( re.match("^SX [0-9& ]+$" , txt) ) ]
    content_text = [ txt for txt in content_text if not( txt == content_title ) ]
    content_text = "\n".join( content_text )
    content_text = re.sub("\n\n+" , "\n" , re.sub(" +", " ", re.sub( "\n\t\t+", " ", re.sub(" +", " ", content_text ) ) ) )
    content_text = re.sub("\nIf you have found this website helpful.*", "", content_text , flags=re.MULTILINE|re.DOTALL ).strip( )
    content_text = re.sub("\nContact me.*", "", content_text , flags=re.MULTILINE|re.DOTALL ).strip( )
    content_text = re.sub(">", "&gt;", re.sub("<", "&lt;", re.sub("&", "&amp;", content_text , flags=re.MULTILINE|re.DOTALL ).strip( ) ) )
    content_text = "\n".join( tokenizer.tokenize( re.sub("\n" , " ", content_text ) ) )
    print "<coordinates>" + coordinates + "</coordinates>"
    print "<images>"
    for img in images: print "<image>" + img + "</image>"
    print "</images>"
    print "<urls>"
    for url in urls: print "<url>" + url + "</url>"      
    print "</urls>"
    print "<text>"   
    print content_text.encode("utf-8")
    print "</text>"
    print "</content>"
  print "</content_list>"
  print "</category>"
print "</dataset>"
