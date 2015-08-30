import os
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
from collections import defaultdict
from sets import Set

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
problemchars_addr = re.compile(r'[=\+/&<>;\'"\?%#$@\,\t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

# Expected street names
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons","Circle","Extension"]

# Mapping needed to update street names
mapping = { 
            "St.": "Street",
            "St": "Street",
            "ST": "Street",
            "Ave": "Avenue",
            "Av": "Avenue",
            "Rd.": "Road",   
            "Rd":"Road",            
# Updated according to the data
            "Dr.":"Drive",            
            "Dr":"Drive",
            "Pkwy.": "Parkway",
            "Pky": "Parkway",
            "Pkwy": "Parkway",
            "Pl":"Place",
            "Ln":"Lane",
            "Cir":"Circle",
            "CIrcle":"Circle",
            "Blvd.":"Boulevard",
            "Blvd":"Boulevard",
            "Ct":"Court",
            "Ext":"Extension"
            }			
			
# Finding out the file size
statinfo = os.stat('raleigh_north-carolina.osm')
print statinfo.st_size

# Iterative Parsing and fetching the number of tags
def count_tags(filename):
    output = {}
    context = ET.iterparse(filename)
    for event, elem in context:
        #print('Processing {e}'.format(e=ET.tostring(elem)))
        if elem.tag not in output.keys():
            output[elem.tag] = 1
        else:
            output[elem.tag] = output[elem.tag] + 1
    return output


def key_type(element, keys):
    if element.tag == "tag":
        val =  element.attrib['k'] 
        if bool(lower.search(val)):
            keys['lower'] = keys['lower'] + 1
        elif bool(lower_colon.search(val)):    
            keys['lower_colon'] = keys['lower_colon'] + 1
        elif bool(problemchars.search(val)):    
            keys['problemchars'] = keys['problemchars'] + 1
        else :
            keys['other'] = keys['other'] + 1
    return keys

	
def process_map_users(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
		keys = key_type(element, keys)
		if 'user' in element.attrib.keys():
			users.add(element.attrib['user'])

    return keys, users

# Auditing street names	
def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

# Checking if the tag is a street name
def is_street_name(elem):
    return (bool(re.search('[Ss]treet',elem.attrib['k'])))

# Audit the input file
def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    #import pdb; pdb.set_trace()
    for event, elem in ET.iterparse(osm_file, events=("start",)):
		if elem.tag == "node" or elem.tag == "way" or elem.tag == "relation":
			for tag in elem.iter("tag"):
				if is_street_name(tag):
					audit_street_type(street_types, tag.attrib['v'])
    return street_types


# Update street names with the expected street names	
def update_name(name, mapping):

    # YOUR CODE HERE
    for i in mapping.keys():
        # Building the regex search query parameter to use
        regex_query = i
        #regex_query = r'\b' + re.escape(i) + r'\b'
        obj = re.search(regex_query,name)
        if obj != None:
            #If a hit is found, exit the loop after making the change
            pos = obj.start()
            pos_end = obj.end()
            name = name[:pos] + mapping[i] + name[pos_end:]
            break
    return name

# Code to shape the element into the require data dictionary format 
def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way" or element.tag == "relation":
        # YOUR CODE HERE
        address = {}
        temp = {}
        pos = [0,0]
        ref = []
        mem_ref = []
        mem_type = []
        mem_role = []
        #node["rel_members"] = {}
        node["rel_members"] = []
        temp_rel_member = {}
        temp_rel_members = []
        for attrib_key, attrib_val in element.attrib.items():            
            if attrib_key in CREATED:
                temp[attrib_key] = attrib_val
            elif attrib_key == "lat":
                pos[0] = float(attrib_val)
            elif attrib_key == "lon":
                pos[1] = float(attrib_val)
            else:
                node[attrib_key] = attrib_val
            tag_element = element.iter("tag")
            if tag_element != []:
                for tag in tag_element:
                    if tag.attrib["k"] != None:
                        #print tag.attrib["k"], tag.attrib["v"] 
                        if (tag.attrib["k"].startswith("addr:")) and (bool(problemchars_addr.search(tag.attrib["v"])) == False):
                            if (re.search(":",tag.attrib["k"][5:])) == None:
                                # If the attribute is addr:street
                                if tag.attrib["k"][5:] == "street":
                                    # The street attribute is updated -- Updation should occur for those street names which do not conform to expected values
                                    update_street_flag = ""
                                    for street_exp in expected:
                                        if bool(re.search(street_exp, tag.attrib["v"])) == False:
                                            update_street_flag = "X"
                                    if update_street_flag == "X":
                                        address["street"] = update_name(tag.attrib["v"],mapping)
                                    else :
                                        address["street"] = tag.attrib["v"]
                                else:
                                    address[tag.attrib["k"][5:]] = tag.attrib["v"]
                        # If the tag contains street, then the value needs to be updated accordingly
                        elif is_street_name(tag):
                            # Updation should occur for those street names which do not conform to expected values
                            update_street_flag = ""
                            for street_exp in expected:
                                if bool(re.search(street_exp, tag.attrib["v"])) == False:
                                    update_street_flag = "X"
                            if update_street_flag == "X":
                                node[tag.attrib["k"]] = update_name(tag.attrib["v"],mapping)
                            else :
                                node[tag.attrib["k"]] = tag.attrib["v"]
                        elif bool(problemchars_addr.search(tag.attrib["v"])) == False :
                            node[tag.attrib["k"]] = tag.attrib["v"]                                  
            if element.tag == "way":
                nd_element = element.iter("nd")                
                if ref == []:
                    for i in nd_element:
                        ref.append(i.attrib["ref"])
            if element.tag == "relation":
                mem_element = element.iter("member")
                #mem_element = element.findall("member")
                for i in mem_element:                    
                    #temp_rel_member["ref"] = i.attrib["ref"]
                    #temp_rel_member["type"] = i.attrib["type"]
                    #temp_rel_member["role"] = i.attrib["role"]
                    #temp_rel_members.append(temp_rel_member)
                    mem_ref.append(i.attrib["ref"])
                    mem_type.append(i.attrib["type"])
                    mem_role.append(i.attrib["role"])
                
        if ref != []:
            node["node_refs"] = list(Set(ref))
        if mem_ref != []:
            for i in range(len(mem_ref)):
                temp_rel_member = {}
                temp_rel_member["ref"] = mem_ref[i]
                temp_rel_member["type"] = mem_type[i]
                temp_rel_member["role"] = mem_role[i]
                temp_rel_members.append(temp_rel_member)  
        #if mem_type != []:
        #    node["rel_members"]["mem_type"] = mem_type
        #if mem_role != []:
        #    node["rel_members"]["mem_role"] = mem_role
        if temp_rel_members != []:
            node["rel_members"] = {v['ref']: v for v in temp_rel_members}.values()
        if address != {}:
            node["address"] = address
        node["created"] = temp
        node["pos"] = pos
        node["type"] = element.tag
        return node
    else:
        return None

# This code is used to write the JSON file which will be loaded into MongoDB
def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    print data[-1]
    return data
	
def test():
	#Checking the count of tags in the file
    #tags = count_tags('raleigh_north-carolina.osm')
    #pprint.pprint(tags)
	
	# You can use another testfile 'map.osm' to look at your solution
    # Note that the assertions will be incorrect then.
    #keys = process_map_users('raleigh_north-carolina.osm')
    #pprint.pprint(keys)
	
    #The input file is audited here    
    st_types = audit('raleigh_north-carolina.osm')
    #st_types = audit('test.osm')
    
    #The processing of the input file takes place and the final JSON file is created
    data = process_map('raleigh_north-carolina.osm', False)
    #data = process_map('test.osm', True)
    #st_types = audit('test.osm')
    #pprint.pprint(dict(st_types))
    
    #for st_type, ways in st_types.iteritems():
    #    for name in ways:
    #        better_name = update_name(name, mapping)
    #        print name, "=>", better_name
    
    

if __name__ == "__main__":
    test()