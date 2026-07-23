import urllib.request, ssl, json
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
def tryu(u, insecure=False):
  h={"User-Agent":UA,"Accept":"*/*"}
  ctx=ssl.create_default_context()
  if insecure:
    ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
  try:
    req=urllib.request.Request(u,headers=h)
    with urllib.request.urlopen(req,timeout=25,context=ctx) as r:
      b=r.read(400)
      print("OK", r.status, u[:75], repr(b[:50]))
  except Exception as e:
    print("NO", str(e)[:65], u[:75])

for u,ins in [
 ("https://urlhaus-api.abuse.ch/v1/urls/recent/", True),
 ("https://urlhaus.abuse.ch/downloads/csv_recent/", True),
 ("https://www.gpsjam.org/data", False),
 ("https://gpsjam.org/", False),
 ("https://api.corruptionrisk.cc/", False),
 ("https://www.who.int/rss-feeds/news-english.xml", False),
 ("https://www.ecdc.europa.eu/en/taxonomy/term/2942/feed", False),
 ("https://tools.cdc.gov/api/v2/resources/media/132609.rss", False),
 ("https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.rss.xml", False),
 ("https://www.gov.uk/foreign-travel-advice.atom", False),
 ("https://smartraveller.gov.au/countries/feed", False),
 ("https://www.oref.org.il/WarningMessages/alert/alerts.json", False),
 ("https://www.oref.org.il/WarningMessages/History/AlertsHistory.json", False),
 ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson", False),
 ("https://firms.modaps.eosdis.nasa.gov/api/area/csv/", False),
 ("https://eonet.gsfc.nasa.gov/api/v3/categories", False),
 ("https://api.openbridge.io/", False),
 ("https://www.ngdc.noaa.gov/hazel/rest/V1/get/satellites", False),
 ("https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json", False),
 ("https://finance.yahoo.com/rss/topfinstories", False),
 ("https://feeds.bbci.co.uk/news/business/rss.xml", False),
]:
  tryu(u,ins)
