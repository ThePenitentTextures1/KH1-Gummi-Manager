import os
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import logging

import Gummi_Block_Info
from Gummi_Block_Operations import calculate_gummi_offset

# Setting up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def read_gummi_inventory(gumi_content):
    if gumi_content is None:
        return {}

    gummi_inventory = {}
    for gummi_id, gummi_name in Gummi_Block_Info.gummi_block_names.items():
        gummi_offset = calculate_gummi_offset(gummi_id, gumi_content)
        if gummi_offset is not None and gummi_offset < len(gumi_content):
            quantity = int.from_bytes(gumi_content[gummi_offset:gummi_offset + 1], byteorder='little')
            gummi_inventory[gummi_name] = quantity
    return gummi_inventory


# Function to update the Gummi Block inventory in the save file
def update_gummi_inventory(gumi_content, gummi_inventory, update_spinboxes=False):
    for gummi_name, quantity in gummi_inventory.items():
        # Get Gummi ID from the name
        gummi_id = next((id for id, name in Gummi_Block_Info.gummi_block_names.items() if name == gummi_name), None)
        if gummi_id is not None:
            gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id)
            if gummi_offset is not None:
                quantity_bytes = quantity.to_bytes(1, byteorder='little')
                gumi_content[gummi_offset:gummi_offset + len(quantity_bytes)] = quantity_bytes
            else:
                logging.warning(f"Invalid Gummi ID for {gummi_name}.")
        else:
            logging.warning(f"Gummi name {gummi_name} not found in Gummi_Block_Info.")
    return gumi_content

