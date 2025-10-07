# app.py
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import pandas as pd
from io import StringIO, BytesIO
import base64

def parse_kml_file(uploaded_file):
    """Parse KML file dan ekstrak informasi"""
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        root = ET.fromstring(content)
    except:
        st.error("Error parsing KML file")
        return []
    
    placemarks = []
    
    # Cari semua Placemark dalam file KML
    for placemark in root.iter('{http://www.opengis.net/kml/2.2}Placemark'):
        placemark_data = {}
        
        # Extract name
        name_elem = placemark.find('{http://www.opengis.net/kml/2.2}name')
        placemark_data['name'] = name_elem.text if name_elem is not None else 'N/A'
        
        # Extract description
        desc_elem = placemark.find('{http://www.opengis.net/kml/2.2}description')
        placemark_data['description'] = desc_elem.text if desc_elem is not None else ''
        
        # Extract coordinates
        coords_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}coordinates')
        placemark_data['coordinates'] = coords_elem.text if coords_elem is not None else 'N/A'
        
        # Extract icon URL
        icon_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}href')
        placemark_data['icon_url'] = icon_elem.text if icon_elem is not None else 'N/A'
        
        # Identifikasi tipe berdasarkan aturan
        placemark_data['type'] = identify_type(placemark_data['name'], placemark_data['description'])
        
        placemarks.append(placemark_data)
    
    return placemarks

def identify_type(name, description):
    """Identifikasi tipe berdasarkan nama dan deskripsi"""
    name_str = str(name).upper()
    desc_str = str(description).upper()
    
    if 'JC01' in name_str:
        return 'JC01 (Forbidden)'
    elif 'OP01' in name_str:
        return 'OP01 (Blue Stars)'
    elif 'OTB-4X1-BIG-BAY' in desc_str:
        return 'OTB-4x1-Big-Bay (Picnic)'
    elif 'KU01' in name_str:
        return 'KU01 (Default)'
    else:
        return 'Unknown'

def get_icon_for_type(type_name):
    """Dapatkan URL icon berdasarkan tipe"""
    icon_map = {
        'JC01 (Forbidden)': 'http://maps.google.com/mapfiles/kml/shapes/forbidden.png',
        'OP01 (Blue Stars)': 'http://maps.google.com/mapfiles/kml/paddle/ltblu-stars.png',
        'OTB-4x1-Big-Bay (Picnic)': 'http://maps.google.com/mapfiles/kml/shapes/picnic.png',
        'KU01 (Default)': 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png',
        'Unknown': 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png'
    }
    return icon_map.get(type_name, 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png')

def create_enhanced_kml(placemarks):
    """Buat KML baru dengan identifikasi yang benar"""
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Buat folder untuk setiap tipe
    folders = {}
    type_colors = {
        'JC01 (Forbidden)': 'ff0000ff',  # Red
        'OP01 (Blue Stars)': 'ffff0000',  # Blue  
        'OTB-4x1-Big-Bay (Picnic)': 'ff00ff00',  # Green
        'KU01 (Default)': 'ff00aaff',  # Orange
        'Unknown': 'ff888888'  # Gray
    }
    
    for placemark_data in placemarks:
        type_name = placemark_data['type']
        
        if type_name not in folders:
            folder = ET.SubElement(document, 'Folder')
            name_elem = ET.SubElement(folder, 'name')
            name_elem.text = type_name
            folders[type_name] = folder
    
    # Tambahkan placemark ke folder masing-masing
    for placemark_data in placemarks:
        folder = folders[placemark_data['type']]
        placemark = ET.SubElement(folder, 'Placemark')
        
        # Name
        name_elem = ET.SubElement(placemark, 'name')
        name_elem.text = placemark_data['name']
        
        # Description dengan info lengkap
        desc_elem = ET.SubElement(placemark, 'description')
        desc_text = f"""
        <![CDATA[
        <h3>Informasi Titik</h3>
        <b>Nama:</b> {placemark_data['name']}<br/>
        <b>Tipe Teridentifikasi:</b> {placemark_data['type']}<br/>
        <b>Koordinat:</b> {placemark_data['coordinates']}<br/>
        <b>Deskripsi Asli:</b> {placemark_data['description']}<br/>
        <b>Icon:</b> {placemark_data['icon_url']}<br/>
        ]]>
        """
        desc_elem.text = desc_text
        
        # Style dengan icon yang benar
        style = ET.SubElement(placemark, 'Style')
        icon_style = ET.SubElement(style, 'IconStyle')
        icon = ET.SubElement(icon_style, 'Icon')
        href = ET.SubElement(icon, 'href')
        href.text = get_icon_for_type(placemark_data['type'])
        
        # Point coordinates
        point = ET.SubElement(placemark, 'Point')
        coordinates = ET.SubElement(point, 'coordinates')
        coordinates.text = placemark_data['coordinates']
    
    # Convert to string
    rough_string = ET.tostring(kml, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    st.set_page_config(
        page_title="KML Identifier",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ KML Auto Identifier")
    st.markdown("Upload file KML untuk mengidentifikasi tipe titik secara otomatis")
    
    # Upload file
    uploaded_file = st.file_uploader("Pilih file KML", type=['kml'])
    
    if uploaded_file is not None:
        # Parse KML
        with st.spinner("Mengidentifikasi titik-titik..."):
            placemarks = parse_kml_file(uploaded_file)
        
        if placemarks:
            st.success(f"✅ Berhasil mengidentifikasi {len(placemarks)} titik!")
            
            # Tampilkan summary
            col1, col2, col3, col4 = st.columns(4)
            
            type_counts = {}
            for pm in placemarks:
                type_name = pm['type']
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            with col1:
                st.metric("Total Titik", len(placemarks))
            with col2:
                st.metric("JC01", type_counts.get('JC01 (Forbidden)', 0))
            with col3:
                st.metric("OP01", type_counts.get('OP01 (Blue Stars)', 0))
            with col4:
                st.metric("OTB", type_counts.get('OTB-4x1-Big-Bay (Picnic)', 0))
            
            # Tampilkan data dalam tabel
            st.subheader("📊 Data Titik Teridentifikasi")
            df_data = []
            for pm in placemarks:
                df_data.append({
                    'Nama': pm['name'],
                    'Tipe': pm['type'],
                    'Koordinat': pm['coordinates'][:50] + '...' if len(pm['coordinates']) > 50 else pm['coordinates'],
                    'Icon': pm['icon_url']
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Download enhanced KML
            st.subheader("📥 Download KML Hasil Identifikasi")
            enhanced_kml = create_enhanced_kml(placemarks)
            
            # Create download link
            b64 = base64.b64encode(enhanced_kml.encode()).decode()
            href = f'<a href="data:application/vnd.google-earth.kml+xml;base64,{b64}" download="identified_points.kml">⬇️ Download KML File</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            # Tampilkan preview KML
            with st.expander("🔍 Preview KML Content"):
                st.code(enhanced_kml[:2000] + "..." if len(enhanced_kml) > 2000 else enhanced_kml, language='xml')
            
            # Statistics
            st.subheader("📈 Statistik Identifikasi")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Distribusi Tipe Titik:**")
                type_df = pd.DataFrame({
                    'Tipe': list(type_counts.keys()),
                    'Jumlah': list(type_counts.values())
                })
                st.bar_chart(type_df.set_index('Tipe'))
            
            with col2:
                st.write("**Detail Tipe:**")
                for type_name, count in type_counts.items():
                    icon_url = get_icon_for_type(type_name)
                    st.write(f"![Icon]({icon_url}) **{type_name}**: {count} titik")
        
        else:
            st.warning("Tidak ada titik yang ditemukan dalam file KML")

    else:
        # Contoh penggunaan
        st.info("""
        **Contoh Format KML yang Didukung:**
        ```xml
        <Placemark>
            <name>R04-CLGO-R015-S13-010-JC01</name>
            <description>spec_id : SC-OF-SM-24</description>
            <Point>
                <coordinates>106.150271,-6.125063,0</coordinates>
            </Point>
        </Placemark>
        ```
        
        **Aturan Identifikasi:**
        - **JC01** → Icon Forbidden 🔴
        - **OP01** → Icon Blue Stars 🔵  
        - **OTB-4x1-Big-Bay** → Icon Picnic 🟢
        - Lainnya → Icon Default ⚪
        """)

if __name__ == "__main__":
    main()
