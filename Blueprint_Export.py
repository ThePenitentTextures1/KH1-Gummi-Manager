import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import tkinter.simpledialog as sd
import shutil
import tempfile

import KH1SYS_Text

def optimize_blueprint(blueprint_data):
    # Read Byte 00 to determine how many Gummi Blocks are used in the blueprint
    num_blocks_used = blueprint_data[0]

    # Extract only the necessary Gummi Block data
    optimized_blueprint_data = blueprint_data[:0x6C + num_blocks_used * 12]

    # Fill out the remaining F6C bytes with 00
    remaining_bytes = 0xF6C - len(optimized_blueprint_data)
    optimized_blueprint_data += bytes(remaining_bytes)

    return optimized_blueprint_data

def decode_blueprint_name(blueprint_data):
    # Extract the encoded name hex from the blueprint data
    encoded_name_hex = blueprint_data[0x4C:0x58]
    
    decoded_name = ''
    # Iterate through each hex value in the encoded name
    for hex_char in encoded_name_hex:
        if hex_char == 0x00:
            break  # Stop decoding if a 0x00 byte is encountered
        if hex_char in KH1SYS_Text.KH1SYS_Text:
            decoded_name += KH1SYS_Text.KH1SYS_Text[hex_char]
        else:
            decoded_name += ""  # Add an empty string if key is not found
    
    return decoded_name

def export_blueprint(save_filename, gumi_data, blueprint_listbox, selected_blueprint=None):
    if selected_blueprint is None:
        # Get the index of the selected blueprint in the listbox
        selected_index = blueprint_listbox.curselection()

        if selected_index:
            # Extract the blueprint number from the listbox item
            selected_blueprint = int(blueprint_listbox.get(selected_index[0]).split()[1])
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to export.")
            return

    # Extract the blueprint data using gumi_data (an instance of GummiBlueprintData)
    blueprint_data = gumi_data.extract_blueprint_data(selected_blueprint)

    if blueprint_data:
        # Optimize the blueprint data
        optimized_blueprint_data = optimize_blueprint(blueprint_data)

        # Capture the decoded name
        decoded_name = decode_blueprint_name(blueprint_data)

        # Replace invalid characters in the decoded name with their corresponding values from KH1SYS_Filename
        decoded_name = ''.join([KH1SYS_Text.KH1SYS_Filename[char] if char in KH1SYS_Text.KH1SYS_Filename else char for char in decoded_name])

        # Construct the output filename
        if not isinstance(save_filename, str):
            messagebox.showerror("Invalid Argument", "save_filename must be a string representing the file path.")
            return
        short_save_filename = os.path.basename(save_filename)
        output_filename = f"{short_save_filename}_#{selected_blueprint}_{decoded_name}.kh1blueprint"

        # Prompt the user to select a destination file
        selected_filename = filedialog.asksaveasfilename(defaultextension=".kh1blueprint", initialfile=output_filename)

        if not selected_filename:
            messagebox.showinfo("Operation Canceled", "Export operation canceled.")
            return

        if os.path.exists(selected_filename):
            confirm_overwrite = messagebox.askokcancel("Warning", f"{selected_filename} already exists. Do you want to overwrite it?")
            if not confirm_overwrite:
                messagebox.showinfo("Operation Canceled", "Export operation canceled.")
                return

        with open(selected_filename, 'wb') as f:
            f.write(optimized_blueprint_data)

        messagebox.showinfo("Export Successful", f"Blueprint exported successfully to:\n{selected_filename}")
    else:
        messagebox.showwarning("Empty Blueprint", f"Blueprint {selected_blueprint} is empty and cannot be exported.")
