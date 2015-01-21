import argparse
import ldif
import ldap.dn
import ldap.modlist
import ldap
import copy
import sys

parser = argparse.ArgumentParser(description='Load LDIF files into and LDAP server.')
parser.add_argument('ldifs', metavar='LDIF', nargs='+', help='files to parse')
parser.add_argument('-H', dest='url', help='URL of the LDAP server')
parser.add_argument('--merged-attribute', dest='merged_attribute', action='append',
                   default=[], help='attribute that should be merged, not replaced (old value are mixed with the new ones)')

args = parser.parse_args()
args.merged_attribute = map(str.lower, args.merged_attribute)

entries = []

def lower_keys(d):
    return dict((key.lower(), value) for key, value in d.iteritems())

class MyLDIFParser(ldif.LDIFParser):
    def handle(self, dn, entry):
        entries.append((dn, lower_keys(entry)))
print args.ldifs
for ldif in args.ldifs:
    MyLDIFParser(file(ldif)).parse()

entries.sort(key=lambda x: ldap.dn.str2dn(x[0])[::-1])

conn = ldap.initialize(args.url)

adds = []
modifies = []

for dn, attrs in entries:
    try:
        result = ldap.search_s(dn, ldap.SCOPE_BASE)
        old_attrs = lower_keys(result[1][0][1])
        new_attrs = {}
        # keep attributes to merge that are unchanged
        for key in args.merged_attribute:
            if key not in attrs:
                new_attrs[key] = old_attrs[key]
        for key in attrs:
            # merge attributes with their old value
            if key in args.merged_attribute:
                new_attrs[key] = list(set(old_attrs[key])|set(attrs[key]))
            else:
                new_attrs[key] = attrs[key]
        modlist = ldap.modlist.modifyModlist(old_attrs, new_attrs)
        modifies.append((dn, modlist))
    except ldap.NO_SUCH_OBJECT:
        adds.append((dn, ldap.modlist.addModlist(attrs))

for dn, add in adds:
    try:
        conn.add_s(dn, add)
    except ldap.LDAPError, e:
         print >>sys.stderr, 'Unable to create entry %s: %s" % (dn, e)
for dn, modify in modifies:
    try:
        conn.modify_s(dn, modify)
    except ldap.LDAPError, e:
         print >>sys.stderr, 'Unable to modify entry %s: %s" % (dn, e)
