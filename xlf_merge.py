#!/usr/bin/python3
import os
import sys
#import xml.etree.ElementTree as ET
from lxml import etree
import html
import re

bVerbose = False
bKeepFirst = True

# Define a ranking for the state values
state_ranking = {
    'translated': 5,
    'needs-review-translation': 4,
    'new': 3,
    'needs-translation': 2,
    'needs-adaptation': 1
}

def xml_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
#        .replace('"', "&quot;")
#end xml_escape()

'''
def expand_self_closing_tags(xml_string):
    # Regular expression to match self-closing tags
    pattern = re.compile(r'<(\w+)([^>]*)\/>')
    
    # Replacement function that constructs an opening and closing tag
    def replacement(match):
        tag_name = match.group(1)
        attributes = match.group(2)
        return f'<{tag_name}{attributes}></{tag_name}>'
    
    # Use re.sub to replace all self-closing tags with expanded tags
    return pattern.sub(replacement, xml_string)
'''

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

class XLFParser:
    def __init__(self, filename, keep_first=True):
        global bVerbose
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            #self.root = ET.fromstring(content)
            
            # Extract raw header and tail
            start_index = content.index('<trans-unit')
            end_index = content.rindex('</trans-unit>') + len('</trans-unit>')
            self.raw_header = content[:start_index].strip()
            self.raw_tail = content[end_index:].strip()

            # Extract only the trans-unit elements for parsing
            trans_units_content = content[start_index:end_index]
            #root = ET.fromstring("<root>" + trans_units_content + "</root>")  # Wrap in a root for parsing
            root = etree.fromstring("<root>" + trans_units_content + "</root>")  # Wrap in a root for parsing
             
            self.trans_unit_ids = []
            self.id_to_source = {}
            self.raw_id_str = {}
            self.source_to_target = {}
            self.source_to_state = {}
            self.source_to_note = {}
            self.dup_count = 0
            self.new_count = 0

            #for trans_unit in root.findall(".//trans-unit"):
            for trans_unit in root.findall("trans-unit"):
                                
                source = trans_unit.find("source").text
                raw_id_str_open = extract_opening_tag(etree.tostring(trans_unit, encoding="unicode").strip())
                target_element = trans_unit.find("target")
                note_element = trans_unit.find("note")
                id_str = trans_unit.attrib['id']
                #print(trans_unit.attrib['id'])
                #print(source)

                # Handle duplicates based on keep_first flag and state ranking
                #if source in self.source_to_target:
                if id_str in self.id_to_source:
                    self.dup_count += 1

                    if(bVerbose):
                        print("Dup: "+trans_unit.attrib['id'])
                        print("  -> "+source)

                    if keep_first:
                        continue
                    
                    existing_state_rank = state_ranking.get(self.source_to_state.get(source, ''), 0)
                    new_state_rank = state_ranking.get(state_attrib, 0)
                            
                    # If the new state is not better than the existing one, skip updating
                    if new_state_rank <= existing_state_rank:
                        continue

                if target_element is not None:
                    self.trans_unit_ids.append(id_str)
                    self.id_to_source[id_str] = source
                    self.raw_id_str[id_str] = raw_id_str_open
                    #self.source_to_target[source] = target_element.text
                    self.source_to_target[source] = etree.tostring(target_element, encoding="unicode")
                    if(note_element is not None):
                        #self.source_to_note[source] = note_element.text
                        # Store raw note content
                        self.source_to_note[source] = etree.tostring(note_element, encoding='unicode')

                    state_attrib = target_element.attrib.get('state', None)                    
                    if state_attrib:
                        self.source_to_state[source] = state_attrib
                #end if(source in self.source_to_target)
            #end for()

    #end __init__()

    def merge(self, other, keep_first=True):

        # Go through items of the second object
        for idx, id_str in enumerate(other.id_to_source):

            source = other.id_to_source[id_str]
            raw_id_str_open = other.raw_id_str[id_str] #extract_opening_tag(etree.tostring(trans_unit, encoding="unicode").strip())
            target = other.source_to_target[source]
            state = other.source_to_state.get(source, None)
            note = other.source_to_note.get(source, None)
            
            # If the source is not in the first object, insert after the same preceding item
            #if source not in self.source_to_target:
            if id_str not in self.id_to_source:
                self.new_count += 1
                if idx == 0:
                    # If it's the first item, prepend to the list
                    self.trans_unit_ids.insert(0, id_str)
                else:
                    # Find the preceding item from the other object in the first object
                    prev_id = other.trans_unit_ids[idx - 1]
                    if prev_id in self.trans_unit_ids:
                        insert_pos = self.trans_unit_ids.index(prev_id) + 1
                        self.trans_unit_ids.insert(insert_pos, id_str)
                    else:
                        # If the preceding source isn't found (unlikely), append to the end
                        self.trans_unit_ids.append(id_str)

                self.id_to_source[id_str] = source
                self.raw_id_str[id_str] = raw_id_str_open
                self.source_to_target[source] = target
                if state:
                    self.source_to_state[source] = state
                if note is not None:
                    self.source_to_note[source] = note
            else:
                # If the source exists in the first object, compare states and update if needed
                existing_state_rank = state_ranking.get(self.source_to_state.get(source, ''), 0)
                new_state_rank = state_ranking.get(state, 0)
                
                if((new_state_rank > existing_state_rank) or 
                   ((new_state_rank == existing_state_rank) and not keep_first) ):
                    self.source_to_target[source] = target
                    self.raw_id_str[id_str] = raw_id_str_open
                    if state:
                        self.source_to_state[source] = state
                    if note is not None:
                        self.source_to_note[source] = note
                    else:
                        self.source_to_note[source] = None
            #end if(source not in self.source_to_target)

        #end for()
    #end merge()

    def save_merged(self, filename):
        with open(filename, 'w', encoding='utf-8') as file:
            # Write raw header
            file.write(self.raw_header + "\n")
            
            # Write each trans-unit in the current order
            for id_str in self.trans_unit_ids:

                source = self.id_to_source[id_str]
                raw_id_str = self.raw_id_str[id_str]
                target = self.source_to_target[source]
                state = self.source_to_state.get(source, '')
                note  = self.source_to_note.get(source, None)
                source = xml_escape(source)

                # Format and write trans-unit item
                #trans_unit_content  = f'        <trans-unit id="{id_str}" translate="yes" xml:space="preserve">\n'
                trans_unit_content =  f'        '+raw_id_str+'\n'
                trans_unit_content += f'          <source>{source}</source>\n'
                #if target is None:
                #    target = ''
                #else:
                #    target = xml_escape(target)

                #if not (state is None):
                #    trans_unit_content += f'          <target state="{state}">{target}</target>\n'
                #else:
                #    trans_unit_content += f'          <target>{target}</target>\n'
                trans_unit_content += '          '+expand_self_closing_tags(target.strip())+'\n'

                if not (note is None):
                    #note = xml_escape(note)
                    #trans_unit_content += f'          <note from="MultilingualUpdate" annotates="source" priority="2">{note}</note>\n'
                    trans_unit_content += '          '+note.strip()+'\n'
                trans_unit_content += '        </trans-unit>\n'
                
                file.write(trans_unit_content)
            
            # Write raw tail
            file.write(self.raw_tail)

    #end save_merged()

#end class XLFParser

def print_help():
    print("  https://alter.org.ua/soft/other/xlf_merge")
    print("Usage:")
    print("  python xlf_merge.py [<options>] -i <xlf1> -i <xlf2> [ -i <xlf3> ....] -o <xlf_merged>")
    print("  python xlf_merge.py [<options>] -i <dir11> -i <dir2> -o <dir_merged>")
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
                merged_file = XLFParser(fn, keep_first)
                print(fn+": dups: "+str(merged_file.dup_count))
            except Exception as e:
                print('Merge error:', str(e))
        else:
            try:
                input_file = XLFParser(fn, keep_first)
                print(fn+": dups: "+str(input_file.dup_count))
                merged_file.merge(input_file, keep_first)
                print("  new: "+str(merged_file.new_count))
            except Exception as e:
                print('Merge error:', str(e))
        #end if()

    #end for()

    if(output_file != None and merged_file != None):
        try:
            merged_file.save_merged(output_file)
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

    print("XLF merge tool v0.2 (c) 2023 by Alexandr A. Telyatnikov aka Alter")
    
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
            if(not fn.endswith(".xlf")):
                continue
            merge_files([os.path.join(src_dir1, fn), os.path.join(src_dir2, fn)], 
                         os.path.join(dst_dir, fn),
                         bKeepFirst )
        #end for()
    else:
        merge_files(input_files, output_file, bKeepFirst)

if __name__ == "__main__":
    main()
