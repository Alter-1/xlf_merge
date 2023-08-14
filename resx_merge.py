#!/usr/bin/python3
import os
import sys
#import xml.etree.ElementTree as ET
from lxml import etree
import html
import re

bVerbose = False
bKeepFirst = True

def xml_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
#        .replace('"', "&quot;")
#end xml_escape()


def expand_self_closing_tags(tag_string):
    if tag_string.endswith("/>"):
        # Remove the trailing "/>" and split the remaining string into the tag name and attributes
        tag_content = tag_string[:-2].strip("<").split(" ", 1)
        tag_name = tag_content[0]
        attributes = tag_content[1] if len(tag_content) > 1 else ""
        
        # Construct the expanded tag with separate opening and closing tags
        return f'<{tag_name} {attributes}></{tag_name}>'
    else:
        # If the tag is not self-closing, return it unchanged
        return tag_string
#end expand_self_closing_tags()

op_tag_pattern = re.compile(r'<[^/>]*?>')

def extract_opening_tag(xml_string):
    # Regular expression pattern to match an opening tag
    
    # Search for the first match in the input string
    match = op_tag_pattern.search(xml_string)
    
    # If a match is found, return the matching string; otherwise, return None
    return match.group(0) if match else None
#end extract_opening_tag()

class RESXParser:
    def __init__(self, filename, keep_first=True):
        global bVerbose
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            #self.root = ET.fromstring(content)
            
            # Extract raw header and tail
            #start_index = content.index('<data')
            start_index = content.rindex('</resheader>') + len('</resheader>')
            start_index = content.index('<data', start_index)
            end_index = content.rindex('</data>') + len('</data>')
            self.raw_header = content[:start_index].strip()
            self.raw_tail = content[end_index:].strip()

            # Extract only the trans-unit elements for parsing
            data_units_content = content[start_index:end_index]
            #root = ET.fromstring("<root>" + data_units_content + "</root>")  # Wrap in a root for parsing
            root = etree.fromstring("<root>" + data_units_content + "</root>")  # Wrap in a root for parsing
             
            self.data_unit_ids = []
            self.raw_id_str = {}
            self.name_to_value = {}
            self.dup_count = 0
            self.new_count = 0

            #for data_unit in root.findall(".//trans-unit"):
            for data_unit in root.findall("data"):
                                
                raw_id_str_open = extract_opening_tag(etree.tostring(data_unit, encoding="unicode").strip())
                value_element = data_unit.find("value")
                id_str = data_unit.attrib['name']
                #print(id_str)

                # Handle duplicates based on keep_first flag
                #if id in self.name_to_value:
                if id_str in self.name_to_value:
                    self.dup_count += 1

                    if(bVerbose):
                        print("Dup: "+data_unit.attrib['name'])

                    if keep_first:
                        continue

                if value_element is not None:
                    self.data_unit_ids.append(id_str)
                    self.raw_id_str[id_str] = raw_id_str_open
                    #self.name_to_value[id_str] = value_element.text
                    self.name_to_value[id_str] = etree.tostring(value_element, encoding="unicode")
                #end if()
            #end for()

    #end __init__()

    def merge(self, other, keep_first=True):

        # Go through items of the second object
        for idx, id_str in enumerate(other.name_to_value):

            raw_id_str_open = other.raw_id_str[id_str] #extract_opening_tag(etree.tostring(data_unit, encoding="unicode").strip())
            value = other.name_to_value[id_str]
            
            # If the name is not in the first object, insert after the same preceding item
            #if source not in self.name_to_value:
            if id_str not in self.name_to_value:
                self.new_count += 1
                if idx == 0:
                    # If it's the first item, prepend to the list
                    self.data_unit_ids.insert(0, id_str)
                else:
                    # Find the preceding item from the other object in the first object
                    prev_id = other.data_unit_ids[idx - 1]
                    if prev_id in self.data_unit_ids:
                        insert_pos = self.data_unit_ids.index(prev_id) + 1
                        self.data_unit_ids.insert(insert_pos, id_str)
                    else:
                        # If the preceding source isn't found (unlikely), append to the end
                        self.data_unit_ids.append(id_str)

                self.raw_id_str[id_str] = raw_id_str_open
                self.name_to_value[id_str] = value
            else:
                # If the source exists in the first object, compare states and update if needed
                
                if(not keep_first):
                    self.name_to_value[id_str] = value
                    self.raw_id_str[id_str] = raw_id_str_open
            #end if(source not in self.name_to_value)

        #end for()
    #end merge()

    def save_to_resx(self, filename):
        with open(filename, 'w', encoding='utf-8') as file:
            # Write raw header
            file.write(self.raw_header + "\n")
            
            # Write each trans-unit in the current order
            for id_str in self.data_unit_ids:

                raw_id_str = self.raw_id_str[id_str]
                value = self.name_to_value[id_str]

                # Format and write trans-unit item
                #data_unit_content  = f'        <trans-unit id="{id_str}" translate="yes" xml:space="preserve">\n'
                data_unit_content =  f'        '+raw_id_str+'\n'
                data_unit_content += '          '+expand_self_closing_tags(value.strip())+'\n'
                data_unit_content += '        </data>\n'

                file.write(data_unit_content)
            
            # Write raw tail
            file.write(self.raw_tail)

    #end save_to_resx()

#end class RESXParser

def print_help():
    print("  https://alter.org.ua/soft/other/xlf_merge")
    print("Usage:")
    print("  python resx_merge.py [<options>] -i <resx1> -i <resx2> [ -i <resx3> ....] -o <resx_merged>")
    print("  python resx_merge.py [<options>] -i <dir11> -i <dir2> -o <dir_merged>")
    print("Options:")
    print("  -v    verbose")
    print("  -f    force using last variant when merging records with same key/state")
    print("  -h    display help screen")
#end print_help()

def merge_files(input_files, output_file, keep_first=True):

    merged_file = None
    input_file = None

    for fn in input_files:

        if(merged_file == None):
            try:
                merged_file = RESXParser(fn, keep_first)
                print(fn+": dups: "+str(merged_file.dup_count))
            except Exception as e:
                print('Merge error:', str(e))
        else:
            try:
                input_file = RESXParser(fn, keep_first)
                print(fn+": dups: "+str(input_file.dup_count))
                merged_file.merge(input_file, keep_first)
                print("  new: "+str(merged_file.new_count))
            except Exception as e:
                print('Merge error:', str(e))
        #end if()

    #end for()

    if(output_file != None and merged_file != None):
        try:
            merged_file.save_to_resx(output_file)
            return True
        except Exception as e:
            print('Save error:', str(e))

    else:
        print_help()

    return False
#end merge_files()

def main(args = sys.argv[1:]):
    global bKeepFirst
    global bVerbose

    input_files = []
    output_file = None

    print("RESX merge tool v0.2 (c) 2023 by Alexandr A. Telyatnikov aka Alter")
    
    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '-i' and i + 1 < len(args):
            input_files.append(args[i+1])
            i += 2
        elif args[i] == '-o' and i + 1 < len(args):
            output_file = args[i+1]
            i += 2
        elif args[i] == '-v':
            bVerbose = True;
            i += 1
        elif args[i] == '-f':
            bKeepFirst = False;
            i += 1
        else:
            print_help()
            return
    #end while()

    if(output_file is None):
        print_help()
        return

    if(len(input_files) == 2 and
       os.path.isdir(input_files[0]) and
       os.path.isdir(input_files[1]) and
       (not os.path.exists(output_file) or os.path.isdir(output_file)) ):

        src_dir1 = input_files[0]
        src_dir2 = input_files[1]
        dst_dir  = output_file
        if(not os.path.exists(dst_dir)):
            os.mkdir(dst_dir)

        files = os.listdir(src_dir1)
        for fn in files:
            if(not fn.endswith(".resx")):
                continue
            merge_files([os.path.join(src_dir1, fn), os.path.join(src_dir2, fn)], 
                         os.path.join(dst_dir, fn),
                         bKeepFirst )
        #end for()
    else:
        merge_files(input_files, output_file, bKeepFirst)

if __name__ == "__main__":
    main()
