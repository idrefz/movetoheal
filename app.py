# app.py
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import pandas as pd
from io import StringIO, BytesIO
import base64

def parse_kml_file(uploaded_file):
    """Parse KML file dan ekstrak informasi dengan struktur folder asli"""
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        root = ET.fromstring(content)
    except:
        st.error("Error parsing KML file")
        return [], []
    
    folders_data = []
    all_placemarks = []
    
    # Cari semua Folder dan Placemark dalam file KML
    for folder in root.iter('{http://www.opengis.net/kml/2.2}Folder'):
        folder_data = {
            'name': '',
            'placemarks': []
        }
        
        # Extract folder name
        name_elem = folder.find('{http://www.opengis.net/kml/2.2}name')
        folder_data['name'] = name_elem.text if name_elem is not None else 'Unnamed Folder'
        
        # Extract placemarks dalam folder ini
        for placemark in folder.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
            placemark_data = extract_placemark_data(placemark)
            if placemark_data:
                folder_data['placemarks'].append(placemark_data)
                all_placemarks.append(placemark_data)
        
        folders_data.append(folder_data)
    
    # Juga cari Placemark langsung di root (tanpa folder)
    for placemark in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
        placemark_data = extract_placemark_data(placemark)
        if placemark_data and placemark_data not in all_placemarks:
            all_placemarks.append(placemark_data)
            # Buat folder virtual untuk placemark tanpa folder
            folders_data.append({
                'name': 'Root Placemarks',
                'placemarks': [placemark_data]
            })
    
    return folders_data, all_placemarks

def extract_placemark_data(placemark):
    """Ekstrak data dari placemark termasuk geometry asli"""
    placemark_data = {}
    
    # Extract name
    name_elem = placemark.find('{http://www.opengis.net/kml/2.2}name')
    placemark_data['name'] = name_elem.text if name_elem is not None else 'N/A'
    
    # Extract description
    desc_elem = placemark.find('{http://www.opengis.net/kml/2.2}description')
    placemark_data['description'] = desc_elem.text if desc_elem is not None else ''
    
    # Extract geometry type dan coordinates asli
    line_string_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}LineString')
    point_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}Point')
    
    if line_string_elem is not None:
        placemark_data['geometry_type'] = 'LineString'
        coords_elem = line_string_elem.find('{http://www.opengis.net/kml/2.2}coordinates')
        placemark_data['coordinates'] = coords_elem.text if coords_elem is not None else 'N/A'
        placemark_data['original_geometry'] = 'LineString'
    elif point_elem is not None:
        placemark_data['geometry_type'] = 'Point'
        coords_elem = point_elem.find('{http://www.opengis.net/kml/2.2}coordinates')
        placemark_data['coordinates'] = coords_elem.text if coords_elem is not None else 'N/A'
        placemark_data['original_geometry'] = 'Point'
    else:
        placemark_data['geometry_type'] = 'Unknown'
        placemark_data['coordinates'] = 'N/A'
        placemark_data['original_geometry'] = 'Unknown'
    
    # Extract icon URL
    icon_elem = placemark.find('.//{http://www.opengis.net/kml/2.2}href')
    placemark_data['icon_url'] = icon_elem.text if icon_elem is not None else 'N/A'
    
    # Identifikasi tipe berdasarkan aturan
    placemark_data['type'] = identify_type(placemark_data['name'], placemark_data['description'])
    
    return placemark_data

def identify_type(name, description):
    """Identifikasi tipe berdasarkan nama dan deskripsi"""
    name_str = str(name).upper()
    desc_str = str(description).upper()
    
    if 'JC01' in name_str:
        return 'JC01'
    elif 'OP01' in name_str:
        return 'OP01'
    elif 'OTB-4X1-BIG-BAY' in desc_str:
        return 'OTB-4x1-Big-Bay'
    elif '-KU' in name_str:
        return 'KU-Line'
    else:
        return 'Unknown'

def get_style_for_type(type_name, geometry_type):
    """Dapatkan style berdasarkan tipe dan geometri"""
    if type_name == 'KU-Line':
        return {
            'line_color': 'ff00ff00',  # Hijau
            'line_width': 3,
            'icon_url': None
        }
    elif type_name == 'JC01':
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/shapes/forbidden.png',
            'line_color': None,
            'line_width': None
        }
    elif type_name == 'OP01':
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/paddle/ltblu-stars.png',
            'line_color': None,
            'line_width': None
        }
    elif type_name == 'OTB-4x1-Big-Bay':
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/shapes/picnic.png',
            'line_color': None,
            'line_width': None
        }
    else:
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png',
            'line_color': None,
            'line_width': None
        }

def create_enhanced_kml(folders_data):
    """Buat KML baru dengan struktur folder asli dan style yang diperbarui"""
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Pertahankan struktur folder asli
    for folder_data in folders_data:
        folder_elem = ET.SubElement(document, 'Folder')
        
        # Nama folder
        name_elem = ET.SubElement(folder_elem, 'name')
        name_elem.text = folder_data['name']
        
        # Tambahkan placemarks ke folder
        for placemark_data in folder_data['placemarks']:
            placemark_elem = ET.SubElement(folder_elem, 'Placemark')
            
            # Name
            name_elem = ET.SubElement(placemark_elem, 'name')
            name_elem.text = placemark_data['name']
            
            # Description dengan info lengkap
            desc_elem = ET.SubElement(placemark_elem, 'description')
            desc_text = f"""
            <![CDATA[
            <h3>Informasi Titik</h3>
            <b>Nama:</b> {placemark_data['name']}<br/>
            <b>Tipe Teridentifikasi:</b> {placemark_data['type']}<br/>
            <b>Geometri Asli:</b> {placemark_data['original_geometry']}<br/>
            <b>Geometri Baru:</b> {placemark_data['geometry_type']}<br/>
            <b>Koordinat:</b> {placemark_data['coordinates'][:100]}...<br/>
            <b>Deskripsi Asli:</b> {placemark_data['description']}<br/>
            ]]>
            """
            desc_elem.text = desc_text
            
            # Style berdasarkan tipe
            style = ET.SubElement(placemark_elem, 'Style')
            style_config = get_style_for_type(placemark_data['type'], placemark_data['geometry_type'])
            
            if placemark_data['type'] == 'KU-Line':
                # Style untuk LineString KU - HIJAU width 3
                line_style = ET.SubElement(style, 'LineStyle')
                color_elem = ET.SubElement(line_style, 'color')
                color_elem.text = style_config['line_color']  # Hijau
                width_elem = ET.SubElement(line_style, 'width')
                width_elem.text = str(style_config['line_width'])  # Width 3
                
                # Nonaktifkan icon untuk LineString
                icon_style = ET.SubElement(style, 'IconStyle')
                scale = ET.SubElement(icon_style, 'scale')
                scale.text = '0'  # Sembunyikan icon
            else:
                # Style untuk Point
                icon_style = ET.SubElement(style, 'IconStyle')
                icon = ET.SubElement(icon_style, 'Icon')
                href = ET.SubElement(icon, 'href')
                href.text = style_config['icon_url']
            
            # Geometry - GUNAKAN LINE STRING ASLI untuk KU
            if placemark_data['type'] == 'KU-Line':
                # Untuk KU, gunakan LineString asli dari KML
                line_string = ET.SubElement(placemark_elem, 'LineString')
                coordinates = ET.SubElement(line_string, 'coordinates')
                
                # Gunakan koordinat asli dari data LineString
                if placemark_data['original_geometry'] == 'LineString':
                    coordinates.text = placemark_data['coordinates']
                else:
                    # Jika aslinya Point, buat LineString sederhana dari koordinat tersebut
                    if placemark_data['coordinates'] != 'N/A' and ',' in placemark_data['coordinates']:
                        coords = placemark_data['coordinates'].split(',')
                        if len(coords) >= 2:
                            lon = float(coords[0])
                            lat = float(coords[1])
                            # Buat line pendek dari titik asli
                            line_coords = f"{lon},{lat},0 {lon+0.001},{lat+0.001},0"
                            coordinates.text = line_coords
            else:
                # Untuk non-KU, pertahankan geometry asli
                if placemark_data['original_geometry'] == 'LineString':
                    line_string = ET.SubElement(placemark_elem, 'LineString')
                    coordinates = ET.SubElement(line_string, 'coordinates')
                    coordinates.text = placemark_data['coordinates']
                else:
                    point = ET.SubElement(placemark_elem, 'Point')
                    coordinates = ET.SubElement(point, 'coordinates')
                    coordinates.text = placemark_data['coordinates']
    
    # Convert to string
    rough_string = ET.tostring(kml, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    st.set_page_config(
        page_title="KML Structure Preserver",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ KML Structure Preserver with Line Preservation")
    st.markdown("Upload file KML - Struktur folder tetap, -KU menjadi LineString hijau **dengan line asli**")
    
    # Upload file
    uploaded_file = st.file_uploader("Pilih file KML", type=['kml'])
    
    if uploaded_file is not None:
        # Parse KML dengan struktur folder
        with st.spinner("Menganalisis struktur KML dan line asli..."):
            folders_data, all_placemarks = parse_kml_file(uploaded_file)
        
        if all_placemarks:
            st.success(f"✅ Berhasil mengidentifikasi {len(all_placemarks)} elemen dalam {len(folders_data)} folder!")
            
            # Analisis data
            type_counts = {}
            geometry_counts = {'Point': 0, 'LineString': 0, 'Unknown': 0}
            original_geometry_counts = {'Point': 0, 'LineString': 0, 'Unknown': 0}
            
            for pm in all_placemarks:
                type_name = pm['type']
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
                geometry_counts[pm['geometry_type']] += 1
                original_geometry_counts[pm['original_geometry']] += 1
            
            # Tampilkan summary
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Elemen", len(all_placemarks))
            with col2:
                st.metric("Folder", len(folders_data))
            with col3:
                st.metric("KU-Line", type_counts.get('KU-Line', 0))
            with col4:
                st.metric("LineString Asli", original_geometry_counts.get('LineString', 0))
            with col5:
                st.metric("Point Asli", original_geometry_counts.get('Point', 0))
            
            # Tampilkan struktur folder
            st.subheader("📁 Struktur Folder KML")
            for i, folder_data in enumerate(folders_data):
                with st.expander(f"📂 {folder_data['name']} ({len(folder_data['placemarks'])} items)"):
                    folder_df = pd.DataFrame([{
                        'Nama': pm['name'],
                        'Tipe': pm['type'],
                        'Geometri Asli': pm['original_geometry'],
                        'Geometri Baru': pm['geometry_type'],
                        'Koordinat': pm['coordinates'][:50] + '...' if len(pm['coordinates']) > 50 else pm['coordinates']
                    } for pm in folder_data['placemarks']])
                    st.dataframe(folder_df, use_container_width=True)
            
            # Tampilkan detail konversi KU
            ku_elements = [pm for pm in all_placemarks if pm['type'] == 'KU-Line']
            if ku_elements:
                st.subheader("🔄 Detail Konversi KU-Line")
                ku_df = pd.DataFrame([{
                    'Nama': pm['name'],
                    'Geometri Asli': pm['original_geometry'],
                    'Koordinat Asli': pm['coordinates'][:100] + '...' if len(pm['coordinates']) > 100 else pm['coordinates'],
                    'Status': '✅ LineString Asli' if pm['original_geometry'] == 'LineString' else '⚠️ Point ke LineString'
                } for pm in ku_elements])
                st.dataframe(ku_df, use_container_width=True)
            
            # Download enhanced KML
            st.subheader("📥 Download KML Hasil Identifikasi")
            enhanced_kml = create_enhanced_kml(folders_data)
            
            # Create download link
            b64 = base64.b64encode(enhanced_kml.encode()).decode()
            href = f'<a href="data:application/vnd.google-earth.kml+xml;base64,{b64}" download="enhanced_with_original_lines.kml">⬇️ Download Enhanced KML</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            # Preview perubahan
            st.subheader("🔍 Preview Perubahan")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Sebelum:**")
                st.write(f"- Total LineString: {original_geometry_counts.get('LineString', 0)}")
                st.write(f"- Total Point: {original_geometry_counts.get('Point', 0)}")
                st.write(f"- KU sebagai Point: {len([pm for pm in ku_elements if pm['original_geometry'] == 'Point'])}")
                
            with col2:
                st.write("**Sesudah:**")
                st.write("🟢 **KU-Line**: LineString hijau, Width 3")
                st.write("- Menggunakan koordinat line asli dari KML")
                st.write("- Style: Hijau (#00ff00), Width 3")
                st.write("🔴 **JC01**: Icon forbidden.png")
                st.write("🔵 **OP01**: Icon ltblu-stars.png")
            
            # Statistics
            st.subheader("📈 Statistik Detil")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Distribusi Tipe:**")
                type_df = pd.DataFrame({
                    'Tipe': list(type_counts.keys()),
                    'Jumlah': list(type_counts.values())
                })
                if not type_df.empty:
                    st.bar_chart(type_df.set_index('Tipe'))
            
            with col2:
                st.write("**Perbandingan Geometri:**")
                comparison_df = pd.DataFrame({
                    'Status': ['Asli', 'Setelah Konversi'],
                    'Point': [original_geometry_counts.get('Point', 0), geometry_counts.get('Point', 0)],
                    'LineString': [original_geometry_counts.get('LineString', 0), geometry_counts.get('LineString', 0)]
                })
                st.dataframe(comparison_df, use_container_width=True)
        
        else:
            st.warning("Tidak ada elemen yang ditemukan dalam file KML")

    else:
        # Contoh penggunaan
        st.info("""
        **Fitur Aplikasi:**
        - ✅ Pertahankan struktur folder KML asli
        - ✅ Gunakan **LineString asli** dari KML untuk elemen -KU
        - ✅ Konversi **-KU** → **LineString hijau width 3**
        - ✅ Otomatis identifikasi tipe titik
        
        **Keuntungan:**
        - Line asli dari KML tetap digunakan (tidak dibuat baru)
        - Koordinat path asli dipertahankan
        - Hanya style yang diubah menjadi hijau width 3
        
        **Format yang Didukung:**
        ```xml
        <Placemark>
            <name>R04-CLGO-R015-S13-010-KU01</name>
            <LineString>
                <coordinates>106.1,-6.1,0 106.2,-6.2,0 106.3,-6.3,0</coordinates>
            </LineString>
        </Placemark>
        ```
        """)

if __name__ == "__main__":
    main()
