#!/usr/bin/env python
"""date: 03/26/2015"""
import sys
import subprocess as sp

PATTERN = 'Depends:'
DEBUG = 0
PROGR = 0

def run_bg():
  if PROGR: print 'Preparing for analyzing...(apt-get update)...'
  step1 = sp.call('apt-get update >/dev/null 2>&1',shell=True)
  if step1 == 0:
    if PROGR: print 'Starting to analyze depends...'
  else:
    print 'Error: apt-get update failed. Please fix it!'
    sys.exit(0)

def __getdeps(pkg):
  '''get 1st deps of pkg'''
  _dlist=set()
  cmd = 'apt-cache show ' + pkg
  p=sp.Popen(['apt-cache','show',pkg], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
  output, err = p.communicate()
  rc = p.returncode
  if rc == 0:
    deps = [s[len(PATTERN):].strip() for s in output.splitlines() if s.startswith(PATTERN)]
    deps = [i.split(', ') for i in deps]
    for i in deps:
      for j in i:
        if ' (' in j:
            _dlist.add(j.split(' (')[0])
        elif ' | ' in j:
            [_dlist.add(k) for k in j.split(' | ')]
        else:
            _dlist.add(j)
  else:
    pass
    #print "Error: "+err
  return _dlist

def getdeps(pkg):
  """ old(analyzed), new(todo), tmp"""
  if PROGR: print "Analyzing {} depends...".format(pkg)
  deps_old=set()
  deps_new=set()
  deps_new = __getdeps(pkg)
  #deps_old.add(pkg)
  if DEBUG: print "Analyzed\tTODO"
  while len(deps_new)>0:
    tset=set()
    for i in deps_new:
      deps_old.add(i)
      tmp = __getdeps(i)
      [tset.add(x) for x in tmp if x not in deps_old and x not in deps_new]
    deps_new = tset
    if DEBUG: print tset
    if DEBUG: print "{}\t\t{}".format(len(deps_old),len(deps_new))
  if DEBUG: print "-"*50
  return deps_old

def get_from_file(pkgfile):
  glist=set()
  with open(pkgfile) as f:
    pkgs = [i.strip() for i in f.readlines() if not i.startswith('#') and len(i.strip())>0]
  for pkg in pkgs:
    dps = getdeps(pkg)
    glist = glist.union(dps)
    if DEBUG: print "{} depends:\n{}\n".format(pkg,str(dps))
  return glist

if __name__ == '__main__':
  if len(sys.argv) != 2:
    print "syntax:\n\tdeplist.py pkgfile"
    sys.exit(0)
  run_bg()
  pkgfile = sys.argv[1]
  globaldepends = list(get_from_file(pkgfile))
  if PROGR: print "\nTotal Number:{}".format(len(globaldepends))
  if PROGR: print "*"*50
  print globaldepends
