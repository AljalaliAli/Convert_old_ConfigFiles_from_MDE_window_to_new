# Filename: db_to_json_config.py

import sqlite3
import os
import json
from PIL import Image
import shutil
import ast
import configparser
 
# Create a ConfigParser object
config = configparser.ConfigParser()
# Read the INI file
config.read('config.ini')

old_template_dir = config.get('Paths', 'old_template_dir')
old_db_path = config.get('Paths', 'old_db_path')
output_dir = config.get('Paths', 'output_dir')
new_template_dir = config.get('Paths', 'new_template_dir')
new_db_path = config.get('Paths', 'new_db_path')
# Step 1: Connect to SQLite database and retrieve data

conn = sqlite3.connect(old_db_path)
cursor = conn.cursor()

# Retrieve data from Modus table
cursor.execute("SELECT * FROM Modus")
modus_data = cursor.fetchall()

# Retrieve data from Parameters table
cursor.execute("SELECT * FROM Parameters")
parameters_data = cursor.fetchall()

# Retrieve data from Refernce_Images table
cursor.execute("SELECT * FROM Refernce_Images")
reference_images_data = cursor.fetchall()

# Close the connection
conn.close()

print(f"Retrieved {len(modus_data)} records from Modus table.")
print(f"Retrieved {len(parameters_data)} records from Parameters table.")
print(f"Retrieved {len(reference_images_data)} records from Refernce_Images table.")

# Step 2: Organize data by machine_id
print("Step 2: Organize data by machine_id ...")
machines = {}

# Process Modus data
for modus in modus_data:
    print('..............', modus)
    try:
        id, name, machine_id = modus
    except:
        id, name  = modus
        machine_id= '1'

    if machine_id not in machines:
        machines[machine_id] = {'modes': [], 'parameters': [], 'images': []}
    machines[machine_id]['modes'].append({'id': id, 'name': name})

# Process Parameters data
for parameter in parameters_data:
    try:
         par_name, mode_id, machine_id, par_pos = parameter
    except:
        machine_id= '1'
        par_name, mode_id,  par_pos = parameter
    
    if machine_id in machines:
        machines[machine_id]['parameters'].append({
            'name': par_name,
            'mode_id': mode_id,
            'position': par_pos
        })

# Process Refernce_Images data
for image in reference_images_data:
    try:
        machine_id, mode_id, merkmal_pos, ref_img_path = image
    except:
        machine_id= '1'
        mode_id, merkmal_pos, ref_img_path = image

    if machine_id in machines:
        machines[machine_id]['images'].append({
            'mode_id': mode_id,
            'merkmal_pos': merkmal_pos,
            'path': ref_img_path
        })

print(f"Processed data for {len(machines)} machines.")

# Step 3: Generate JSON Configuration
print('Step 3: Generate JSON Configuration')

def convert_position(pos_str):
    """
    Convert position string to a dictionary with x1, x2, y1, y2 coordinates.
    """
    pos_tuple = ast.literal_eval(pos_str)
    print(f"pos_str: ", pos_str)
    print(f"pos_tuple: ", pos_tuple)
    x1, y1, x2, y2 =  pos_tuple 
    x1, x2, y1, y2 =  int(x1), int(x2), int(y1), int(y2) 

    return {'x1':x1,'y1': y1, 'x2':x2,'y2': y2 }


def get_image_size(image_path):
    """
    Get the size of the image, handling errors for missing files.
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except FileNotFoundError:
        print(f"Warning: File not found - {image_path}")
        return (0, 0)  # Return default size if the file is not found



configurations = {}
for machine_id, data in machines.items():
    images_config = {}
    for image in data['images']:
        mode_id = image['mode_id']
        image_path = os.path.join(old_template_dir, str(machine_id), image['path'])  #.......................................... machine_id find from config , machine name ...... 
        size = get_image_size(image_path)
        
        if size == (0, 0):
            continue  # Skip images that couldn't be found

        if mode_id not in images_config:
            images_config[mode_id] = {
                'size': {
                    'width': size[0],
                    'height': size[1]
                },
                'path': os.path.basename(image_path),
                'features': {},
                'parameters': {}
            }

        images_config[mode_id]['features']['1'] = {
            'position': convert_position(image['merkmal_pos']),
            'value': '',
            'sypol': ''
        }

    for parameter in data['parameters']:
        mode_id = parameter['mode_id']
        if mode_id in images_config:
            images_config[mode_id]['parameters'][parameter['name']] = {
                'name': parameter['name'],
                'position': convert_position(parameter['position'])
            }

    configurations[machine_id] = {'images': images_config}
    print(' configurations[machine_id]',  configurations[machine_id])

print(f"Generated JSON configuration for {len(configurations)} machines.")

# Step 4: Save JSON and Images
print('Step 4: Save JSON and Images')

 
 
############################################################
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

 
if not os.path.isdir(old_template_dir):
    raise FileNotFoundError(f"The templates directory was not found: {old_template_dir}")

for machine_id, config in configurations.items():
    machine_dir = os.path.join(output_dir, f'machine_{machine_id}')
    if not os.path.exists(machine_dir):
          os.makedirs(machine_dir)
          
    machine_ConfigFiles_dir =os.path.join(f'{machine_dir}', 'ConfigFiles')
    if not os.path.exists(machine_ConfigFiles_dir):
         os.makedirs(os.path.join(machine_dir, 'ConfigFiles'))
    
    new_templates_dir = os.path.join(machine_dir, 'ConfigFiles', 'templates')

    if not os.path.exists(new_templates_dir):
        os.makedirs(new_templates_dir)
       
    # Save JSON configuration
    json_path = os.path.join(machine_ConfigFiles_dir, 'mde_config.json')
    with open(json_path, 'w') as json_file:
        json.dump(config, json_file, indent=4)

    # Copy images
    for image in config['images'].values():
        src_path = os.path.join(old_template_dir, str(machine_id), image['path'])  # Adjust the base path to the templates folder
        dest_path = os.path.join(new_templates_dir, os.path.basename(src_path))
        if os.path.exists(src_path):
            shutil.copy(src_path, dest_path)
        else:
            print(f"Warning: Image file not found - {src_path}")

print("Conversion completed successfully.")
