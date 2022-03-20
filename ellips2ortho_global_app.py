import pandas as pd
import pydeck as pdk
import rasterio.sample
import requests
import streamlit as st
import zipfile

st.set_page_config(layout="wide")

st.title('Ellipsoidal to Orthometric Heights (Global)')

st.sidebar.image('./logo.png', width = 260)
st.sidebar.markdown('#')
st.sidebar.write('The application uses converted binary data of EGM 96 and EGM 2008 from the National Geospatial-Intelligence Agency to convert ellipsoidal heights to orthometric.')
st.sidebar.write('If you have any questions regarding the application, please contact us at support@wingtra.com.')
st.sidebar.markdown('#')
st.sidebar.info('This is a prototype application. Wingtra AG does not guarantee correct functionality. Use with discretion.')

# Upload button for CSVs

uploaded_csvs = st.file_uploader('Please Select Geotags CSV.', accept_multiple_files=True)
uploaded = False

for uploaded_csv in uploaded_csvs: 
    if uploaded_csv is not None:
        uploaded = True
    else:
        uplaoded = False

# Checking if upload of all CSVs is successful

required_columns = ['# image name',
                    'latitude [decimal degrees]',
                    'longitude [decimal degrees]',
                    'altitude [meter]',
                    'accuracy horizontal [meter]',
                    'accuracy vertical [meter]']

if uploaded:
    dfs = []
    filenames = []
    df_dict = {}
    ctr = 0
    for uploaded_csv in uploaded_csvs:
        df = pd.read_csv(uploaded_csv, index_col=False)       
        dfs.append(df)
        df_dict[uploaded_csv.name] = ctr
        filenames.append(uploaded_csv.name)
        
        lat = 'latitude [decimal degrees]'
        lon = 'longitude [decimal degrees]'
        height = 'altitude [meter]'
        
        ctr += 1
        
        # Check location
        
        url = 'http://api.geonames.org/countryCode?lat='
        geo_request = url + str(df[lat][0]) + '&lng=' + str(df[lon][0]) + '&type=json&username=irwinamago'
        country = requests.get(geo_request).json()['countryName']

        # Check if CSV is in the correct format
        
        format_check = True
        for column in required_columns:
            if column not in list(df.columns):
                st.text(column + ' is not in ' + uploaded_csv.name + '.')
                format_check = False
        
        if not format_check:
            msg = uploaded_csv.name + ' is not in the correct format. Delete or reupload to proceed.'
            st.error(msg)
            st.stop()
    
    st.success('All CSVs checked and uploaded successfully. Your locations are in ' + country + '.')
    
    map_options = filenames.copy()
    map_options.insert(0, '<select>')
    option = st.selectbox('Select geotags CSV to visualize', map_options)
    
    # Option to visualize any of the CSVs
    
    if option != '<select>':
        points_df = pd.concat([dfs[df_dict[option]][lat], dfs[df_dict[option]][lon]], axis=1, keys=['lat','lon'])
        
        st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/satellite-streets-v11',
        initial_view_state=pdk.ViewState(
            latitude=points_df['lat'].mean(),
            longitude=points_df['lon'].mean(),
            zoom=14,
            pitch=0,
         ),
         layers=[
             pdk.Layer(
                 'ScatterplotLayer',
                 data=points_df,
                 get_position='[lon, lat]',
                 get_color='[70, 130, 180, 200]',
                 get_radius=20,
             ),
             ],
         ))
    
    # Geoid Selection
    
    geoid_select = st.selectbox('Please Choose Desired Geoid', ('<select>', 'EGM 96', 'EGM 2008'))
    if not geoid_select=='<select>':
        st.write('You selected:', geoid_select)
    
    if uploaded and not geoid_select=='<select>':
        if st.button('CONVERT HEIGHTS'):
            aws = 'https://s3-eu-west-1.amazonaws.com/download.agisoft.com/gtg/'
            egm96_file = aws + 'us_nga_egm96_15.tif'
            egm2008_file = aws + 'us_nga_egm2008_1.tif'
            file_ctr = 0
            
            for df in dfs:
                if geoid_select=='EGM 96':
                    ortho = []
                    egm96 = rasterio.open(egm96_file)
                    points = list(zip(df[lon].tolist(), df[lat].tolist()))
        
                    i = 0
                    for val in egm96.sample(points):
                        ortho.append(df[height][i] - val[0])
                        i += 1
        
                    df[height] = ortho
                    df.rename(columns={height: 'orthometric height egm96 [meters]'}, inplace=True)
        
                else:
                    ortho = []
                    egm2008 = rasterio.open(egm2008_file)
                    points = list(zip(df[lon].tolist(), df[lat].tolist()))
        
                    i = 0
                    for val in egm2008.sample(points):
                        ortho.append(df[height][i] - val[0])
                        i += 1
        
                    df[height] = ortho        
                    df.rename(columns={height: 'orthometric height egm2008 [meters]'}, inplace=True)
    
            st.success('Height conversion finished. Click button below to download new CSV.')
    
            # Create the zip file, convert the dataframes to CSV, and save inside the zip
            
            if len(dfs)==1:
                csv = dfs[0].to_csv(index=False).encode('utf-8')
                filename = filenames[0].split('.')[0] + '_orthometric.csv'

                st.download_button(
                     label="Download Converted Geotags CSV",
                     data=csv,
                     file_name=filename,
                     mime='text/csv',
                 )
                
            else:                
                with zipfile.ZipFile('Converted_CSV.zip', 'w') as csv_zip:
                    file_ctr = 0
                    for df in dfs:
                        csv_zip.writestr(filenames[file_ctr].split('.')[0] + '_orthometric.csv', df.to_csv(index=False).encode('utf-8'))
                        file_ctr += 1   
                
                # Download button for the zip file
                
                fp = open('Converted_CSV.zip', 'rb')
                st.download_button(
                    label="Download Converted Geotags CSV",
                    data=fp,
                    file_name='Converted_CSV.zip',
                    mime='application/zip',
            )
    st.stop()
else:
    st.stop()
