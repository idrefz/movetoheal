import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

def create_advanced_kml_from_data(data_text):
    lines = data_text.strip().split('\n')
    
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Document name
    name = ET.SubElement(document, 'name')
    name.text = lines[0].strip()
    
    # Process data
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for item lines starting with R04-
        if line.startswith('R04-'):
            item_name = line
            item_id = None
            item_spec = None
            
            # Get id and spec_id if available
            if i + 1 < len(lines) and 'id :' in lines[i + 1]:
                item_id = lines[i + 1].strip()
                i += 1
            if i + 1 < len(lines) and 'spec_id :' in lines[i + 1]:
                item_spec = lines[i + 1].strip()
                i += 1
            
            # Create placemark
            placemark = ET.SubElement(document, 'Placemark')
            
            # Name
            name_elem = ET.SubElement(placemark, 'name')
            name_elem.text = item_name
            
            # Description
            description = ET.SubElement(placemark, 'description')
            desc_text = f"Name: {item_name}"
            if item_id:
                desc_text += f"\n{item_id}"
            if item_spec:
                desc_text += f"\n{item_spec}"
            description.text = desc_text
            
            # Style with appropriate icon
            style = ET.SubElement(placemark, 'Style')
            icon_style = ET.SubElement(style, 'IconStyle')
            icon = ET.SubElement(icon_style, 'Icon')
            
            # Apply icon rules
            icon_url = "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"  # default
            
            if 'JC01' in item_name:
                icon_url = "http://maps.google.com/mapfiles/kml/shapes/forbidden.png"
            elif 'OP01' in item_name:
                icon_url = "http://maps.google.com/mapfiles/kml/paddle/ltblu-stars.png"
            elif item_spec and 'OTB-4x1-Big-Bay' in item_spec:
                icon_url = "http://maps.google.com/mapfiles/kml/shapes/picnic.png"
            
            href = ET.SubElement(icon, 'href')
            href.text = icon_url
            
            # Point with coordinates (you need to replace these with actual coordinates)
            point = ET.SubElement(placemark, 'Point')
            coordinates = ET.SubElement(point, 'coordinates')
            
            # Generate some variation in coordinates based on item name
            base_lon = 106.150271
            base_lat = -6.125063
            
            # Simple hash for coordinate variation
            name_hash = sum(ord(c) for c in item_name)
            lon_variation = (name_hash % 100) * 0.001
            lat_variation = ((name_hash // 100) % 100) * 0.001
            
            coordinates.text = f"{base_lon + lon_variation},{base_lat + lat_variation},0"
        
        i += 1
    
    # Format and return
    rough_string = ET.tostring(kml, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

# Usage
data = """SERANG  
MTELEXPWT-CLG-XL-010  
M1DF-R04-CLGO-R015-S13  
R04-CLGO-R015-S13-000-KU01  
id : 938433367  
spec_id : AC-OF-SM-ADSS-24D  
R04-CLGO-R015-S13-030-KU01  
id : 938433350  
spec_id : AC-OF-SM-ADSS-24D  
R04-CLGO-R015-S13-020-KU01  
id : 938433281  
spec_id : AC-OF-SM-ADSS-24D  
R04-CLGO-R015-S13-010-KU01  
id : 938432574  
spec_id : AC-OF-SM-ADSS-24D  
R04-CLGO-R015-S13-010-JC01  
id : 938433295  
spec_id : SC-OF-SM-24  
R04-CLGO-R015-S13-020-JC01  
id : 938433364  
spec_id : SC-OF-SM-24  
R04-CLGO-R015-S13-030-OP01  
id : 938433381  
spec_id : ODP Solid-PB-16 AS  
Anyar  
id : 938433385  
spec_id : OTB-4x1-Big-Bay"""

kml_result = create_advanced_kml_from_data(data)

# Save to file
with open('automatic_output.kml', 'w', encoding='utf-8') as f:
    f.write(kml_result)

print("KML file created: automatic_output.kml")
