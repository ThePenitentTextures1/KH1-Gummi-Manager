import os
import logging
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog as sd
import shutil
import tempfile

import KH1SYS_Text

def extract_imported_blueprint_data(blueprint_filename):
    try:
        with open(blueprint_filename, 'rb') as f:
            imported_blueprint_data = f.read()
            #print(imported_blueprint_data)
        return imported_blueprint_data
    except FileNotFoundError:
        messagebox.showwarning("File Not Found", f"Blueprint file '{blueprint_filename}' not found.")
        return None

def set_gummi_com_levels(gumi_content, imported_blueprint_blocks, num_blueprints, save_filename):
    com_lvl1_offset = 0x9ABC
    com_lvl2_offset = 0x9ABD
    com_lvl3_offset = 0x9ABE

    with open(save_filename, 'r+b') as f:
        f.seek(com_lvl1_offset)
        f.write(b'\x01')  # Set COM. LVL1 to 1 by default

        if imported_blueprint_blocks > 100 or num_blueprints > 1:
            f.seek(com_lvl2_offset)
            f.write(b'\x01')  # Set COM. LVL2 to 1

        if imported_blueprint_blocks > 150 or num_blueprints > 5:
            f.seek(com_lvl3_offset)
            f.write(b'\x01')  # Set COM. LVL3 to 1

def set_gummi_sys_up(gumi_content, blueprint_data, gumi_location, save_filename):
    # Define separate offsets for Sys. Up 1 and Sys. Up 2
    sys_up1_offset = gumi_location + 0x9ABA
    sys_up2_offset = gumi_location + 0x9ABB

    # Determine which offset to use based on blueprint_data
    if blueprint_data[0x02:0x08] == b'\x08\x00\x08\x00\x08\x00':
        target_offset = sys_up1_offset
    elif blueprint_data[0x02:0x08] == b'\x0A\x00\x0A\x00\x0A\x00':
        target_offset = sys_up2_offset
    else:
        # If neither condition is met, do nothing or handle accordingly
        return

    # Perform the file operations
    offset_in_gumi_content = target_offset - gumi_location
    gumi_content[offset_in_gumi_content] = 0x01


def write_imported_blueprint_to_slot(imported_blueprint_data, blueprint_number, blueprint_offsets, gumi_content):
    try:
        # Get the offset for the selected blueprint slot
        blueprint_offset = blueprint_offsets.get(blueprint_number)

        if blueprint_offset is None:
            messagebox.showerror("Invalid Blueprint Number", f"Blueprint number {blueprint_number} is invalid.")
            return False

        # Ensure the imported blueprint data has the correct length (0xF6C bytes)
        blueprint_data_length = 0xF6C
        if len(imported_blueprint_data) != blueprint_data_length:
            messagebox.showerror("Invalid Data Length", "The imported blueprint data has an incorrect size. It must be 0xF6C bytes.")
            return False

        # Write the imported blueprint data into the corresponding slot in the gumi_content
        gumi_content[blueprint_offset:blueprint_offset + blueprint_data_length] = imported_blueprint_data
        return True

    except Exception as e:
        logging.error(f"Error writing imported blueprint to slot: {e}")
        messagebox.showerror("Error", f"An error occurred while importing the blueprint: {e}")
        return False

def import_blueprint(gumi_content, blueprint_listbox, blueprint_offsets, save_filename, gumi_location):
    blueprint_filename = filedialog.askopenfilename(
        title="Import Blueprint", 
        filetypes=[("KH1 Blueprints", "*.kh1blueprint"), ("All Files", "*.*")]
    )

    if blueprint_filename:
        selected_index = blueprint_listbox.curselection()

        if selected_index:
            blueprint_number = int(blueprint_listbox.get(selected_index[0]).split()[1])
            imported_blueprint_data = extract_imported_blueprint_data(blueprint_filename)

            if imported_blueprint_data:
                success = write_imported_blueprint_to_slot(imported_blueprint_data, blueprint_number, blueprint_offsets, gumi_content)
                
                if success:
                    set_gummi_sys_up(gumi_content, imported_blueprint_data, gumi_location, save_filename)

                    replacing_blueprint = gumi_content[blueprint_offsets[blueprint_number]:blueprint_offsets[blueprint_number] + 0xF6C] != b'\x00' * 0xF6C
                    imported_blueprint_blocks = 0  # Set appropriate value based on imported data
                    num_blueprints = 0  # Update with the current number of blueprints

                    if replacing_blueprint:
                        set_gummi_com_levels(gumi_content, imported_blueprint_blocks, num_blueprints, save_filename)
                    else:
                        set_gummi_com_levels(gumi_content, imported_blueprint_blocks, num_blueprints + 1, save_filename)

                    return True
                else:
                    messagebox.showerror("Error", "Failed to import blueprint. Please try again.")
            else:
                messagebox.showwarning("Error", "Failed to read blueprint file.")
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to import into.")
