"""
[Archimate editor](https://www.archimatetool.com/) doesn't have ability to export image from internal Archi format to SVG and enrich it with documentation information.
It is super useful when all your links that you saved for some elements in "Documentation" field will be "copyied" to SVG as links
Input Arguments:
{path to original Archimate file} { path to exported SVG file } {path to output SVG, that will be enriched with links}

if you want to automate process of exporting from Archi to SVG ( not working in headless mode ) - pay your attention to 
https://github.com/cherkavi/docker-images/blob/master/automation4app/Archi-svg-export.md
"""
from xml.dom.minidom import parse, parseString
import sys

def componentSelector(element):
    return element.getAttribute("xsi:type").startswith("archimate:") and element.hasChildNodes()


def componentWithDocumentSelector(element):
    # filter element by classtype, java "instance of" with shortName
    return element.__class__.__name__=="Element" and element.tagName=="documentation"


def descriptionTextPostProcessing(lines):   
    splitted_lines=map(lambda x:x.split("\n"), lines)
    flatted_lines = [each_element for each_line in splitted_lines for each_element in each_line]
    trim_lines=map(lambda x:x.strip(), flatted_lines)
    lines_with_links=list(filter(lambda x:x.startswith("http"), trim_lines))
    return lines_with_links[0] if len(lines_with_links)>0 else None


def archi_elements(path_to_source_file):
    """ find all elements inside 'archimate' that contain a description 
    return dictionary: text -> url
    """
    dom = parse(path_to_source_file)  # parse an XML file by name
    components = [each_element for each_element in dom.getElementsByTagName("element") if componentSelector(each_element)]
    components_description = map( lambda x:(x.getAttribute("name"),  descriptionTextPostProcessing([each_child.firstChild.nodeValue for each_child in x.childNodes if componentWithDocumentSelector(each_child)]) ),components)
    non_empty_description = filter(lambda x:x[1], components_description)
    return dict( (n,d) for n,d in non_empty_description )


def svgComponentSelector(element):
    return element.hasAttribute("clip-path")    


def save_xml_to_file(root_node, output_file_path):
    """ save minidom to file """
    with open(output_file_path, "w") as file:
        root_node.writexml(file)


def wrap_node_with_anchor(dom, url, xml_elements):
    """ replace current element with anchor and put current element inside it """
    for each_node in xml_elements:
        parent = each_node.parentNode
        parent.removeChild(each_node)
        anchor = dom.createElement("a")
        anchor.setAttribute("xlink:href", url)
        anchor.appendChild(each_node)
        parent.appendChild(anchor)


def update_svg_elements(source_file, archimate_description, destination_file):
    """find all elements inside SVG file  """
    dom = parse(source_file) 
    # list of elements: xml_node, text, @clip-path
    svg_elements = [(each_element, each_element.firstChild.nodeValue, each_element.getAttribute("clip-path") ) for each_element in dom.getElementsByTagName("text") if svgComponentSelector(each_element)]
    # generate dict: @clip_path -> [(text, xml_node) (text, xml_node)]
    groupped_by_clip=dict()
    for xml_element, text, clip_path in svg_elements:        
        if clip_path in groupped_by_clip :
            groupped_by_clip[clip_path].append( (text, xml_element) )
        else:
            groupped_by_clip[clip_path] = [(text, xml_element)  ]
    # generate dictionary: title -> xml nodes
    name_xmlnodes=dict()
    for _,value in groupped_by_clip.items():
        text = " ".join([each_element[0] for each_element in value])
        xml_elements=[each_element[1] for each_element in value]
        if text in name_xmlnodes:
            name_xmlnodes[text].extend(xml_elements)
        else:
            name_xmlnodes[text]=xml_elements
    # walk through all objects and wrap with <a>
    for (name,url) in archimate_description.items():
        if name in name_xmlnodes:
            wrap_node_with_anchor(dom, url, name_xmlnodes[name])

    save_xml_to_file(dom, destination_file)



if __name__=="__main__":
    path_to_archimate=sys.argv[0]
    path_to_svg_source=sys.argv[1]
    path_to_svg_destination=sys.argv[2]

    archimate_description = archi_elements(path_to_archimate)
    update_svg_elements(path_to_svg_source, archimate_description, path_to_svg_destination)
