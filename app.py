# app.py
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import pandas as pd
from io import StringIO, BytesIO
import base64
import zipfile

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
    root_placemarks = []
    for placemark in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
        # Skip jika placemark sudah ada dalam folder
        placemark_name = placemark.find('{http://www.opengis.net/kml/2.2}name')
        placemark_name = placemark_name.text if placemark_name is not None else ''
        
        if not any(pm['name'] == placemark_name for folder in folders_data for pm in folder['placemarks']):
            placemark_data = extract_placemark_data(placemark)
            if placemark_data:
                root_placemarks.append(placemark_data)
                all_placemarks.append(placemark_data)
    
    # Jika ada placemark di root, buat folder khusus
    if root_placemarks:
        folders_data.append({
            'name': 'Root Placemarks',
            'placemarks': root_placemarks
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
    elif '-OB' in name_str:
        return 'OB'
    elif '-OC' in name_str:
        return 'OC'
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
    elif type_name == 'OB':
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png',
            'line_color': None,
            'line_width': None
        }
    elif type_name == 'OC':
        return {
            'icon_url': 'http://maps.google.com/mapfiles/kml/shapes/triangle.png',
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
        
        # Nama folder asli
        name_elem = ET.SubElement(folder_elem, 'name')
        name_elem.text = folder_data['name']
        
        # Description folder (opsional)
        desc_elem = ET.SubElement(folder_elem, 'description')
        desc_elem.text = f"Folder: {folder_data['name']} - {len(folder_data['placemarks'])} items"
        
        # Tambahkan placemarks ke folder asli
        for placemark_data in folder_data['placemarks']:
            placemark_elem = ET.SubElement(folder_elem, 'Placemark')
            
            # Name asli
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
            <b>Folder:</b> {folder_data['name']}<br/>
            <b>Koordinat:</b> {placemark_data['coordinates'][:100]}...<br/>
            <b>Deskripsi Asli:</b> {placemark_data['description']}<br/>
            <b>Style Applied:</b> {get_style_for_type(placemark_data['type'], placemark_data['geometry_type'])['icon_url'] or 'LineString Hijau'}<br/>
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
            
            # Geometry - GUNAKAN GEOMETRI ASLI
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

def create_single_folder_kml(folder_data):
    """Buat KML untuk satu folder saja"""
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Nama document sesuai folder
    name_elem = ET.SubElement(document, 'name')
    name_elem.text = folder_data['name']
    
    # Description document
    desc_elem = ET.SubElement(document, 'description')
    desc_elem.text = f"KML untuk folder: {folder_data['name']} - {len(folder_data['placemarks'])} items"
    
    # Tambahkan semua placemarks dari folder ini
    for placemark_data in folder_data['placemarks']:
        placemark_elem = ET.SubElement(document, 'Placemark')
        
        # Name asli
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
        <b>Folder Asli:</b> {folder_data['name']}<br/>
        <b>Koordinat:</b> {placemark_data['coordinates'][:100]}...<br/>
        <b>Deskripsi Asli:</b> {placemark_data['description']}<br/>
        <b>Style Applied:</b> {get_style_for_type(placemark_data['type'], placemark_data['geometry_type'])['icon_url'] or 'LineString Hijau'}<br/>
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
        
        # Geometry - GUNAKAN GEOMETRI ASLI
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

def create_zip_with_separate_kmls(folders_data):
    """Buat file ZIP berisi KML terpisah untuk setiap folder"""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for folder_data in folders_data:
            # Buat KML untuk folder ini
            folder_kml = create_single_folder_kml(folder_data)
            
            # Buat nama file yang aman
            safe_name = re.sub(r'[^\w\s-]', '', folder_data['name']).strip()
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            filename = f"{safe_name}.kml"
            
            # Tambahkan ke ZIP
            zip_file.writestr(filename, folder_kml)
    
    zip_buffer.seek(0)
    return zip_buffer

def main():
    st.set_page_config(
        page_title="KML Structure Preserver",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ KML Structure Preserver with Complete Rules")
    st.markdown("Upload file KML - Struktur folder **asli dipertahankan**, aturan icon lengkap")
    
    # Upload file
    uploaded_file = st.file_uploader("Pilih file KML", type=['kml'])
    
    if uploaded_file is not None:
        # Parse KML dengan struktur folder asli
        with st.spinner("Menganalisis struktur KML asli..."):
            folders_data, all_placemarks = parse_kml_file(uploaded_file)
        
        if all_placemarks:
            st.success(f"✅ Berhasil mengidentifikasi {len(all_placemarks)} elemen dalam {len(folders_data)} folder!")
            
            # Analisis data
            type_counts = {}
            for pm in all_placemarks:
                type_name = pm['type']
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # Tampilkan summary
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("Total Elemen", len(all_placemarks))
            with col2:
                st.metric("Folder Asli", len(folders_data))
            with col3:
                st.metric("KU-Line", type_counts.get('KU-Line', 0))
            with col4:
                st.metric("OB", type_counts.get('OB', 0))
            with col5:
                st.metric("OC", type_counts.get('OC', 0))
            with col6:
                st.metric("Lainnya", type_counts.get('Unknown', 0))
            
            # Tampilkan struktur folder asli
            st.subheader("📁 Struktur Folder Asli KML")
            for i, folder_data in enumerate(folders_data):
                with st.expander(f"📂 {folder_data['name']} ({len(folder_data['placemarks'])} items)"):
                    folder_df = pd.DataFrame([{
                        'Nama': pm['name'],
                        'Tipe': pm['type'],
                        'Geometri Asli': pm['original_geometry'],
                        'Icon Terapkan': get_style_for_type(pm['type'], pm['geometry_type'])['icon_url'] or 'LineString Hijau'
                    } for pm in folder_data['placemarks']])
                    st.dataframe(folder_df, use_container_width=True)
            
            # Menu Download Options
            st.subheader("📥 Menu Download")
            
            # Tab untuk opsi download
            tab1, tab2, tab3 = st.tabs(["📄 KML Utuh", "📁 KML per Folder", "⚙️ Aturan"])
            
            with tab1:
                st.write("**Download KML Utuh**")
                st.write("Semua folder dalam satu file KML dengan aturan style diterapkan")
                
                enhanced_kml = create_enhanced_kml(folders_data)
                
                # Create download link untuk KML utuh
                b64_kml = base64.b64encode(enhanced_kml.encode()).decode()
                href_kml = f'<a href="data:application/vnd.google-earth.kml+xml;base64,{b64_kml}" download="kml_enhanced_complete.kml">⬇️ Download KML Utuh</a>'
                st.markdown(href_kml, unsafe_allow_html=True)
                
                # Preview kecil
                with st.expander("🔍 Preview KML Utuh"):
                    st.code(enhanced_kml[:1000] + "..." if len(enhanced_kml) > 1000 else enhanced_kml, language='xml')
            
            with tab2:
                st.write("**Download KML per Folder**")
                st.write("Setiap folder menjadi file KML terpisah dalam format ZIP")
                
                # Buat ZIP dengan KML terpisah
                zip_buffer = create_zip_with_separate_kmls(folders_data)
                
                # Create download link untuk ZIP
                b64_zip = base64.b64encode(zip_buffer.getvalue()).decode()
                href_zip = f'<a href="data:application/zip;base64,{b64_zip}" download="kml_folders_separated.zip">⬇️ Download ZIP (KML per Folder)</a>'
                st.markdown(href_zip, unsafe_allow_html=True)
                
                # Tampilkan daftar file dalam ZIP
                st.write("**File yang akan dihasilkan:**")
                for folder_data in folders_data:
                    safe_name = re.sub(r'[^\w\s-]', '', folder_data['name']).strip()
                    safe_name = re.sub(r'[-\s]+', '_', safe_name)
                    st.write(f"📄 {safe_name}.kml ({len(folder_data['placemarks'])} items)")
                
                # Opsi download per folder individual
                st.write("**Download Folder Individual:**")
                col1, col2 = st.columns(2)
                
                for i, folder_data in enumerate(folders_data):
                    with col1 if i % 2 == 0 else col2:
                        folder_kml = create_single_folder_kml(folder_data)
                        safe_name = re.sub(r'[^\w\s-]', '', folder_data['name']).strip()
                        safe_name = re.sub(r'[-\s]+', '_', safe_name)
                        
                        b64_folder = base64.b64encode(folder_kml.encode()).decode()
                        href_folder = f'<a href="data:application/vnd.google-earth.kml+xml;base64,{b64_folder}" download="{safe_name}.kml" style="font-size: 0.8em;">⬇️ {folder_data["name"]}</a>'
                        st.markdown(href_folder, unsafe_allow_html=True)
            
            with tab3:
                st.write("**Aturan yang Diterapkan**")
                rules_data = [
                    {'Pattern': '-JC01', 'Icon': 'forbidden.png', 'Keterangan': 'Titik forbidden'},
                    {'Pattern': '-OP01', 'Icon': 'ltblu-stars.png', 'Keterangan': 'Titik bintang biru'},
                    {'Pattern': '-OB', 'Icon': 'placemark_square.png', 'Keterangan': 'Titik persegi'},
                    {'Pattern': '-OC', 'Icon': 'triangle.png', 'Keterangan': 'Titik segitiga'},
                    {'Pattern': '-KU', 'Icon': 'LineString Hijau', 'Keterangan': 'Garis hijau width 3'},
                    {'Pattern': 'OTB-4x1-Big-Bay', 'Icon': 'picnic.png', 'Keterangan': 'Titik picnic (dari spec_id)'}
                ]
                
                rules_df = pd.DataFrame(rules_data)
                st.dataframe(rules_df, use_container_width=True)
            
            # Statistics detail
            st.subheader("📈 Statistik Detail")
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
                st.write("**Informasi File:**")
                st.write(f"- **Nama file**: {uploaded_file.name}")
                st.write(f"- **Total folder**: {len(folders_data)}")
                st.write(f"- **Total placemarks**: {len(all_placemarks)}")
                st.write(f"- **Folder terbesar**: {max([len(f['placemarks']) for f in folders_data])} items")
                st.write(f"- **Folder terkecil**: {min([len(f['placemarks']) for f in folders_data])} items")
        
        else:
            st.warning("Tidak ada elemen yang ditemukan dalam file KML")

    else:
        # Contoh penggunaan
        st.info("""
        **📋 Aturan Lengkap yang Diterapkan:**

        | Pattern | Icon | Keterangan |
        |---------|------|------------|
        | **-JC01** | 🚫 `forbidden.png` | Titik forbidden |
        | **-OP01** | 🔵 `ltblu-stars.png` | Titik bintang biru |
        | **-OB** | ◼️ `placemark_square.png` | Titik persegi |
        | **-OC** | 🔺 `triangle.png` | Titik segitiga |
        | **-KU** | 🟢 LineString hijau | Garis hijau width 3 |
        | **OTB-4x1-Big-Bay** | 🧺 `picnic.png` | Titik picnic (dari spec_id) |

        **✅ Fitur Utama:**
        - Struktur folder asli **dipertahankan 100%**
        - **Download KML Utuh**: Semua folder dalam satu file
        - **Download KML per Folder**: Setiap folder menjadi file terpisah (ZIP)
        - Aturan icon diterapkan otomatis
        - LineString asli untuk -KU tetap digunakan
        """)

if __name__ == "__main__":
    main()
