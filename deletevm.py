#!/usr/bin/env python

import sys, os
import libvirt
from xml.etree import ElementTree

class vmterminator(object):
    def __init__(s):
        s.conn = libvirt.open('qemu:///system')
        if s.conn is None:
            print "Error: kvm is not running."
            sys.exit(0)
        s.domains = s.conn.listAllDomains()
        s.netwrks = s.conn.listAllNetworks()

    def __delete(self,domain):
        root = ElementTree.fromstring(domain.XMLDesc())
        disksource = root.find('./devices/disk/source')
        name = domain.name()
        if disksource is not None:
            imgpath = disksource.attrib['file']

            if domain.isActive():
                domain.destroy()
            vol = None
            '''try:
                vol = self.conn.storageVolLookupByPath(imgpath)
            except:
                print "Path '%s' is not managed. Deleting locally" % (imgpath)'''
            if vol is not None:
                vol.delete(0)
            else:
                os.unlink(imgpath)

            flags = 0
            flags |= getattr(libvirt, "VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA", 0)
            flags |= getattr(libvirt, "VIR_DOMAIN_UNDEFINE_MANAGED_SAVE", 0)
            try:
                domain.undefineFlags(flags)
            except libvirt.libvirtError:
                domain.undefine()
            print "VM {} is deleted successfully!".format(name)


    def delete_domain(self,vmlist):
        name2domain={}
        for i in self.domains:
            name2domain[i.name()] = i
        for vm in vmlist:
            if name2domain.has_key(vm):
                self.__delete(name2domain[vm])
            else:
                print "VM {} is not existing and cannot be deleted.".format(vm)


    def delete_network(self, namelist):
        name2nw = {}
        for i in  self.conn.listAllNetworks():
            name2nw[i.name()] = i
        for name in namelist:
            if not name2nw.has_key(name):
                print "Network {} doesn't exist!".format(name)
            else:
                n = name2nw[name]
                n.destroy()
                n.undefine()
                print "network {} is deleted successfully!".format(name)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "\nSYNOPSIS:\n" \
              "\tsudo python deletevm.py [VMname] [-n Networkname]" \
              "\n\nDESCRIPTION:\n\t" \
              "This script will delete VM by name. " \
              "You can also add '-n networkname1 networkname1' to delete network." \
              "\n\teg." \
              "\n\t\tsudo python deletevm.py vmx1 vmx2 vmx3\n" \
              "\t\tsudo python deletevm.py vmx1 vmx2 vmx3 -n pxe pxe2" \
              "\n\tPlease use it carefully and do not forget to do backup if necBy default, tessary."

        sys.exit(0)
    vmlist=[]
    nwlist=[]
    m=0
    for i in sys.argv[1:]:
        if i=='-n':
            m=1
            continue
        if m==1:
            nwlist.append(i)
        else:
            vmlist.append(i)

    dvm = vmterminator()
    if os.geteuid()!=0:
        print "please run this program with sudo."
        sys.exit(0)
    if len(vmlist)>0:
        dvm.delete_domain(vmlist)
    if len(nwlist)>0:
        dvm.delete_network(nwlist)


