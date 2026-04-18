import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog as sd
import shutil
import tempfile
import logging
from collections import Counter

from Gummi_Block_Info import gummi_block_names
from Gummi_Block_Info import max_gummi_counts
from Gummi_Block_Info import rare_gummis
from Gummi_Block_Info import design_gummis
from Gummi_Block_Info import rare_design_gummis

# Toggle to reduce per-block debug spam in normal usage.
VERBOSE_DEBUG = False

_GUMMI_INVENTORY_ORDER = sorted(gummi_block_names.keys())
_GUMMI_INVENTORY_INDEX = {gid: idx for idx, gid in enumerate(_GUMMI_INVENTORY_ORDER)}

def calculate_gummi_offset(gummi_id, gumi_content):
    if gummi_id == 0x00:
        return None  # Skip over GummiID 00

    base_offset = 0x9A78 # INVENTORY OFFSET START

    # Inventory entries are stored contiguously in gummi_block_names order.
    index = _GUMMI_INVENTORY_INDEX.get(gummi_id)
    if index is None:
        return None
    gummi_offset = base_offset + index

    # Log the calculated offset
    if VERBOSE_DEBUG:
        logging.debug(
            f"Calculating offset for Gummi ID: {gummi_id}. "
            f"Base Offset: {hex(base_offset)}, Calculated Offset: {hex(gummi_offset)}"
        )

    # Check if the offset is valid within gumi_content
    if gummi_offset < len(gumi_content):
        return gummi_offset
    else:
        logging.error(f"Invalid offset for Gummi ID: {gummi_id}. Offset: {hex(gummi_offset)} exceeds gumi_content length.")
        return None

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
    gummi_ids = (gummi_block[4] for gummi_block in gummi_blocks)  # Extract GummiID from each Gummi Block
    required_gummi_counts = Counter(gummi_ids)
    # Filter out Gummi Blocks with a quantity of 0
    required_gummi_counts = {gummi_id: count for gummi_id, count in required_gummi_counts.items() if count > 0}
    
    return required_gummi_counts

# Modify the update_gummi_block_list function to take only the blueprint data and gummi block listbox
def get_gummi_type(gummi_id):
    if gummi_id in rare_design_gummis:
        return "Chest+Design"
    if gummi_id in design_gummis:
        return "Design"
    elif gummi_id in rare_gummis:
        return "Chest"
    else:
        return "Common"
