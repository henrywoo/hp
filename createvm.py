#!/usr/bin/env python

import sys
import json
import random
import libvirt
import subprocess as sp
from xml.etree import ElementTree

class Template(object):
    def __init__(self,s):
        self.temp = s

    def render(self,**kwargs):
        str = self.temp
        for key, value in kwargs.iteritems():
            str = str.replace('{{'+key+'}}',value)
        return str

def randomUUID(conn):
    if hasattr(conn, "_virtinst__fake_conn_predictable"):
        # Testing hack
        return "00000000-1111-2222-3333-444444444444"
    u = [random.randint(0, 255) for ignore in range(0, 16)]
    u[6] = (u[6] & 0x0F) | (4 << 4)
    u[8] = (u[8] & 0x3F) | (2 << 6)
    return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
                     "%02x" * 6]) % tuple(u)

def vm_uuid_collision(conn, uuid):
    """
    Check if passed UUID string is in use by another guest of the connection
    Returns true/false
    """
    return libvirt_collision(conn.lookupByUUIDString, uuid)


def libvirt_collision(collision_cb, val):
    """
    Run the passed collision function with val as the only argument:
    If libvirtError is raised, return False
    If no libvirtError raised, return True
    """
    check = False
    if val is not None:
        try:
            if collision_cb(val) is not None:
                check = True
        except libvirt.libvirtError:
            pass
    return check

def generate_uuid(conn):
    for ignore in range(256):
        uuid = randomUUID(conn)
        if not vm_uuid_collision(conn, uuid):
            return uuid

class vnetworkgenerator(object):
    '''create virtual network'''
    def __init__(self, conn, conf):
        self.conn = conn
        self.conf = conf

    def create(self):
        t = Template('<network><name>{{name}}</name><uuid>{{uuid}}</uuid>'
                     '{{forwardstr}}<domain name="{{name}}"/>'
                     '<ip address="{{address}}" netmask="{{netmask}}">{{dhcpstr}}</ip></network>')
        dhcpstr=''
        if self.conf['dhcp'].lower()=='true':
            t2=Template('<dhcp><range start="{{dhcp_start}}" end="{{dhcp_end}}"/></dhcp>')
            dhcpstr=t2.render(dhcp_start=self.conf['dhcp_start'],
                 dhcp_end=self.conf['dhcp_end'])

        mode  = ''; devstr = ''
        forward = self.conf.has_key('forward') and self.conf['forward'].lower()!='isolation'
        if forward:
            mode = self.conf['forward']
            if (mode.lower()=='nat' or mode.lower()=='route') \
                    and self.conf.has_key('dev'):
                dev = self.conf['dev']
                devstr='dev ="{}"'.format(dev)
        forwardstr=''
        if forward:
            forwardstr = '<forward mode="{}" {}/>'.format(mode,devstr)

        xml = t.render(name=self.conf['name'],
                 uuid=generate_uuid(self.conn),
                 address=self.conf['gw'],
                 netmask=self.conf['netmask'],
                 dhcpstr=dhcpstr,
                 forwardstr=forwardstr
                 )
        net = None

        net = self.conn.networkDefineXML(xml)
        try:
          net.create()
          net.setAutostart(1)
        except Exception, e:
          if "is already in use" in str(e):
              print "Error: Your network setting in json file conflicts " \
                    "with the existing network. Please fix your json file."
          if net is not None:
              if net.isActive():
                net.destroy()
              net.undefine()
          return None
        return net

class vmgenerator(object):
    '''create virtual machine'''
    @staticmethod
    def _gateway_ipaddr_to_network(ipaddr):
        octets = ipaddr.split('.')
        # smarty pants
        octets[3] = str(int(octets[3]) - 1)
        return '.'.join(octets)

    @staticmethod
    def _fetch_network_data(network):
        network_data = {'name': network.name()}

        root = ElementTree.fromstring(network.XMLDesc())
        network_data['dhcp'] = root.find('./ip/dhcp') is not None
        root_ip = root.find('./ip')
        if root_ip is not None:
          network_data['netmask'] = root_ip.attrib['netmask']
          network_data['network'] = vmgenerator._gateway_ipaddr_to_network(root_ip.attrib['address'])

        network_data['dhcp_start'] = root.find('./ip/dhcp/range').attrib['start'] if network_data['dhcp'] else None
        network_data['dhcp_end'] =  root.find('./ip/dhcp/range').attrib['end'] if network_data['dhcp'] else None

        return network_data

    def __init__(s):
        s.conn = libvirt.open('qemu:///system')
        if s.conn is None:
            print "Error: kvm is not running."
            sys.exit(0)
        s.domains = s.conn.listAllDomains()
        s.netwrks = s.conn.listAllNetworks()


    def getconn(self):
        return self.conn

    def readconf(s,fname):
        with open(fname) as f:
            c=f.read()
        s.conf=json.loads(c)
        return s.conf

    def checkconf(s):
        # check network
        ##########################################################################
        network_data_map = {}
        network_data = [vmgenerator._fetch_network_data(i) for i in s.netwrks]
        for i in network_data:
            network_data_map[i['name']] = i
        #print 'nwk:',network_data
        info = s.conf['vm']
        #print 'conf:',info

        new_networks=[]

        print "*"*50
        for i in info:
            ns = i['network']
            for n in ns:
                #print n
                nwname = n['name']
                if nwname in new_networks:
                    continue
                if network_data_map.has_key(nwname):
                    #check if the network setting is correct
                    d = network_data_map[nwname]
                    conf_dhcp = n['dhcp'].lower()=='true'
                    if d['dhcp'] != conf_dhcp:
                        print "Error: the network {} is already existing and " \
                              "has a different dhcp setting with yours.".format(nwname)
                        sys.exit(0)
                    else:
                        if d['dhcp']:
                            if d['dhcp_start'] != n['dhcp_start'] or d['dhcp_end'] != n['dhcp_end']:
                                print "Error: the network {} is already existing and " \
                              "has a different dhcp setting with yours.".format(nwname)
                                sys.exit(0)
                    #print "network {} is already there".format(nwname)
                else:
                    print "Creating network {}...".format(nwname)
                    try:
                        vn = vnetworkgenerator(s.getconn(),n)
                        r = vn.create()
                        if r is None:
                          print "Creating network {} failed.".format(nwname)
                          sys.exit(0)
                    except Exception, e:
                        print("Error:: %s" % str(e))
                        sys.exit(0)
                    new_networks.append(nwname)
        ##########################################################################

        # check name
        ##########################################################################
        existingdnames = [i.name() for i in s.domains]
        #print existingdnames
        for i in info:
            dname = i['name']
            #print dname
            if dname in existingdnames:
                print "Error: the VM {} is already existing.".format(dname)
                sys.exit(0)

    def createvm(self):
        cmd='sudo python /usr/bin/virt-install -n {{name}} --pxe --os-type=Linux ' \
              '--os-variant=ubuntutrusty --ram={{ram}} --vcpus={{cpu}} --disk ' \
              'path=/var/lib/libvirt/images/{{name}}.img,bus=virtio,size={{disksize}} --graphics vnc ' \
              '{{networkstring}} --noreboot --force --quiet --noautoconsole'
        t = Template(cmd)

        info = self.conf['vm']
        for i in info:
            nname = [j['name'] for j in i['network']]
            networkstring =''
            for x in nname:
                networkstring = networkstring+" --network network="+x
            cmdstr=t.render(name=i['name'],
                     ram=i['ram'],
                     cpu=i['cpu'],
                     disksize=i['disk'],
                     networkstring=networkstring,
                     network=i['network'][0]['name']
                     )
            #print cmdstr
            step1 = sp.call(cmdstr, shell=True)
            if step1 == 0:
              print 'VM {} has been created successfully.'.format(i['name'])
            else:
              print 'VM {} creation failed.'.format(i['name'])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "syntax:\n\tcreatevm.py xxx.json"
        sys.exit(0)
    vg = vmgenerator()
    vg.readconf(sys.argv[1])
    vg.checkconf()
    vg.createvm()
