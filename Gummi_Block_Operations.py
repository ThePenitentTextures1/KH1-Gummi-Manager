import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog as sd
import shutil
import tempfile

from Gummi_Block_Info import gummi_block_names
from Gummi_Block_Info import max_gummi_counts
from Gummi_Block_Info import rare_gummis
from Gummi_Block_Info import design_gummis

#### TODO:
#### Currently the tool reads the unused Gummi Block data from the end of the blueprint.
#### This results in odd behavior such as claiming the selected blueprint calls for 58 Life-Gs, when the blueprint never actually calls for that.
#### The Blueprint_Export module deals with this by extracting only the data that the game actually reads and filling out the remaining space with 00.
#### This commented-out, not-yet-fully-implemented code will make Gummi_Block_Operations read the blueprint in the same way that the game does, ensuring only the used blocks are read.
#
#def read_used_blocks(blueprint_data):
#    # Read Byte 00 to determine how many Gummi Blocks are used in the blueprint
#    num_blocks_used = blueprint_data[0]
#
#    # Extract only the necessary Gummi Block data
#    optimized_blueprint_data = blueprint_data[:0x6C + num_blocks_used * 12]
#
#    return gummi_blocks

# GummiID to Gummi Inventory Offset mapping
def calculate_gummi_offset(gummi_id, gumi_content):
    if gummi_id == 0x00:
        return None  # Skip over GummiID 00
    return 0x9A78 + gummi_id - 1  # Subtract 1 to adjust for skipping GummiID 00

# Function to parse Gummi Block data from the currently selected Blueprint
def parse_gummi_blocks(blueprint_data):
    num_blocks_used = blueprint_data[0]
    gummi_data_start = 0x6C  # Offset where Gummi Block data starts
    gummi_block_size = 12  # Each Gummi Block is 12 bytes
    gummi_blocks = []

    for i in range(num_blocks_used):
        start = gummi_data_start + i * gummi_block_size
        end = start + gummi_block_size
        gummi_block = blueprint_data[start:end]
        gummi_blocks.append(gummi_block)

    return gummi_blocks


# Function to count the quantity of each Gummi Block type used in the Blueprint
def count_gummi_blocks(blueprint_data):
    gummi_blocks = parse_gummi_blocks(blueprint_data)
    gummi_ids = [gummi_block[4] for gummi_block in gummi_blocks]  # Extract GummiID from each Gummi Block
    required_gummi_counts = {gummi_id: gummi_ids.count(gummi_id) for gummi_id in set(gummi_ids)}
    
    # Filter out Gummi Blocks with a quantity of 0
    required_gummi_counts = {gummi_id: count for gummi_id, count in required_gummi_counts.items() if count > 0}
    
    return required_gummi_counts

# Modify the update_gummi_block_list function to take only the blueprint data and gummi block listbox
def get_gummi_type(gummi_id):
    if gummi_id in design_gummis:
        return "Design"
    elif gummi_id in rare_gummis:
        return "Rare"
    else:
        return "Common"