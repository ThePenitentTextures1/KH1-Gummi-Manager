import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import logging

import KH1SYS_Text
import Gummi_Block_Info
import Blueprint_Export
import Blueprint_Import
import Gummi_Block_Operations
import Gummi_Inventory_Editor

# Setting up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for GUMI data structure
BLUEPRINT_SELECTION_OFFSET = 0x10          # Offset for selected blueprint in gumi_content
BLUEPRINT_DATA_SIZE = 0xF6C                # Size of each blueprint data block
GUMI_CONTENT_SIZE = 0x9B08                 # Total size of GUMI content block
BLUEPRINT_NAME_OFFSET_START = 0x4C         # Start of the encoded blueprint name in blueprint data
BLUEPRINT_NAME_OFFSET_END = 0x58           # End of the encoded blueprint name in blueprint data
INVENTORY_OFFSET_START = 0x9A78            # Start of the Gummi Block inventory in gumi_content


class GummiBlueprintData:
    def __init__(self):
        self.blueprint_offsets = {
            1: 0x1C, 2: 0xF8C, 3: 0x1EFC, 4: 0x2E6C, 5: 0x3DDC,
            6: 0x4D4C, 7: 0x5CBC, 8: 0x6C2C, 9: 0x7B9C, 10: 0x8B0C
        }
        self.file_content = bytearray()
        self.gumi_content = bytearray()
        self.current_gumi_location = ''
        self.blueprint_data = ''

    def load_save_file(self, file_path):
        try:
            with open(file_path, 'rb') as save_file:
                self.file_content = bytearray(save_file.read())

                # Find the GUMI header in the loaded file
                self.current_gumi_location = self.find_gumi_header(self.file_content)

                if self.current_gumi_location is not None:
                    # Extract GUMI content using constant
                    self.gumi_content = bytearray(self.file_content[self.current_gumi_location:self.current_gumi_location + GUMI_CONTENT_SIZE])
                    return True
                else:
                    return False
        except Exception as e:
            logging.error(f"Error loading save file: {e}")
            return False


    def save_changes(self, file_path):
        try:
            with open(file_path, 'r+b') as save_file:
                save_file.seek(self.current_gumi_location)
                save_file.write(self.gumi_content)
            return True
        except Exception as e:
            logging.error(f"Error saving changes: {e}")
            return False

    def find_gumi_header(self, file_content):
        gumi_locations = []
        bislps_pattern = b'BISLPS-25198-'
        bislps_locations = []

        for i in range(len(file_content) - len(bislps_pattern) - 2):
            if file_content[i:i+len(bislps_pattern)] == bislps_pattern:
                if file_content[i+len(bislps_pattern):i+len(bislps_pattern)+2].isdigit():
                    bislps_locations.append(i)

        if not bislps_locations:
            search_start = 0
            search_end = search_start + 4

            while search_end <= len(file_content):
                header = file_content[search_start:search_end]
                if header == b'GUMI':
                    gumi_locations.append(("Entire File", search_start))
                search_start += 1
                search_end = search_start + 4
        else:
            for start in bislps_locations:
                end = len(file_content)
                next_bislps = next((loc for loc in bislps_locations if loc > start), None)
                if next_bislps:
                    end = next_bislps

                search_start = start
                search_end = search_start + 4

                while search_end <= end:
                    header = file_content[search_start:search_end]
                    if header == b'GUMI':
                        bislps_string = file_content[start:start+len(bislps_pattern)+2].decode('ascii')
                        gumi_locations.append((bislps_string, search_start))
                    search_start += 1
                    search_end = search_start + 4

        if len(gumi_locations) == 0:
            return None
        elif len(gumi_locations) == 1:
            return gumi_locations[0][1]  # Return the GUMI offset
        else:
            options = [f"{bislps_string} (Offset: {hex(location)})" for bislps_string, location in gumi_locations]
            dialog = simpledialog.Dialog(self.root, options)
            gumi_location_index = dialog.result

            if gumi_location_index is not None:
                return gumi_locations[gumi_location_index][1]
            else:
                messagebox.showerror("Invalid Selection", "Invalid selection. Please try again.")
                return None

    def list_available_blueprints(self):
        if len(self.gumi_content) > 0:
            blueprint_list = []
            for blueprint_number, offset in self.blueprint_offsets.items():
                blueprint_data = self.extract_blueprint_data(blueprint_number)
                decoded_name = self.decode_blueprint_name(blueprint_data) if blueprint_data else "(Empty)"
                blueprint_list.append(f"Blueprint {blueprint_number} - {decoded_name}")
            return blueprint_list
        return []

    def extract_blueprint_data(self, blueprint_number):
        """Extract the data for a specific blueprint slot."""
        try:
            blueprint_offset = self.blueprint_offsets.get(blueprint_number)
            if blueprint_offset is None:
                return None
            if blueprint_offset < len(self.gumi_content) and len(self.gumi_content) >= (blueprint_offset + BLUEPRINT_DATA_SIZE):
                blueprint_data = self.gumi_content[blueprint_offset:blueprint_offset + BLUEPRINT_DATA_SIZE]
                if blueprint_data[0] == 0x00:  # Empty blueprint
                    return None
                return blueprint_data
            return None
        except Exception as e:
            logging.error(f"Error extracting blueprint data: {e}")
            return None

    def get_selected_blueprint(self):
        """Returns the currently selected blueprint slot based on the byte at the blueprint selection offset."""
        if len(self.gumi_content) > BLUEPRINT_SELECTION_OFFSET:
            return self.gumi_content[BLUEPRINT_SELECTION_OFFSET] + 1  # Convert 0-9 to 1-10
        return None

    def set_selected_blueprint(self, blueprint_number):
        """Sets the currently selected blueprint slot."""
        if 1 <= blueprint_number <= 10:
            self.gumi_content[BLUEPRINT_SELECTION_OFFSET] = blueprint_number - 1    # Convert 1-10 to 0-9
            return True
        return False

    def select_blueprint(self, blueprint_number):
        """Selects the blueprint and updates the gumi_content."""
        self.blueprint_data = self.extract_blueprint_data(blueprint_number)
        if self.blueprint_data:
            return self.set_selected_blueprint(blueprint_number)
        return False

    def decode_blueprint_name(self, blueprint_data):
        """Decode the encoded blueprint name from the blueprint data."""
        encoded_name_hex = blueprint_data[BLUEPRINT_NAME_OFFSET_START:BLUEPRINT_NAME_OFFSET_END]

        decoded_name = ''
        for hex_char in encoded_name_hex:
            if hex_char == 0x00:  # Stop decoding if null byte is encountered
                break
            decoded_name += KH1SYS_Text.KH1SYS_Text.get(hex_char, "")
        
        return decoded_name

    def rename_blueprint(self, blueprint_number, new_name):
        """Rename the blueprint by encoding the new name and updating the gumi content."""
        blueprint_data = self.extract_blueprint_data(blueprint_number)

        if blueprint_data:
            # Encode the new name
            encoded_name_bytes = self.encode_blueprint_name(new_name)
            updated_blueprint_data = self.update_blueprint_name(blueprint_data, encoded_name_bytes)

            # Write the updated blueprint data back to the save file content
            success = self.write_blueprint_to_slot(updated_blueprint_data, blueprint_number)
            return success
        else:
            return False

    def delete_blueprint(self, blueprint_number):
        """Delete the blueprint by overwriting its content with 0x00 bytes."""
        offset = self.blueprint_offsets.get(blueprint_number)
        if offset is not None:
            start_pos = offset
            end_pos = start_pos + BLUEPRINT_DATA_SIZE  # Use constant here
            self.gumi_content[start_pos:end_pos] = bytes(BLUEPRINT_DATA_SIZE)  # Overwrite with zeros
            return True
        else:
            return False

    def encode_blueprint_name(self, name):
        """Encode the name into bytes."""
        encoded_name = bytearray()
        name = name[:12]  # Ensure the name is not longer than 12 characters

        for char in name:
            hex_value = next((k for k, v in KH1SYS_Text.KH1SYS_Text.items() if v == char), None)
            if hex_value is not None:
                encoded_name.append(hex_value)
            else:
                encoded_name.append(0x20)  # Default to space (0x20)

        encoded_name.extend([0x00] * (12 - len(name)))  # Pad to 12 bytes
        return encoded_name

    def update_blueprint_name(self, blueprint_data, encoded_name_bytes):
        """Update the encoded name bytes in the blueprint data."""
        if len(encoded_name_bytes) != 12:
            raise ValueError("Encoded name bytes must be of length 12.")
        blueprint_data[BLUEPRINT_NAME_OFFSET_START:BLUEPRINT_NAME_OFFSET_END] = encoded_name_bytes  # Replace name in blueprint data
        return blueprint_data


    def write_blueprint_to_slot(self, updated_blueprint_data, blueprint_number):
        """Write the updated blueprint data back to the appropriate slot in gumi_content."""
        blueprint_offset = self.blueprint_offsets.get(blueprint_number)
        if blueprint_offset is None:
            return False

        start_pos = blueprint_offset
        end_pos = start_pos + len(updated_blueprint_data)
        self.gumi_content[start_pos:end_pos] = updated_blueprint_data
        return True

    def add_required_gummi_blocks(self, include_rare=False, include_design=False):
        """Automatically add required Gummi Blocks to the inventory based on the selected blueprint."""
        if not self.blueprint_data:
            messagebox.showerror("No Blueprint Selected", "Please select a blueprint first.")
            return

        # Get the current required Gummi counts from the blueprint
        required_gummi_counts = Gummi_Block_Operations.count_gummi_blocks(self.blueprint_data)

        # Go through required Gummi counts and add to inventory
        for gummi_id, required_count in required_gummi_counts.items():
            # Filter based on parameters
            gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)

            if gummi_type == "Rare" and not include_rare:
                continue  # Skip if Rare Gummis are not selected

            if gummi_type == "Design" and not include_design:
                continue  # Skip if Design Gummis are not selected

            # Get the current quantity of the Gummi block in inventory
            gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, self.gumi_content)
            if gummi_offset is not None:
                current_quantity = self.gumi_content[gummi_offset]
                max_quantity = Gummi_Block_Info.max_gummi_counts.get(gummi_id, 1)

                # Add required Gummis, but do not exceed max allowed quantity
                if current_quantity < required_count:
                    new_quantity = required_count
                else:
                    new_quantity = current_quantity

                self.gumi_content[gummi_offset] = new_quantity

        # You might want to return a success flag or message
        return True

class GummiBlueprintGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KH1 Gummi Manager")
        self.root.geometry("720x450")

        self.data = GummiBlueprintData()  # Data handler class

        self.save_filename = ''
        self.inventory_spinboxes = {}
        self.current_ship_label = None  # For displaying the current selected ship

        self.setup_ui()

    def setup_ui(self):
        logging.debug("Setting up UI elements.")
        
        # Create a frame for the load button
        load_button_frame = tk.Frame(self.root)
        load_button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Load Save File button
        load_button = tk.Button(load_button_frame, text="Load Save File", command=self.load_save_file)
        load_button.pack(side=tk.LEFT, pady=10)

        # Save Changes button
        save_changes_button = tk.Button(load_button_frame, text="Save Changes", command=self.save_changes)
        save_changes_button.pack(side=tk.LEFT, pady=10)

        # Create the result_frame for current save, ship, and system levels display
        self.result_frame = tk.Frame(load_button_frame)
        self.result_frame.pack(side=tk.RIGHT, pady=10)

        # Create current_save_label to display the filename of the loaded save file
        self.current_save_label = tk.Label(self.result_frame, text="")
        self.current_save_label.pack(side=tk.TOP)

        # Create current_ship_label to display the current selected Gummi Ship
        self.current_ship_label = tk.Label(self.result_frame, text="")
        self.current_ship_label.pack(side=tk.TOP)

        # Create sys_up_label to display the current max Gummi Sys. Up
        self.sys_up_label = tk.Label(self.result_frame, text="")
        self.sys_up_label.pack(side=tk.TOP)

        # Create com_lvl_label to display the current max Gummi COM Lvl.
        self.com_lvl_label = tk.Label(self.result_frame, text="")
        self.com_lvl_label.pack(side=tk.TOP)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        self.setup_blueprint_tab()
        self.setup_inventory_tabs()

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Rename", command=self.rename_blueprint)
        self.context_menu.add_command(label="Delete", command=self.delete_blueprint)

        # Bind the right-click event to show the context menu
        self.blueprint_listbox.bind("<Button-3>", self.show_context_menu)

        logging.debug("UI setup complete.")


    def rename_blueprint(self):
        """Prompt user to rename the selected blueprint."""
        selected_index = self.blueprint_listbox.curselection()
        if selected_index:
            blueprint_number = int(self.blueprint_listbox.get(selected_index[0]).split()[1])
            current_name = self.data.decode_blueprint_name(self.data.extract_blueprint_data(blueprint_number))

            # Prompt for new name
            new_name = simpledialog.askstring("Rename Blueprint", f"Enter new name for Blueprint {blueprint_number}:", initialvalue=current_name)
            if new_name:
                success = self.data.rename_blueprint(blueprint_number, new_name)
                if success:
                    self.refresh_blueprint_list()
                    messagebox.showinfo("Blueprint Renamed", f"Blueprint {blueprint_number} renamed to '{new_name}' successfully.")
                else:
                    messagebox.showerror("Error", "Failed to rename blueprint.")
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to rename.")

    def delete_blueprint(self):
        """Delete the selected blueprint."""
        selected_index = self.blueprint_listbox.curselection()
        if selected_index:
            blueprint_number = int(self.blueprint_listbox.get(selected_index[0]).split()[1])
            blueprint_name = self.data.decode_blueprint_name(self.data.extract_blueprint_data(blueprint_number))

            # Confirm deletion
            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {blueprint_name}?")
            if confirm:
                success = self.data.delete_blueprint(blueprint_number)
                if success:
                    self.refresh_blueprint_list()
                    self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
                    messagebox.showinfo("Blueprint Deleted", f"{blueprint_name} deleted successfully.")
                else:
                    messagebox.showerror("Error", "Failed to delete blueprint.")
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to delete.")

    def setup_blueprint_tab(self):
        logging.debug("Setting up Blueprint tab.")
        blueprint_tab = ttk.Frame(self.notebook)
        self.notebook.add(blueprint_tab, text='Blueprint Manager')

        blueprint_frame = tk.Frame(blueprint_tab)
        blueprint_frame.pack(side=tk.LEFT, padx=10, pady=10)

        blueprint_label = tk.Label(blueprint_frame, text="Blueprints in save file:")
        blueprint_label.pack()

        self.blueprint_listbox = tk.Listbox(blueprint_frame, width=30, height=10)
        self.blueprint_listbox.pack(side=tk.TOP, expand=False)

        # Bind left-click and right-click events
        self.blueprint_listbox.bind("<<ListboxSelect>>", self.on_blueprint_select)
        self.blueprint_listbox.bind("<Button-3>", self.show_context_menu)  # Right-click binding

        export_button = tk.Button(blueprint_frame, text="Export Blueprint", command=self.export_blueprint)
        export_button.pack(side=tk.BOTTOM, padx=10)

        import_button = tk.Button(blueprint_frame, text="Import Blueprint", command=self.import_blueprint)
        import_button.pack(side=tk.BOTTOM, padx=10)

        # Frame for Gummi Block list and Gummi Inventory
        gummi_frame = tk.Frame(blueprint_tab)
        gummi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create Treeview with four columns: Type, Name, Required, Inventory
        columns = ('Type', 'Gummi Block', 'Required', 'Inventory')
        self.gummi_treeview = ttk.Treeview(gummi_frame, columns=columns, show='headings', height=10)

        # Define headings
        self.gummi_treeview.heading('Type', text='Type')
        self.gummi_treeview.heading('Gummi Block', text='Gummi Block')
        self.gummi_treeview.heading('Required', text='Required')
        self.gummi_treeview.heading('Inventory', text='Inventory')

        # Define column widths
        self.gummi_treeview.column('Type', width=70)
        self.gummi_treeview.column('Gummi Block', width=220)
        self.gummi_treeview.column('Required', width=70)
        self.gummi_treeview.column('Inventory', width=70)

        # Add scrollbars to the treeview
        scrollbar_y = ttk.Scrollbar(gummi_frame, orient="vertical", command=self.gummi_treeview.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.gummi_treeview.configure(yscrollcommand=scrollbar_y.set)

        # Pack the treeview so it fills the space above the button frame
        self.gummi_treeview.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Create a new frame for the button and checkboxes, and pack it to the bottom of gummi_frame
        button_frame = tk.Frame(gummi_frame)
        button_frame.pack(side=tk.BOTTOM, pady=10, fill=tk.X)

        # Add the "Add Required Gummi Blocks" button to the button_frame
        add_gummi_button = tk.Button(
            button_frame,
            text="Add Required Gummi Blocks",
            command=self.add_required_gummi_blocks  # Updated to call GUI method
        )
        add_gummi_button.pack(side=tk.LEFT, padx=5)

        # Add checkboxes to the button_frame and align them to the right of the button
        self.include_rare_var = tk.BooleanVar(value=False)
        self.include_design_var = tk.BooleanVar(value=False)

        self.include_rare_check = tk.Checkbutton(button_frame, text="Include Rare Gummi", variable=self.include_rare_var)
        self.include_rare_check.pack(side=tk.LEFT, padx=5)

        self.include_design_check = tk.Checkbutton(button_frame, text="Include Design Gummi", variable=self.include_design_var)
        self.include_design_check.pack(side=tk.LEFT, padx=5)


    def update_gummi_treeview(self, blueprint_data, gumi_content):
        """Update the Treeview with Gummi Block types, names, required counts, and inventory counts."""
        self.gummi_treeview.delete(*self.gummi_treeview.get_children())  # Clear the treeview

        # Get the required Gummi Blocks from the blueprint data
        required_gummi_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)

        # Populate Treeview with Gummi Block information
        for gummi_id, required_count in required_gummi_counts.items():
            gummi_name = Gummi_Block_Info.gummi_block_names.get(gummi_id)
            if gummi_name:
                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, gumi_content)

                # Get the current inventory count
                inventory_count = int.from_bytes(gumi_content[gummi_offset:gummi_offset + 1], byteorder='little') if gummi_offset is not None else 0

                # Determine the Gummi Block type (Common, Rare, Design)
                gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)

                # Insert row into Treeview
                self.gummi_treeview.insert('', 'end', values=(gummi_type, gummi_name, required_count, inventory_count))

    def on_blueprint_select(self, event=None):
        """Handles blueprint selection from both left and right mouse clicks."""
        selected_index = self.blueprint_listbox.curselection()
        if selected_index:
            # Get the selected blueprint slot number directly from the listbox index
            blueprint_number = selected_index[0] + 1  # Index 0 -> Blueprint 1, Index 9 -> Blueprint 10

            # Call the data logic to select the blueprint
            if self.data.select_blueprint(blueprint_number):
                self.update_current_ship_label()  # Update the GUI label

                # Update the consolidated Treeview with Gummi Block, type, required count, and inventory data
                self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
                self.refresh_blueprint_list()
                self.update_current_ship_label()  # Update the current ship label with the name
                self.update_gummi_stats()  # Update Gummi Sys. Up and COM Lvl. stats

    def show_context_menu(self, event):
        """Display the context menu on right-click and select the clicked blueprint."""
        # Get the index of the item clicked
        index = self.blueprint_listbox.nearest(event.y)

        # Set the selection
        self.blueprint_listbox.selection_clear(0, tk.END)
        self.blueprint_listbox.selection_set(index)
        self.blueprint_listbox.activate(index)

        # Call the left-click logic to update the GUI
        self.on_blueprint_select()

        # Display the context menu
        try:
            self.context_menu.post(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def update_current_selection(self, index):
        """Updates the current selection based on the given index."""
        selected_blueprint = int(self.blueprint_listbox.get(index).split()[1])
    
        # Extract blueprint data
        blueprint_data = self.data.extract_blueprint_data(selected_blueprint)
        if blueprint_data:
            # Set the selected blueprint as the current ship
            self.data.set_selected_blueprint(selected_blueprint)
            self.update_current_ship_label()
        
            # Parse and update the Gummi Block and Inventory lists
            self.update_gummi_block_list(blueprint_data)
            self.update_gummi_inventory_list(self.data.gumi_content, blueprint_data)

    def update_gummi_block_list(self, blueprint_data):
        """Update the Gummi Block listbox based on the blueprint data."""
        self.gummi_block_listbox.delete(0, tk.END)

        # Use Gummi_Block_Operations to parse the Gummi block data
        gummi_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)

        for gummi_id, count in gummi_counts.items():
            if gummi_id in Gummi_Block_Info.gummi_block_names:
                gummi_name = Gummi_Block_Info.gummi_block_names[gummi_id]
                gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)
                gummi_info = f" {gummi_type} Gummi: x{count} {gummi_name}"
                self.gummi_block_listbox.insert(tk.END, gummi_info)

    def update_gummi_inventory_list(self, gumi_content, blueprint_data):
        """Update the Gummi Inventory listbox based on the current inventory and blueprint data."""
        self.gummi_inventory_listbox.delete(0, tk.END)

        # Use Gummi_Block_Operations to count the required Gummi blocks
        required_gummi_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)

        # Build the Gummi inventory display
        for gummi_id, count in required_gummi_counts.items():
            gummi_name = Gummi_Block_Info.gummi_block_names.get(gummi_id)
            if gummi_name:
                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, gumi_content)
                if gummi_offset is not None:
                    quantity = int.from_bytes(gumi_content[gummi_offset:gummi_offset + 1], byteorder='little')
                    gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)
                    gummi_info = f" {gummi_type} Gummi: x{quantity} {gummi_name}"
                    self.gummi_inventory_listbox.insert(tk.END, gummi_info)

    def load_save_file(self):
        # Clear previous file content
        self.data.file_content = bytearray()
        self.data.gumi_content = bytearray()

        file_path = filedialog.askopenfilename(title="Select a Save File", filetypes=[("All Files", "*.*")])

        if file_path and self.data.load_save_file(file_path):
            self.save_filename = file_path
            short_save_filename = os.path.basename(file_path)  # Use os.path.basename instead

            # Update current_save_label with the short filename
            self.current_save_label.config(text=f"Save File: {short_save_filename}")

            self.refresh_blueprint_list()
            self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
            self.update_current_ship_label()  # Update the current ship label with the name
            self.update_gummi_stats()  # Update Gummi Sys. Up and COM Lvl. stats
        else:
            # Clear labels and reset state if the file load fails
            self.current_save_label.config(text="")
            self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
            self.sys_up_label.config(text="Gummi Sys. Up: N/A")
            self.com_lvl_label.config(text="Gummi COM Lvl.: N/A")
            messagebox.showerror("Error", "GUMI header not found in the save file")

    def update_gummi_stats(self):
        """Updates the Sys. Up and COM Lvl labels based on gumi_content values."""

        # Read Sys. Up levels
        sys_up_1 = self.data.gumi_content[0x9ABA]
        sys_up_2 = self.data.gumi_content[0x9ABB]
        
        # Determine max Sys. Up
        if sys_up_2 == 1:
            max_sys_up = 2
        elif sys_up_1 == 1:
            max_sys_up = 1
        else:
            max_sys_up = 0

        # Read COM Lvl values
        com_lvl_1 = self.data.gumi_content[0x9ABC]
        com_lvl_2 = self.data.gumi_content[0x9ABD]
        com_lvl_3 = self.data.gumi_content[0x9ABE]
        
        # Determine max COM Lvl
        if com_lvl_3 == 1:
            max_com_lvl = 3
        elif com_lvl_2 == 1:
            max_com_lvl = 2
        elif com_lvl_1 == 1:
            max_com_lvl = 1
        else:
            max_com_lvl = 0

        # Update the labels with the determined values
        self.sys_up_label.config(text=f"Sys. Up: {max_sys_up}")
        self.com_lvl_label.config(text=f"COM Lvl: {max_com_lvl}")

    def update_current_ship_label(self):
        """Update the label to show the currently selected ship."""
        selected_blueprint_number = self.data.get_selected_blueprint()
        if selected_blueprint_number:
            blueprint_data = self.data.extract_blueprint_data(selected_blueprint_number)
            blueprint_name = self.data.decode_blueprint_name(blueprint_data) if blueprint_data else "(Empty)"
            
            # Update the current_ship_label with the selected ship's name
            self.current_ship_label.config(text=f"Current Ship: #{selected_blueprint_number} - {blueprint_name}")

            # Also select the corresponding blueprint in the listbox
            self.blueprint_listbox.selection_clear(0, tk.END)
            self.blueprint_listbox.selection_set(selected_blueprint_number - 1)
            self.blueprint_listbox.activate(selected_blueprint_number - 1)

    def save_changes(self):
        if self.save_filename:
            if self.data.save_changes(self.save_filename):
                messagebox.showinfo("Success", "Changes saved successfully.")
            else:
                messagebox.showerror("Save Error", "Failed to save changes.")
        else:
            messagebox.showerror("Invalid File Path", "No save file loaded.")

    def refresh_blueprint_list(self):
        self.blueprint_listbox.delete(0, tk.END)
        blueprints = self.data.list_available_blueprints()
        for blueprint in blueprints:
            self.blueprint_listbox.insert(tk.END, blueprint)

#Pre-Indented
    def import_blueprint(self):
        # Call the import blueprint function from Blueprint_Import
        success = Blueprint_Import.import_blueprint(
            self.data.gumi_content,
            self.blueprint_listbox,
            self.data.blueprint_offsets,
            self.save_filename,
            self.data.current_gumi_location
        )

        # If the import was successful, update the blueprint listbox
        if success:
            # Refresh the blueprint list and other GUI elements
            self.refresh_blueprint_list()
            self.update_current_ship_label()
            self.update_gummi_stats()
            self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
            self.refresh_inventory_editor()



    def export_blueprint(self):
        # Pass self.data (which contains gumi_content and extract_blueprint_data method) to export_blueprint
        Blueprint_Export.export_blueprint(self.save_filename, self.data, self.blueprint_listbox)

    def setup_inventory_tabs(self):
        logging.debug("Setting up Inventory tabs.")
        gummi_inventory_tab = ttk.Frame(self.notebook)
        blueprint_collection_tab = ttk.Frame(self.notebook)

        self.notebook.add(gummi_inventory_tab, text='Gummi Block Inventory')
        self.notebook.add(blueprint_collection_tab, text='Blueprint Collection')

        self.create_inventory_editor(gummi_inventory_tab, show_blueprints=False)
        self.create_inventory_editor(blueprint_collection_tab, show_blueprints=True)
        logging.debug("Inventory tabs setup complete.")

    def create_inventory_editor(self, tab, show_blueprints):
        logging.debug("Creating inventory editor for %s", "Blueprint Collection" if show_blueprints else "Gummi Block Inventory")

        # Create a canvas and scrollbar for scrolling through the inventory
        canvas = tk.Canvas(tab)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        editor_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=editor_frame, anchor="nw")

        # Variable to keep track of the spinbox count
        spinbox_count = 0

        row = 1
        # Loop through the Gummi Block info and create labels and spinboxes
        for gummi_id, gummi_name in Gummi_Block_Info.gummi_block_names.items():
            if (gummi_id in Gummi_Block_Info.gummi_blueprints) == show_blueprints:
                gummi_label = ttk.Label(editor_frame, text=gummi_name)
                gummi_label.grid(row=row, column=0, sticky="w")
            
                var = tk.IntVar(value=0)
                gummi_spinbox = tk.Spinbox(
                    editor_frame,
                    textvariable=var,
                    from_=0,
                    to=Gummi_Block_Info.max_gummi_counts.get(gummi_id, 1)
                )
                gummi_spinbox.grid(row=row, column=1)

                # Store reference to the spinboxes in the inventory dictionary
                self.inventory_spinboxes[gummi_name] = var

                # Bind the variable to update gumi_content
                var.trace_add('write', lambda *args, name=gummi_name, var=var: self.update_gummi_quantity(name, var.get()))
                spinbox_count += 1
                row += 1

        logging.debug("Created %d spinboxes for %s", spinbox_count, "Blueprints" if show_blueprints else "Gummi Blocks")

        # Update the canvas scrollregion when the content changes
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def update_gummi_quantity(self, gummi_name, quantity):
        try:
            # Convert quantity to integer
            quantity = int(quantity)

            # Get the Gummi ID from the name
            gummi_id = next(
                (id for id, name in Gummi_Block_Info.gummi_block_names.items() if name == gummi_name),
                None
            )
            if gummi_id is not None:
                # Get the maximum allowed quantity for this Gummi Block
                max_quantity = Gummi_Block_Info.max_gummi_counts.get(gummi_id, 1)

                # Ensure quantity is within valid range
                quantity = max(0, min(quantity, max_quantity))

                # Calculate the offset in gumi_content
                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, self.data.gumi_content)
                if gummi_offset is not None:
                    # Update gumi_content with the new quantity
                    self.data.gumi_content[gummi_offset] = quantity
                else:
                    logging.warning(f"Invalid Gummi offset for {gummi_name} (ID: {gummi_id}).")
            else:
                logging.warning(f"Gummi name {gummi_name} not found in gummi_block_names.")
        except ValueError:
            messagebox.showerror("Invalid Input", f"Invalid quantity for {gummi_name}. Please enter a valid number.")

    def refresh_inventory_editor(self):
        """Refresh the inventory editor after data changes by updating only changed values."""
        gummi_inventory = Gummi_Inventory_Editor.read_gummi_inventory(self.data.gumi_content)

        for gummi_name, var in self.inventory_spinboxes.items():
            # Check if the gummi_name exists in the current inventory
            if gummi_name in gummi_inventory:
                # Get the current inventory value for the gummi_name
                inventory_value = gummi_inventory[gummi_name]
            
                # Only update the Spinbox if the value has changed
                if var.get() != inventory_value:
                    var.set(inventory_value)  # Update the Spinbox with the new value
                    logging.debug(f"Updated Spinbox for {gummi_name}: {inventory_value}")

    def add_required_gummi_blocks(self):
        """Handle the addition of required Gummi Blocks based on user selections."""
        include_rare = self.include_rare_var.get()
        include_design = self.include_design_var.get()
        success = self.data.add_required_gummi_blocks(include_rare, include_design)
        if success:
            self.refresh_inventory_editor()
            self.update_gummi_treeview(self.data.blueprint_data, self.data.gumi_content)
            messagebox.showinfo("Success", "Required Gummi Blocks have been added to the inventory.")

# Main application execution point
if __name__ == "__main__":
    root = tk.Tk()
    app = GummiBlueprintGUI(root)
    root.mainloop()
