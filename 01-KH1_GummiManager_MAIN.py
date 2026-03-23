import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import logging
import re
import struct
import json
import os
import sys
import traceback

from decrypt import getDecryptedEntries, getValidSaveEntries
import KH1SYS_Text
import Gummi_Block_Info
import Blueprint_Export
import Blueprint_Import
import Gummi_Block_Operations
import Gummi_Inventory_Editor

# Toggle to reduce debug spam for routine scans.
VERBOSE_DEBUG = False
# Optional: include per-blueprint counts in stats recompute logs.
VERBOSE_STATS_REASON = False

# Setting up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def _log_startup_exception(exc_type, exc_value, exc_tb):
    try:
        log_path = os.path.join(os.path.dirname(__file__), "gummi_manager_crash.log")
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write("Unhandled exception during startup:\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=handle)
    except Exception:
        pass

sys.excepthook = _log_startup_exception

# Constants for GUMI data structure
BLUEPRINT_SELECTION_OFFSET = 0x10          # Offset for selected blueprint in gumi_content
BLUEPRINT_DATA_SIZE = 0xF6C                # Size of each blueprint data block
GUMI_CONTENT_SIZE = 0x9B64                 # Total size of GUMI content block (includes control bytes)
BLUEPRINT_NAME_OFFSET_START = 0x4C         # Start of the encoded blueprint name in blueprint data
BLUEPRINT_NAME_OFFSET_END = 0x58           # End of the encoded blueprint name in blueprint data
INVENTORY_OFFSET_START = 0x9A78            # Start of the Gummi Block inventory in gumi_content


class GummiBlueprintData:
    def __init__(self):
        # Offsets for blueprint slots
        self.blueprint_offsets = {
            1: 0x1C, 2: 0xF8C, 3: 0x1EFC, 4: 0x2E6C, 5: 0x3DDC,
            6: 0x4D4C, 7: 0x5CBC, 8: 0x6C2C, 9: 0x7B9C, 10: 0x8B0C
        }
        self.file_content = bytearray()
        self.gumi_offsets = {}      # Key: save_number, Value: Offset to GUMI content
        self.gumi_contents = {}     # Key: save_number, Value: bytearray of GUMI content
        self.gumi_content = None    # Active save’s GUMI content (a bytearray)
        self.blueprint_data = ''
        self.current_save_number = '01'  # Default; will be updated when a save is loaded
        self.last_validation_error = ""

    def load_save_file(self, file_path):
        """
        Load the save file and extract all GUMI content entries.
        Once loaded, set the active save’s content into self.gumi_content.
        """
        try:
            with open(file_path, 'rb') as save_file:
                self.file_content = bytearray(save_file.read())
            logging.info(f"Loaded save file: {file_path}")

            if not self.validate_save_file(self.file_content, file_path):
                logging.error("File failed save validation checks.")
                return False

            # Find all GUMI header offsets; pass file_path for name extraction
            gumi_locations = self.find_gumi_header(self.file_content, file_path)
            if not gumi_locations:
                logging.error("No valid GUMI headers found. Load failed.")
                return False

            # Clear any previous save data
            self.gumi_contents = {}
            self.gumi_content = {}
            self.gumi_offsets = {}

            # Extract each save’s GUMI content
            for save_number, gumi_offset in gumi_locations:
                if gumi_offset + GUMI_CONTENT_SIZE > len(self.file_content):
                    logging.error(f"GUMI content at offset {hex(gumi_offset)} exceeds file size. Skipping.")
                    continue
                content = bytearray(self.file_content[gumi_offset : gumi_offset + GUMI_CONTENT_SIZE])
                self.gumi_contents[save_number] = content
                self.gumi_offsets[save_number] = gumi_offset
                logging.debug(f"Extracted GUMI content for Save {save_number} at offset {hex(gumi_offset)}")

            # Set the active save to the first entry (tabs will allow switching)
            if self.gumi_contents:
                save_num = list(self.gumi_contents.keys())[0]
                self.current_save_number = save_num
                self.gumi_content = self.gumi_contents[save_num]
                logging.info(f"Active GUMI content set to Save {save_num}")

            return True

        except Exception as e:
            logging.error(f"Error loading save file: {e}")
            return False

    def validate_save_file(self, file_content, file_path):
        """Validate that the file looks like a KH1 Gummi save (PS2 or PC)."""
        self.last_validation_error = ""
        if not file_content:
            logging.error("File is empty.")
            self.last_validation_error = "File is empty."
            return False

        png_signature = b"\x89PNG\r\n\x1a\n"
        is_png = file_content.startswith(png_signature)

        if is_png:
            # PC port: must include BISLPS-25198-XX entries after decryption
            pattern = re.compile(br'BISLPS-25198-\d{2}')
            if not pattern.search(file_content):
                logging.error("PNG file does not contain KHFM save markers (BISLPS-25198-XX).")
                self.last_validation_error = "PNG does not contain KHFM save markers (BISLPS-25198-XX)."
                return False
            try:
                decrypted_entries = getValidSaveEntries(file_content)
                has_valid_entry = bool(decrypted_entries)
                if not has_valid_entry:
                    logging.error("PNG file does not contain valid decrypted KHFM save entries.")
                    self.last_validation_error = "PNG does not contain valid decrypted KHFM save entries."
                    return False
            except Exception as e:
                logging.error(f"Failed to validate PNG save entries: {e}")
                self.last_validation_error = f"Failed to validate PNG save entries: {e}"
                return False
            return True

        # PS2 save: filename should match known region IDs and GUMI must be at 0x2400
        basename = os.path.basename(file_path)
        ps2_pattern = re.compile(
            r'^(BISLPS-25198|BISLPS-25105|BASLUS-20370|BESCES-50967|BESCES-50968|'
            r'BESCES-50969|BESCES-50970|BESCES-50971)-\d{2}',
            re.IGNORECASE
        )
        if not ps2_pattern.search(basename):
            logging.error("PS2 save filename does not match known KH1 region patterns.")
            self.last_validation_error = "PS2 filename does not match known KH1 region patterns."
            return False
        if len(file_content) != 0x16C00:
            logging.error(
                "PS2 save length mismatch. Expected 0x16C00 bytes, got 0x%X bytes.",
                len(file_content)
            )
            self.last_validation_error = "PS2 save length mismatch (expected 0x16C00 bytes)."
            return False
        if len(file_content) < 0x2404 or file_content[0x2400:0x2404] != b"GUMI":
            logging.error("PS2 save does not contain a GUMI header at offset 0x2400.")
            self.last_validation_error = "PS2 save does not contain a GUMI header at offset 0x2400."
            return False

        return True

    def save_changes(self, file_path):
        try:
            with open(file_path, 'r+b') as save_file:
                # Write all loaded GUMI contents using their stored offsets
                for save_number, gumi_offset in self.gumi_offsets.items():
                    content = self.gumi_contents.get(save_number)
                    if content is None:
                        continue
                    save_file.seek(gumi_offset)
                    save_file.write(content)
            return True
        except Exception as e:
            logging.error(f"Error saving changes: {e}")
            return False

    def find_gumi_header(self, file_content, file_path):
        """
        Find all GUMI header offsets in the save file.
        Returns:
            list of tuples: Each tuple contains (save_number, gumi_header_offset)
        """
        gumi_locations = []
        # Find all occurrences of 'BISLPS-25198-' followed by two digits
        if isinstance(file_content, (bytes, bytearray)):
            pattern = re.compile(br'BISLPS-25198-\d{2}')
        else:
            pattern = re.compile(r'BISLPS-25198-\d{2}')
        bislps_locations = [match.start() for match in pattern.finditer(file_content)]
        for loc in bislps_locations:
            logging.debug(f"Found BISLPS pattern at offset {hex(loc)}")

        if bislps_locations:
            logging.info(f"Multiple save entries found: {len(bislps_locations)}")
            decrypted_entries = getValidSaveEntries(file_content)
            logging.debug(f"Decrypted {len(decrypted_entries)} entries.")
            for entry in decrypted_entries:
                name = entry.get("name", "")
                save_number = name[-2:]
                entry_index = entry.get("index")
                if entry_index is None:
                    continue
                # KH1FM PC Port Save Data Offsets:
                # 0x10D30 = offset of first save entry; 0x16C40 = length of each save entry;
                # 0x2400 = offset of the GUMI header within the save file.
                gumi_header_offset = 0x10D30 + entry_index * 0x16C40 + 0x2400
                gumi_locations.append((save_number, gumi_header_offset))
                logging.debug(f"Valid save entry: Save {save_number}, GUMI Offset {hex(gumi_header_offset)}")
        else:
            logging.info("No BISLPS patterns found. Checking for single GUMI header.")
            for i in range(len(file_content) - 4):
                if file_content[i:i+4] == b'GUMI':
                    basename = os.path.basename(file_path)
                    # Prefer BISLPS-25198-XX style, otherwise fall back to last 2 digits in the name.
                    match = re.search(r'BISLPS-25198-(\d{2})', basename)
                    if not match:
                        match = re.search(r'(\d{2})\D*$', basename)
                    save_number = match.group(1) if match else "01"
                    gumi_locations.append((save_number, i))
                    logging.debug(f"Found single GUMI header at offset {hex(i)} with save number {save_number}")
                    break

        if not gumi_locations:
            logging.error("No GUMI headers found in the save file.")
        return gumi_locations  # Returns a list of (save_number, gumi_header_offset)

    def prompt_save_selection(self, save_numbers):
        """
        Prompt the user to choose a save slot when multiple are available.
        Returns the selected save number string or None.
        """
        if not save_numbers:
            return None
        options_text = ", ".join(save_numbers)
        prompt = f"Multiple saves found. Enter one of: {options_text}"
        selection = simpledialog.askstring("Select Save Slot", prompt)
        if selection in save_numbers:
            return selection
        messagebox.showerror("Invalid Selection", "Invalid save slot selected.")
        return None

    def list_available_blueprints(self):
        if len(self.gumi_contents[self.current_save_number]) > 0:
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
            if blueprint_offset < len(self.gumi_contents[self.current_save_number]) and len(self.gumi_contents[self.current_save_number]) >= (blueprint_offset + BLUEPRINT_DATA_SIZE):
                blueprint_data = self.gumi_contents[self.current_save_number][blueprint_offset:blueprint_offset + BLUEPRINT_DATA_SIZE]
                if blueprint_data[0] == 0x00:  # Empty blueprint
                    return None
                return blueprint_data
            return None
        except Exception as e:
            logging.error(f"Error extracting blueprint data: {e}")
            return None

    def get_selected_blueprint(self):
        """Returns the currently selected blueprint slot based on the byte at the blueprint selection offset."""
        if len(self.gumi_contents[self.current_save_number]) > BLUEPRINT_SELECTION_OFFSET:
            return self.gumi_contents[self.current_save_number][BLUEPRINT_SELECTION_OFFSET] + 1  # Convert 0-9 to 1-10
        return None

    def set_selected_blueprint(self, blueprint_number):
        """Sets the currently selected blueprint slot."""
        if 1 <= blueprint_number <= 10:
            self.gumi_contents[self.current_save_number][BLUEPRINT_SELECTION_OFFSET] = blueprint_number - 1    # Convert 1-10 to 0-9
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

    def set_gummi_sys_com_levels(self, gumi_content):
        system_gummi_offsets = Gummi_Block_Info.system_gummis  # Dictionary containing offset locations

        # Iterate over the stored offsets and set the corresponding bytes to 0x01
        for offset in system_gummi_offsets.values():
            target_offset = INVENTORY_OFFSET_START + offset  # Adjust based on inventory start
            gumi_content[target_offset] = 0x01  # Set byte to 0x01


    def add_required_gummi_blocks(self, include_chest=False, include_design=False):
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

            if gummi_type == "Chest" and not include_chest:
                continue  # Skip if Chest Gummis are not selected

            if gummi_type == "Design" and not include_design:
                continue  # Skip if Design Gummis are not selected

            if gummi_type == "Chest+Design" and not (include_chest and include_design):
                continue  # Requires both Chest and Design to be selected

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

    def add_required_gummi_blocks_all(self, include_chest=False, include_design=False):
        """Add required Gummi Blocks to inventory for all blueprints in the save."""
        any_blueprint = False
        for blueprint_number in range(1, 11):
            blueprint_data = self.extract_blueprint_data(blueprint_number)
            if not blueprint_data:
                continue
            any_blueprint = True
            required_gummi_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)
            for gummi_id, required_count in required_gummi_counts.items():
                gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)

                if gummi_type == "Chest" and not include_chest:
                    continue
                if gummi_type == "Design" and not include_design:
                    continue
                if gummi_type == "Chest+Design" and not (include_chest and include_design):
                    continue

                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, self.gumi_content)
                if gummi_offset is None:
                    continue

                current_quantity = self.gumi_content[gummi_offset]
                max_quantity = Gummi_Block_Info.max_gummi_counts.get(gummi_id, 1)
                new_quantity = required_count if current_quantity < required_count else current_quantity
                self.gumi_content[gummi_offset] = max(0, min(new_quantity, max_quantity))

        if not any_blueprint:
            messagebox.showerror("No Blueprints", "No blueprints found to calculate required Gummi blocks.")
            return False

        return True

class GummiBlueprintView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller

        self.root.title("KH1 Gummi Manager")
        self.root.geometry("720x560")

        self.save_tabs = {}
        self.save_notebook = None

        self.current_save_label = None
        self.sys_up_label = None
        self.current_ship_label = None
        self.com_lvl_label = None
        self.default_label_bg = None

        self.setup_ui()

    def setup_ui(self):
        logging.debug("Setting up UI elements.")
        
        load_button_frame = tk.Frame(self.root)
        load_button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=6)

        load_button = tk.Button(load_button_frame, text="Load Save File", command=self.controller.load_save_file)
        load_button.pack(side=tk.LEFT, pady=6)
        self.attach_tooltip(
            load_button,
            "Open a KH1 save file (.png archive or PS2 save) and load its GUMI data.\n"
            "On load, all blueprints are automatically downscaled to the smallest usable Blueprint Area.",
            position="below"
        )

        save_changes_button = tk.Button(load_button_frame, text="Save Changes", command=self.controller.save_changes)
        save_changes_button.pack(side=tk.LEFT, pady=6)
        self.attach_tooltip(
            save_changes_button,
            "Write your changes (including Current Ship selection) back to the save file.",
            position="below"
        )

        self.manual_ship_var = tk.BooleanVar(
            value=bool(self.controller.preferences.get("manual_current_ship_popup", False))
        )
        manual_ship_check = tk.Checkbutton(
            load_button_frame,
            text="Set Current Ship Manually (Popup Window)",
            variable=self.manual_ship_var,
            command=self.controller.on_manual_ship_toggle
        )
        manual_ship_check.pack(side=tk.LEFT, padx=10, pady=6)
        self.attach_tooltip(
            manual_ship_check,
            "If checked, a popup will appear when saving so you can choose the current ship.\n"
            "If unchecked, the first flyable ship will be selected automatically.",
            position="below"
        )

        self.result_frame = tk.Frame(load_button_frame)
        self.result_frame.pack(side=tk.RIGHT, pady=2)

        save_box = tk.LabelFrame(self.result_frame, text="Save File", padx=6, pady=2)
        save_box.pack(side=tk.RIGHT)

        self.current_save_label = tk.Label(save_box, text="")
        self.current_save_label.pack()

        self.default_label_bg = self.root.cget("bg")

        self.save_notebook = ttk.Notebook(self.root)
        self.save_notebook.pack(fill='both', expand=True)
        self.save_notebook.bind("<<NotebookTabChanged>>", self.controller.on_save_tab_changed)

        logging.debug("UI setup complete.")

    def _hide_global_tooltip(self):
        tip = getattr(self, "_global_tooltip_window", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
        self._global_tooltip_window = None

    def _show_global_tooltip(self, widget, text, x, y):
        self._hide_global_tooltip()
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tip,
            text=text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal")
        )
        label.pack(ipadx=6, ipady=3)
        self._global_tooltip_window = tip

    def attach_tooltip(self, widget, text, position="right_top"):
        """Attach a simple hover tooltip to a widget."""
        def show_tooltip(_event=None):
            if position == "below":
                x = widget.winfo_rootx() + 12
                y = widget.winfo_rooty() + widget.winfo_height() + 6
            elif position == "overlay_bottom":
                x = widget.winfo_rootx() + 12
                y = widget.winfo_rooty() + max(2, widget.winfo_height() - 64)
            else:
                x = widget.winfo_rootx() + widget.winfo_width() + 8
                y = widget.winfo_rooty() + 2
            self._show_global_tooltip(widget, text, x, y)

        def hide_tooltip(_event=None):
            self._hide_global_tooltip()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        widget.bind("<ButtonPress>", hide_tooltip)

    def attach_notebook_tooltips(self, notebook, tooltip_texts):
        """Attach hover tooltips for notebook tabs (ordered list)."""
        if getattr(notebook, "_tooltip_bound", False):
            return
        notebook._tooltip_bound = True

        tooltip = {"index": None}

        def hide(_event=None):
            self._hide_global_tooltip()
            tooltip["index"] = None

        def on_motion(event):
            try:
                index = notebook.index(f"@{event.x},{event.y}")
            except tk.TclError:
                hide()
                return
            if index is None or index >= len(tooltip_texts):
                hide()
                return
            if tooltip["index"] == index:
                return
            tooltip["index"] = index
            x = notebook.winfo_rootx() + event.x + 12
            y = notebook.winfo_rooty() + event.y + 18
            self._show_global_tooltip(notebook, tooltip_texts[index], x, y)

        notebook.bind("<Motion>", on_motion)
        notebook.bind("<Leave>", hide)
        notebook.bind("<ButtonPress>", hide)


class GummiBlueprintController:
    def __init__(self, root):
        self.root = root
        self.data = GummiBlueprintData()  # Model
        self.save_filename = ''
        self.config_path = os.path.join(os.path.dirname(__file__), "gummi_manager_config.json")
        self.preferences = {
            "manual_current_ship_popup": False,
            "include_all_blueprints": True,
            "include_chest": False,
            "include_design": False
        }
        self.suppress_pref_sync = False
        self.original_blueprint_signatures = {}
        self.load_config()

        self.view = GummiBlueprintView(root, self)

        # Mirror view widget refs for minimal churn in controller logic
        self.save_tabs = self.view.save_tabs
        self.save_notebook = self.view.save_notebook
        self.current_save_label = self.view.current_save_label
        self.sys_up_label = self.view.sys_up_label
        self.current_ship_label = self.view.current_ship_label
        self.com_lvl_label = self.view.com_lvl_label
        self.default_label_bg = self.view.default_label_bg

    def attach_tooltip(self, widget, text, position="right_top"):
        return self.view.attach_tooltip(widget, text, position=position)

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    self.preferences.update({k: data.get(k, v) for k, v in self.preferences.items()})
        except Exception as exc:
            logging.warning("Failed to load config: %s", exc)

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as handle:
                json.dump(self.preferences, handle, indent=2)
        except Exception as exc:
            logging.warning("Failed to save config: %s", exc)

    def on_manual_ship_toggle(self):
        if self.view.manual_ship_var is None:
            return
        self.preferences["manual_current_ship_popup"] = bool(self.view.manual_ship_var.get())
        self.save_config()

    def sync_preference(self, key, value, source_save=None):
        if self.suppress_pref_sync:
            return
        self.preferences[key] = bool(value)
        self.save_config()

        self.suppress_pref_sync = True
        try:
            for save_num, ui in self.save_tabs.items():
                if save_num == source_save:
                    continue
                var_key = f"{key}_var"
                if var_key in ui:
                    ui[var_key].set(bool(value))
        finally:
            self.suppress_pref_sync = False

    def rename_blueprint(self, save_number, ui):
        self.set_active_save(save_number)
        selected_index = ui["blueprint_listbox"].curselection()
        if selected_index:
            blueprint_number = int(ui["blueprint_listbox"].get(selected_index[0]).split()[1])
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if not blueprint_data:
                messagebox.showwarning("Empty Blueprint", "This blueprint slot is empty and cannot be renamed.")
                return
            current_name = self.data.decode_blueprint_name(blueprint_data)

            new_name = simpledialog.askstring(
                "Rename Blueprint",
                f"Enter new name for Blueprint {blueprint_number}:",
                initialvalue=current_name
            )
            if new_name:
                success = self.data.rename_blueprint(blueprint_number, new_name)
                if success:
                    self.refresh_blueprint_list(save_number, ui)
                    messagebox.showinfo(
                        "Blueprint Renamed",
                        f"Blueprint {blueprint_number} renamed to '{new_name}' successfully."
                    )
                else:
                    messagebox.showerror("Error", "Failed to rename blueprint.")
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to rename.")

    def import_blueprint_from_save(self, save_number, ui):
        self.set_active_save(save_number)
        if len(self.data.gumi_contents) <= 1:
            messagebox.showwarning(
                "No Other Saves",
                "Only one save is loaded. Importing from another save is unavailable."
            )
            return

        selected_index = ui["blueprint_listbox"].curselection()
        if not selected_index:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint slot to import into.")
            return

        target_blueprint_number = int(ui["blueprint_listbox"].get(selected_index[0]).split()[1])
        options = [sn for sn in self.data.gumi_contents.keys() if sn != save_number]
        if not options:
            messagebox.showwarning(
                "No Other Saves",
                "Only one save is available for import."
            )
            return

        source_save, source_slot = self.prompt_import_from_save_dialog(
            save_number,
            target_blueprint_number,
            options
        )
        if not source_save or source_slot is None:
            return

        original_save = self.data.current_save_number
        try:
            if not self.set_active_save(source_save):
                messagebox.showerror("Error", "Failed to switch to source save.")
                return
            blueprint_data = self.data.extract_blueprint_data(source_slot)
            if not blueprint_data:
                messagebox.showwarning(
                    "Empty Blueprint",
                    f"Source Save {source_save} slot {source_slot} is empty."
                )
                return
        finally:
            self.set_active_save(original_save)

        self.set_active_save(save_number)
        existing_target = self.data.extract_blueprint_data(target_blueprint_number)
        if existing_target:
            confirm = messagebox.askyesno(
                "Overwrite Blueprint?",
                f"Blueprint slot {target_blueprint_number} already contains data.\n"
                "Do you want to overwrite it?"
            )
            if not confirm:
                return
        downscaled = self.downscale_blueprint_data(bytearray(blueprint_data))
        success = self.data.write_blueprint_to_slot(downscaled, target_blueprint_number)
        if success:
            blueprint_data = self.data.extract_blueprint_data(target_blueprint_number)
            if blueprint_data and len(blueprint_data) >= 0x08:
                size_hex = blueprint_data[0x02:0x08].hex().upper()
                logging.info(
                    "Import-from-save wrote blueprint size bytes for slot %d: %s",
                    target_blueprint_number,
                    size_hex
                )
            ui["stats_dirty"] = True
            self.refresh_blueprint_list(save_number, ui)
            ui["blueprint_listbox"].selection_clear(0, tk.END)
            ui["blueprint_listbox"].selection_set(target_blueprint_number - 1)
            ui["blueprint_listbox"].activate(target_blueprint_number - 1)
            ui["blueprint_listbox"].see(target_blueprint_number - 1)
            self.on_blueprint_select(save_number, ui)
            self.update_gummi_stats(
                save_number,
                reason=(
                    f"import from save {source_save} slot {source_slot} -> slot {target_blueprint_number}"
                )
            )
            messagebox.showinfo(
                "Blueprint Imported",
                f"Imported from Save {source_save} slot {source_slot} into slot {target_blueprint_number}."
            )
        else:
            messagebox.showerror("Error", "Failed to import blueprint from save.")

    def prompt_import_from_save_dialog(self, current_save, target_slot, options):
        """Prompt for a source save (dropdown) and source blueprint (listbox)."""
        result = {"save": None, "slot": None}
        dialog = tk.Toplevel(self.root)
        dialog.title("Import From Save")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog_frame = tk.Frame(dialog, padx=10, pady=10)
        dialog_frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(dialog_frame, text="Source Save:")
        label.grid(row=0, column=0, sticky="w")

        source_var = tk.StringVar()
        source_combo = ttk.Combobox(
            dialog_frame,
            textvariable=source_var,
            values=sorted(options),
            state="readonly",
            width=10
        )
        source_combo.grid(row=0, column=1, sticky="w")

        list_label = tk.Label(dialog_frame, text="Source Blueprint:")
        list_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        listbox = tk.Listbox(dialog_frame, width=30, height=10)
        listbox.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(4, 0))

        dialog_frame.grid_rowconfigure(2, weight=1)
        dialog_frame.grid_columnconfigure(1, weight=1)

        preview_label = tk.Label(dialog_frame, text="Selected: (none)")
        preview_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def get_blueprints_for_save(save_num):
            original = self.data.current_save_number
            if not self.set_active_save(save_num):
                return []
            blueprints = self.data.list_available_blueprints()
            self.set_active_save(original)
            return blueprints

        def update_preview():
            save_num = source_var.get()
            selected = listbox.curselection()
            if save_num and selected:
                text = listbox.get(selected[0])
                preview_label.config(text=f"Selected: Save {save_num} / {text}")
            else:
                preview_label.config(text="Selected: (none)")

        def populate_list():
            listbox.delete(0, tk.END)
            save_num = source_var.get()
            if not save_num:
                update_preview()
                return
            for blueprint in get_blueprints_for_save(save_num):
                listbox.insert(tk.END, blueprint)
            if 1 <= target_slot <= listbox.size():
                listbox.selection_set(target_slot - 1)
                listbox.activate(target_slot - 1)
                listbox.see(target_slot - 1)
            update_preview()

        def on_ok():
            save_num = source_var.get()
            if save_num not in options:
                messagebox.showerror("Invalid Selection", "Please choose a source save.")
                return
            selected = listbox.curselection()
            if not selected:
                messagebox.showerror("Invalid Selection", "Please choose a source blueprint slot.")
                return
            result["save"] = save_num
            result["slot"] = selected[0] + 1
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        source_combo.bind("<<ComboboxSelected>>", lambda _e: populate_list())
        listbox.bind("<<ListboxSelect>>", lambda _e: update_preview())
        source_var.set(sorted(options)[0])
        populate_list()

        button_frame = tk.Frame(dialog_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(8, 0), sticky="e")

        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        dialog.wait_window()
        return result["save"], result["slot"]

    def delete_blueprint(self, save_number, ui):
        self.set_active_save(save_number)
        selected_index = ui["blueprint_listbox"].curselection()
        if selected_index:
            blueprint_number = int(ui["blueprint_listbox"].get(selected_index[0]).split()[1])
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if not blueprint_data:
                return
            blueprint_name = self.data.decode_blueprint_name(blueprint_data)

            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {blueprint_name}?")
            if confirm:
                success = self.data.delete_blueprint(blueprint_number)
                if success:
                    ui["stats_dirty"] = True
                    self.refresh_blueprint_list(save_number, ui)
                    self.update_gummi_stats(
                        save_number,
                        reason=f"delete blueprint slot {blueprint_number}"
                    )
                    messagebox.showinfo("Blueprint Deleted", f"{blueprint_name} deleted successfully.")
                else:
                    messagebox.showerror("Error", "Failed to delete blueprint.")
        else:
            messagebox.showwarning("No Blueprint Selected", "Please select a blueprint to delete.")

    def setup_blueprint_tab_for_save(self, save_number, parent_notebook, ui):
        logging.debug("Setting up Blueprint tab for Save %s.", save_number)
        blueprint_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(blueprint_tab, text='Blueprint Manager')

        left_panel = tk.Frame(blueprint_tab, width=198)
        left_panel.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        left_panel.pack_propagate(False)

        info_box = tk.LabelFrame(left_panel, text="Current Ship", padx=6, pady=4)
        info_box.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))
        ui["current_ship_label"] = tk.Label(info_box, text="")
        ui["current_ship_label"].pack(anchor="w")

        syscom_frame = tk.Frame(left_panel)
        syscom_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))
        sys_box = tk.LabelFrame(syscom_frame, text="SYS. UP", padx=6, pady=2)
        com_box = tk.LabelFrame(syscom_frame, text="COM Lvl", padx=6, pady=2)
        sys_box.pack(side=tk.LEFT, padx=(0, 6))
        com_box.pack(side=tk.LEFT)
        ui["sys_up_label"] = tk.Label(sys_box, text="")
        ui["sys_up_label"].pack()
        ui["com_lvl_label"] = tk.Label(com_box, text="")
        ui["com_lvl_label"].pack()
        self.attach_tooltip(
            sys_box,
            "SYS UP level required by the blueprints in this save.\n"
            "\n"
            "SYS UP controls the maximum allowed Blueprint Area for a given blueprint.",
            position="below"
        )
        self.attach_tooltip(
            com_box,
            "COM LVL required by the blueprints in this save.\n"
            "\n"
            "COM LVL upgrades allow you to save more blueprints\n"
            "and build bigger ships.",
            position="below"
        )

        blueprint_frame = tk.Frame(left_panel)
        blueprint_frame.pack(side=tk.TOP, fill=tk.X)

        blueprint_label = tk.Label(blueprint_frame, text="Blueprints in save file:")
        blueprint_label.pack()

        blueprint_listbox = tk.Listbox(blueprint_frame, width=30, height=10)
        blueprint_listbox.pack(side=tk.TOP, expand=False)
        self.attach_tooltip(
            blueprint_listbox,
            "Select a blueprint to view its blocks and stats. Right-click for Rename, Import from Save, or Delete."
        )

        blueprint_listbox.bind(
            "<<ListboxSelect>>",
            lambda event, sn=save_number, u=ui: self.on_blueprint_select(sn, u, event)
        )

        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Rename", command=lambda sn=save_number, u=ui: self.rename_blueprint(sn, u))
        context_menu.add_command(
            label="Import from Save File",
            command=lambda sn=save_number, u=ui: self.import_blueprint_from_save(sn, u)
        )
        context_menu.add_command(label="Delete", command=lambda sn=save_number, u=ui: self.delete_blueprint(sn, u))

        blueprint_listbox.bind(
            "<Button-3>",
            lambda event, sn=save_number, u=ui, cm=context_menu: self.show_context_menu(sn, u, cm, event)
        )

        metrics_frame = tk.LabelFrame(left_panel, text="(No Blueprint Selected)", padx=6, pady=4)
        metrics_frame.pack(side=tk.TOP, fill=tk.X, pady=(6, 8))
        ui["blueprint_metrics_frame"] = metrics_frame
        ui["blueprint_block_count_label"] = tk.Label(metrics_frame, text="Block Count: —", justify=tk.LEFT)
        ui["blueprint_block_count_label"].pack(anchor="w")
        ui["blueprint_bounds_label"] = tk.Label(metrics_frame, text="Ship Size: —", justify=tk.LEFT)
        ui["blueprint_bounds_label"].pack(anchor="w")
        ui["blueprint_size_label"] = tk.Label(metrics_frame, text="Blueprint Area: —", justify=tk.LEFT)
        ui["blueprint_size_label"].pack(anchor="w")

        bottom_controls = tk.Frame(left_panel)
        bottom_controls.pack(side=tk.TOP, fill=tk.X)

        export_button = tk.Button(
            bottom_controls,
            text="Export Blueprint",
            command=lambda sn=save_number, u=ui: self.export_blueprint(sn, u)
        )
        export_button.pack(side=tk.LEFT, padx=(0, 6))
        self.attach_tooltip(
            export_button,
            "Export the selected blueprint to a .kh1blueprint file.",
            position="below"
        )

        import_button = tk.Button(
            bottom_controls,
            text="Import Blueprint",
            command=lambda sn=save_number, u=ui: self.import_blueprint(sn, u)
        )
        import_button.pack(side=tk.LEFT)
        self.attach_tooltip(
            import_button,
            "Import a .kh1blueprint file into the selected slot.\n"
            "Blueprint will be automatically downscaled to the smallest usable Blueprint Area.",
            position="below"
        )

        include_all_blueprints_var = tk.BooleanVar(
            value=bool(self.preferences.get("include_all_blueprints", True))
        )
        include_chest_var = tk.BooleanVar(
            value=bool(self.preferences.get("include_chest", False))
        )
        include_design_var = tk.BooleanVar(
            value=bool(self.preferences.get("include_design", False))
        )

        gummi_frame = tk.Frame(blueprint_tab)
        gummi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        treeview_frame = tk.Frame(gummi_frame)
        treeview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ('Type', 'Gummi Block', 'Required', 'Inventory')
        gummi_treeview = ttk.Treeview(
            treeview_frame,
            columns=columns,
            show='headings',
            height=10,
            selectmode="none"
        )
        self.attach_tooltip(
            gummi_treeview,
            "List of required blocks for the selected blueprint and your inventory counts.\n"
            "\n"
            "Common Gummi blocks are always imported by Add Required Gummi Blocks.\n"
            "Chest and Design Gummi Blocks are imported according to the checkboxes below.",
            position="overlay_bottom"
        )

        gummi_treeview.heading('Type', text='Type')
        gummi_treeview.heading('Gummi Block', text='Gummi Block')
        gummi_treeview.heading('Required', text='Required')
        gummi_treeview.heading('Inventory', text='Inventory')

        gummi_treeview.column('Type', width=80)
        gummi_treeview.column('Gummi Block', width=220)
        gummi_treeview.column('Required', width=70)
        gummi_treeview.column('Inventory', width=70)

        scrollbar_y = ttk.Scrollbar(treeview_frame, orient="vertical", command=gummi_treeview.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        gummi_treeview.configure(yscrollcommand=scrollbar_y.set)

        gummi_treeview.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        gummi_treeview.bind("<<TreeviewSelect>>", lambda _e: gummi_treeview.selection_remove(gummi_treeview.selection()))

        button_frame = tk.Frame(gummi_frame)
        button_frame.pack(side=tk.BOTTOM, pady=10, fill=tk.X)

        center_stack = tk.Frame(button_frame)
        center_stack.pack(side=tk.TOP, anchor="center")

        top_row = tk.Frame(center_stack)
        top_row.pack(side=tk.TOP)

        bottom_row = tk.Frame(center_stack)
        bottom_row.pack(side=tk.TOP, pady=(4, 0))

        add_gummi_button = tk.Button(
            top_row,
            text="Add Required Gummi Blocks",
            command=lambda sn=save_number, u=ui: self.add_required_gummi_blocks(sn, u)
        )
        add_gummi_button.pack(side=tk.TOP, pady=(0, 2))
        self.attach_tooltip(
            add_gummi_button,
            "Adds required Gummi Blocks based on the current settings."
        )

        options_row = tk.Frame(center_stack)
        options_row.pack(side=tk.TOP, pady=(4, 0))

        include_all_blueprints_check = tk.Checkbutton(
            options_row,
            text="Include All Blueprints",
            variable=include_all_blueprints_var
        )
        include_all_blueprints_check.pack(side=tk.LEFT, padx=5)
        self.attach_tooltip(
            include_all_blueprints_check,
            "When checked, Add Required Gummi Blocks will add\n"
            "Gummi Blocks for all custom blueprints in the save.",
            position="below"
        )

        include_chest_check = tk.Checkbutton(options_row, text="Include Chest Gummi", variable=include_chest_var)
        include_chest_check.pack(side=tk.LEFT, padx=5)
        self.attach_tooltip(
            include_chest_check,
            "Include Chest Gummi Blocks. If checked, any Final Mix treasure chests\n"
            "containing these Gummi Blocks may be rendered unobtainable.\n"
            "\n"
            "Chest+Design blocks require both Chest and Design to be checked.",
            position="below"
        )

        include_design_check = tk.Checkbutton(options_row, text="Include Design Gummi", variable=include_design_var)
        include_design_check.pack(side=tk.LEFT, padx=5)
        self.attach_tooltip(
            include_design_check,
            "Include Design Gummi Blocks exclusive to Final Mix. This option\n"
            "is disabled when pre-Final Mix save files are loaded.\n"
            "\n"
            "Chest+Design blocks require both Chest and Design to be checked.",
            position="below"
        )


        ui["blueprint_listbox"] = blueprint_listbox
        ui["gummi_treeview"] = gummi_treeview
        ui["include_all_blueprints_var"] = include_all_blueprints_var
        ui["include_chest_var"] = include_chest_var
        ui["include_design_var"] = include_design_var
        ui["include_design_check"] = include_design_check
        ui["context_menu"] = context_menu

        include_all_blueprints_var.trace_add(
            "write",
            lambda *_a, sn=save_number: self.sync_preference("include_all_blueprints", include_all_blueprints_var.get(), sn)
        )
        include_chest_var.trace_add(
            "write",
            lambda *_a, sn=save_number: self.sync_preference("include_chest", include_chest_var.get(), sn)
        )
        include_design_var.trace_add(
            "write",
            lambda *_a, sn=save_number: self.sync_preference("include_design", include_design_var.get(), sn)
        )

        self.update_design_checkbox_state(save_number, ui)

    def add_required_gummi_blocks(self, save_number, ui):
        """Add required Gummi Blocks to inventory for the selected save."""
        self.set_active_save(save_number)
        include_all = ui["include_all_blueprints_var"].get()
        include_chest = ui["include_chest_var"].get()
        include_design = ui["include_design_var"].get()

        if include_all:
            success = self.data.add_required_gummi_blocks_all(include_chest, include_design)
        else:
            success = self.data.add_required_gummi_blocks(include_chest, include_design)
        if success:
            ui["stats_dirty"] = True
            self.update_gummi_treeview(ui, self.data.blueprint_data, self.data.gumi_content)
            self.refresh_inventory_editor(save_number, ui, log_updates=True)
            messagebox.showinfo("Success", "Required Gummi Blocks have been added to the inventory.")


    def update_gummi_treeview(self, ui, blueprint_data, gumi_content):
        """Update the Treeview with Gummi Block types, names, required counts, and inventory counts."""
        ui["gummi_treeview"].delete(*ui["gummi_treeview"].get_children())  # Clear the treeview
        if not blueprint_data:
            return

        # Get the required Gummi Blocks from the blueprint data
        required_gummi_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)

        # Populate Treeview with Gummi Block information in Gummi_Block_Info order
        ui["gummi_treeview"].tag_configure("missing_common", background="#f6caca")
        ui["gummi_treeview"].tag_configure("missing_special", background="#fff2b3")
        for gummi_id in Gummi_Block_Info.gummi_block_names.keys():
            if gummi_id not in required_gummi_counts:
                continue
            required_count = required_gummi_counts[gummi_id]
            gummi_name = Gummi_Block_Info.gummi_block_names.get(gummi_id)
            if gummi_name:
                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, gumi_content)

                # Log the offset and ID information (guarded to reduce spam)
                if getattr(Gummi_Block_Operations, "VERBOSE_DEBUG", False):
                    logging.debug(
                        f"Processing Gummi ID {gummi_id} ({gummi_name}). "
                        f"Calculated offset: {gummi_offset}"
                    )

                if gummi_offset is not None and 0 <= gummi_offset < len(gumi_content):
                    inventory_count = int.from_bytes(gumi_content[gummi_offset:gummi_offset + 1], byteorder='little')
                else:
                    logging.warning(f"Invalid or out-of-bounds gummi_offset: {gummi_offset} for Gummi ID: {gummi_id}")
                    inventory_count = 0  # Default to 0 if the offset is invalid

                # Determine the Gummi Block type (Common, Chest, Design)
                gummi_type = Gummi_Block_Operations.get_gummi_type(gummi_id)

                # Insert row into Treeview
                tags = ()
                if inventory_count < required_count:
                    if gummi_type == "Common":
                        tags = ("missing_common",)
                    else:
                        tags = ("missing_special",)
                ui["gummi_treeview"].insert(
                    '',
                    'end',
                    values=(gummi_type, gummi_name, required_count, inventory_count),
                    tags=tags
                )

    def on_blueprint_select(self, save_number, ui, event=None):
        """Handles blueprint selection from both left and right mouse clicks."""
        self.set_active_save(save_number)
        selected_index = ui["blueprint_listbox"].curselection()
        if not selected_index:
            return
        blueprint_number = selected_index[0] + 1  # Index 0 -> Blueprint 1
        blueprint_data = self.data.extract_blueprint_data(blueprint_number)
        self.data.blueprint_data = blueprint_data

        if blueprint_data:
            self.update_gummi_treeview(ui, blueprint_data, self.data.gumi_content)
            self.update_blueprint_metrics_ui(ui, blueprint_data)
        else:
            self.update_gummi_treeview(ui, None, self.data.gumi_content)
            self.update_blueprint_metrics_ui(ui, None)

    def show_context_menu(self, save_number, ui, context_menu, event):
        """Display the context menu on right-click and select the clicked blueprint."""
        index = ui["blueprint_listbox"].nearest(event.y)
        ui["blueprint_listbox"].selection_clear(0, tk.END)
        ui["blueprint_listbox"].selection_set(index)
        ui["blueprint_listbox"].activate(index)
        self.on_blueprint_select(save_number, ui)

        blueprint_number = index + 1
        blueprint_data = self.data.extract_blueprint_data(blueprint_number)
        rename_state = tk.NORMAL if blueprint_data else tk.DISABLED
        delete_state = tk.NORMAL if blueprint_data else tk.DISABLED
        context_menu.entryconfig("Rename", state=rename_state)
        context_menu.entryconfig("Delete", state=delete_state)

        import_state = tk.NORMAL if len(self.data.gumi_contents) > 1 else tk.DISABLED
        context_menu.entryconfig("Import from Save File", state=import_state)
        try:
            context_menu.post(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def load_save_file(self):
        file_path = filedialog.askopenfilename(title="Select a Save File", filetypes=[("All Files", "*.*")])
        if not file_path:
            return

        # Clear previous file content
        self.data.file_content = bytearray()
        self.data.gumi_contents = {}
        self.data.gumi_offsets = {}
        self.original_blueprint_signatures = {}

        if file_path and self.data.load_save_file(file_path):
            self.save_filename = file_path
            short_save_filename = os.path.basename(file_path)
            self.current_save_label.config(text=f"{short_save_filename}")
            self.downscale_all_blueprints_in_loaded_saves()
            self.build_save_tabs()
            self.original_blueprint_signatures = {
                save_num: self.get_blueprint_signature(save_num)
                for save_num in self.data.gumi_contents.keys()
            }
        else:
            # Clear labels and reset state if the file load fails
            self.current_save_label.config(text="")
            if self.current_ship_label:
                self.current_ship_label.config(text="")
            if self.sys_up_label:
                self.sys_up_label.config(text="N/A")
            if self.com_lvl_label:
                self.com_lvl_label.config(text="N/A")
            error_message = self.data.last_validation_error or "Save file failed validation."
            messagebox.showerror("Error", error_message)
            self.clear_save_tabs()
            self.original_blueprint_signatures = {}

    def clear_save_tabs(self):
        for tab_id in list(self.save_notebook.tabs()):
            try:
                frame = self.save_notebook.nametowidget(tab_id)
                frame.destroy()
            except Exception:
                self.save_notebook.forget(tab_id)
        self.save_tabs = {}

    def build_save_tabs(self):
        self.clear_save_tabs()
        save_numbers = list(self.data.gumi_contents.keys())
        if not save_numbers:
            return

        def sort_key(value):
            return int(value) if str(value).isdigit() else str(value)

        for save_number in sorted(save_numbers, key=sort_key):
            ui = self.create_save_tab(save_number)
            self.save_tabs[save_number] = ui

        # Select the first tab in display order
        first_save = sorted(save_numbers, key=sort_key)[0]
        self.set_active_save(first_save)
        self.ensure_save_tab_built(first_save, self.save_tabs[first_save])
        selected_blueprint = self.data.get_selected_blueprint()
        self.data.blueprint_data = (
            self.data.extract_blueprint_data(selected_blueprint) if selected_blueprint else None
        )
        if self.save_filename:
            short_save_filename = os.path.basename(self.save_filename)
            self.current_save_label.config(text=f"{short_save_filename} (Save {first_save})")
        self.update_current_ship_label(first_save, self.save_tabs[first_save])
        self.update_design_checkbox_state(first_save, self.save_tabs[first_save])
        self.update_gummi_stats(first_save, force=True, reason="initial load")
        self.update_blueprint_metrics_ui(self.save_tabs[first_save], self.data.blueprint_data)
        self.save_notebook.select(self.save_tabs[first_save]["tab_id"])

    def create_save_tab(self, save_number):
        frame = ttk.Frame(self.save_notebook)
        self.save_notebook.add(frame, text=f"Save {save_number}")

        ui = {
            "tab_id": frame,
            "frame": frame,
            "save_number": save_number,
            "inventory_spinboxes": {},
            "stats_dirty": True,
            "last_sys_level": None,
            "last_sys_reason": None,
            "last_com_level": None,
            "last_com_reason": None,
            "built": False,
        }

        ui["placeholder_label"] = ttk.Label(frame, text="Loading...")
        ui["placeholder_label"].pack(fill="both", expand=True)
        return ui

    def ensure_save_tab_built(self, save_number, ui):
        if ui.get("built"):
            return
        placeholder = ui.get("placeholder_label")
        if placeholder:
            placeholder.destroy()
            ui["placeholder_label"] = None
        notebook = ttk.Notebook(ui["frame"])
        notebook.pack(fill='both', expand=True)
        ui["notebook"] = notebook

        self.setup_blueprint_tab_for_save(save_number, notebook, ui)
        self.setup_inventory_tabs_for_save(save_number, notebook, ui)
        ui["built"] = True

        self.view.attach_notebook_tooltips(
            notebook,
            [
                "Manage blueprints: list, import/export, and required blocks.",
                "Edit quantities of Gummi Blocks in the save.",
                "Manage collection of prebuilt Gummi Ship blueprints.",
                "Edit Gummi Ship control bindings.",
            ]
        )

        self.refresh_blueprint_list(save_number, ui)
        self.refresh_inventory_editor(save_number, ui, log_updates=False)
        logging.info("Initial inventory loaded for Save %s.", save_number)

    def downscale_all_blueprints_in_loaded_saves(self):
        """Apply blueprint downscaler to all populated blueprints after loading a save file."""
        total_changed = 0
        saves_changed = 0
        for save_number, gumi_content in self.data.gumi_contents.items():
            any_changed = False
            for blueprint_number, offset in self.data.blueprint_offsets.items():
                end = offset + BLUEPRINT_DATA_SIZE
                if end > len(gumi_content):
                    continue
                blueprint_data = gumi_content[offset:end]
                if not blueprint_data or blueprint_data[0] == 0:
                    continue
                downscaled = self.downscale_blueprint_data(bytearray(blueprint_data))
                if downscaled and downscaled != blueprint_data:
                    gumi_content[offset:end] = downscaled
                    any_changed = True
                    total_changed += 1
                else:
                    name = self.data.decode_blueprint_name(blueprint_data) if blueprint_data else ""
                    if not name:
                        name = "Unnamed Blueprint"
                    logging.debug("Downscaler pass-through (no change) for %s.", name)
            if any_changed:
                ui = self.save_tabs.get(save_number)
                if ui:
                    ui["stats_dirty"] = True
                saves_changed += 1
        logging.info(
            "Downscale on load: %d blueprint%s adjusted across %d save%s.",
            total_changed,
            "" if total_changed == 1 else "s",
            saves_changed,
            "" if saves_changed == 1 else "s"
        )

    def set_active_save(self, save_number):
        if save_number not in self.data.gumi_contents:
            logging.warning("Save number %s not found in loaded contents.", save_number)
            return False
        self.data.current_save_number = save_number
        self.data.gumi_content = self.data.gumi_contents[save_number]
        self.current_save_number = save_number
        return True

    def normalize_save_number(self, label):
        if label.startswith("Save "):
            return label.replace("Save ", "", 1).strip()
        return label.strip()

    def is_final_mix_save(self, save_number):
        """Best-effort check for Final Mix saves to gate Design Gummi UI."""
        if not self.save_filename:
            return False
        basename = os.path.basename(self.save_filename).upper()
        if basename.endswith(".PNG"):
            return True  # PC KHFM PNG archive
        if "BISLPS-25198" in basename:
            return True  # PS2 KHFM JP
        return False

    def update_design_checkbox_state(self, save_number, ui):
        if not ui:
            return
        include_design_var = ui.get("include_design_var")
        include_design_check = ui.get("include_design_check")
        if include_design_var is None or include_design_check is None:
            return
        is_final_mix = self.is_final_mix_save(save_number)
        if is_final_mix:
            include_design_check.config(state=tk.NORMAL)
            return
        # Non-FM: force off without syncing preferences
        self.suppress_pref_sync = True
        try:
            include_design_var.set(False)
        finally:
            self.suppress_pref_sync = False
        include_design_check.config(state=tk.DISABLED)

    def get_ship_controls_base_offset(self, save_number):
        """Return the base offset for ship controls depending on save type."""
        if self.is_final_mix_save(save_number):
            return 0x9B40
        return 0x9B00

    def on_save_tab_changed(self, event=None):
        selected = self.save_notebook.select()
        if not selected:
            return
        save_label = self.save_notebook.tab(selected, "text")
        save_number = self.normalize_save_number(save_label)
        ui = self.save_tabs.get(save_number)
        if not ui:
            return
        self.ensure_save_tab_built(save_number, ui)
        if not self.set_active_save(save_number):
            return
        selected_blueprint = self.data.get_selected_blueprint()
        self.data.blueprint_data = (
            self.data.extract_blueprint_data(selected_blueprint) if selected_blueprint else None
        )
        if self.save_filename:
            short_save_filename = os.path.basename(self.save_filename)
            self.current_save_label.config(text=f"{short_save_filename} (Save {save_number})")
        self.refresh_blueprint_list(save_number, ui)
        self.update_current_ship_label(save_number, ui)
        self.update_design_checkbox_state(save_number, ui)
        self.update_gummi_stats(save_number, force=True, reason="tab change")
        self.update_gummi_treeview(ui, self.data.blueprint_data, self.data.gumi_content)
        self.refresh_inventory_editor(save_number, ui, log_updates=False)
        self.update_blueprint_metrics_ui(ui, self.data.blueprint_data)


    def prompt_save_selection(self, save_numbers):
        """
        Prompt the user to select a save entry when multiple are found.
        
        Args:
            save_numbers (list): List of save numbers available.
        
        Returns:
            str or None: The selected save number, or None if canceled.
        """
        from tkinter import simpledialog, messagebox
    
        if not save_numbers:
            return None
    
        # Create a dialog for the user to select a save entry
        dialog = simpledialog.askstring(
            "Select Save",
            f"Multiple save entries found. Please enter the save number to load ({', '.join(save_numbers)}):",
            parent=self.root
        )
    
        if dialog and dialog in save_numbers:
            logging.debug(f"User selected Save {dialog}")
            return dialog
        else:
            messagebox.showerror("Invalid Selection", "Invalid selection. Please try again.")
            logging.warning("User made an invalid selection for save entry.")
            return None

    def update_gummi_stats(self, current_save_number=None, force=False, reason=None):
        """Updates the Sys. Up and COM Lvl labels based on gumi_content values."""
        if current_save_number is None:
            current_save_number = self.data.current_save_number
        if current_save_number not in self.data.gumi_contents:
            return
        ui = self.save_tabs.get(current_save_number)
        if ui and not force and not ui.get("stats_dirty", True):
            return
        sys_label = ui.get("sys_up_label") if ui else None
        com_label = ui.get("com_lvl_label") if ui else None
        if sys_label is None:
            sys_label = self.sys_up_label
        if com_label is None:
            com_label = self.com_lvl_label
        if reason:
            if VERBOSE_STATS_REASON:
                selected = self.data.get_selected_blueprint()
                details = "no selected blueprint"
                if selected:
                    selected_data = self.data.extract_blueprint_data(selected)
                    if selected_data:
                        counts = Gummi_Block_Operations.count_gummi_blocks(selected_data)
                        engines = sum(counts.get(gid, 0) for gid in Gummi_Block_Info.engine_gummis)
                        weapons = sum(counts.get(gid, 0) for gid in Gummi_Block_Info.weapon_gummis)
                        blocks = selected_data[0]
                        details = f"selected slot {selected}: blocks={blocks}, engines={engines}, weapons={weapons}"
                logging.debug(
                    "Recomputing SYS UP / COM LVL for Save %s (reason: %s, %s).",
                    current_save_number,
                    reason,
                    details
                )
            else:
                logging.debug(
                    "Recomputing SYS UP / COM LVL for Save %s (reason: %s).",
                    current_save_number,
                    reason
                )
        else:
            logging.debug("Recomputing SYS UP / COM LVL for Save %s.", current_save_number)

        # Show checking state while recomputing
        if sys_label:
            sys_label.config(text="checking...", bg=self.default_label_bg)
        if com_label:
            com_label.config(text="checking...", bg=self.default_label_bg)
        self.root.update_idletasks()

        gumi_content = self.data.gumi_contents[current_save_number]
        sys_up_1_offset = 0x9ABA
        sys_up_2_offset = 0x9ABB
        com_lvl_1_offset = 0x9ABC
        com_lvl_2_offset = 0x9ABD
        com_lvl_3_offset = 0x9ABE

        has_size_0a = False
        has_size_08 = False
        sys_reason_0a = None
        sys_reason_08 = None
        populated_slots_2_5 = False
        populated_slots_6_10 = False
        com3_rule = False
        com2_rule = False
        com3_reason = None
        com2_reason = None

        for blueprint_number in range(1, 11):
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if not blueprint_data:
                continue

            if 2 <= blueprint_number <= 5:
                populated_slots_2_5 = True
            if 6 <= blueprint_number <= 10:
                populated_slots_6_10 = True

            size_bytes = blueprint_data[0x02:0x08]
            size_hex = size_bytes.hex().upper()
            size_values = ()
            if len(blueprint_data) >= 0x08:
                try:
                    size_values = struct.unpack_from("<3H", blueprint_data, 0x02)
                except struct.error:
                    size_values = ()

            if size_values == (0x000A, 0x000A, 0x000A):
                has_size_0a = True
                if not sys_reason_0a:
                    sys_reason_0a = f"slot {blueprint_number}, size=0A ({size_hex})"
            elif size_values == (0x0008, 0x0008, 0x0008):
                has_size_08 = True
                if not sys_reason_08:
                    sys_reason_08 = f"slot {blueprint_number}, size=08 ({size_hex})"

            block_count = blueprint_data[0]
            required_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)
            engine_count = sum(required_counts.get(gid, 0) for gid in Gummi_Block_Info.engine_gummis)
            weapon_count = sum(required_counts.get(gid, 0) for gid in Gummi_Block_Info.weapon_gummis)

            if block_count > 150 or engine_count > 4 or weapon_count > 6:
                com3_rule = True
                if not com3_reason:
                    com3_reason = (
                        f"slot {blueprint_number}, blocks={block_count}, "
                        f"engines={engine_count}, weapons={weapon_count}"
                    )
            if block_count > 100 or engine_count > 2 or weapon_count > 4:
                com2_rule = True
                if not com2_reason:
                    com2_reason = (
                        f"slot {blueprint_number}, blocks={block_count}, "
                        f"engines={engine_count}, weapons={weapon_count}"
                    )

        if has_size_0a:
            sys_level = 2
            sys_reason = sys_reason_0a or "unknown slot"
            gumi_content[sys_up_2_offset] = 0x01
            gumi_content[sys_up_1_offset] = 0x01
            if sys_label:
                sys_label.config(text="SYS UP: 2", bg="#cfe8ff")
        elif has_size_08:
            sys_level = 1
            sys_reason = sys_reason_08 or "unknown slot"
            gumi_content[sys_up_1_offset] = 0x01
            gumi_content[sys_up_2_offset] = 0x00
            if sys_label:
                sys_label.config(text="SYS UP: 1", bg="#d8f5d0")
        else:
            sys_level = 0
            sys_reason = None
            gumi_content[sys_up_1_offset] = 0x00
            gumi_content[sys_up_2_offset] = 0x00
            if sys_label:
                sys_label.config(text="SYS UP: 0", bg=self.default_label_bg)

        if populated_slots_6_10 or com3_rule:
            com_level = 3
            gumi_content[com_lvl_3_offset] = 0x01
            gumi_content[com_lvl_2_offset] = 0x01
            gumi_content[com_lvl_1_offset] = 0x01
            if com_label:
                com_label.config(text="COM LVL: 3", bg="#cfe8ff")
            com_reason = "slots 6-10 populated" if populated_slots_6_10 else (com3_reason or "unknown slot")
        elif populated_slots_2_5 or com2_rule:
            com_level = 2
            gumi_content[com_lvl_2_offset] = 0x01
            gumi_content[com_lvl_3_offset] = 0x00
            gumi_content[com_lvl_1_offset] = 0x01
            if com_label:
                com_label.config(text="COM LVL: 2", bg="#d8f5d0")
            com_reason = "slots 2-5 populated" if populated_slots_2_5 else (com2_reason or "unknown slot")
        else:
            com_level = 1
            gumi_content[com_lvl_1_offset] = 0x01
            gumi_content[com_lvl_2_offset] = 0x00
            gumi_content[com_lvl_3_offset] = 0x00
            if com_label:
                com_label.config(text="COM LVL: 1", bg=self.default_label_bg)
            com_reason = None

        if ui:
            if ui.get("last_sys_level") != sys_level or ui.get("last_sys_reason") != sys_reason:
                if sys_level == 2:
                    logging.debug("SYS UP:2 triggered (size 0A) via %s.", sys_reason)
                elif sys_level == 1:
                    logging.debug("SYS UP:1 triggered (size 08) via %s.", sys_reason)
                else:
                    logging.debug("SYS UP:0 triggered (no size conditions met).")
                ui["last_sys_level"] = sys_level
                ui["last_sys_reason"] = sys_reason

            if ui.get("last_com_level") != com_level or ui.get("last_com_reason") != com_reason:
                if com_level == 3:
                    logging.debug(
                        "COM LVL:3 triggered (>150 blocks / >4 engines / >6 weapons or slots 6-10) via %s.",
                        com_reason or "unknown slot"
                    )
                elif com_level == 2:
                    logging.debug(
                        "COM LVL:2 triggered (>100 blocks / >2 engines / >4 weapons or slots 2-5) via %s.",
                        com_reason or "unknown slot"
                    )
                else:
                    logging.debug("COM LVL:1 triggered (no higher-level conditions met).")
                ui["last_com_level"] = com_level
                ui["last_com_reason"] = com_reason

            ui["stats_dirty"] = False

    def update_current_ship_label(self, save_number, ui):
        """Update the label to show the currently selected ship."""
        self.set_active_save(save_number)
        selected_blueprint_number = self.data.get_selected_blueprint()
        label = ui.get("current_ship_label") if ui else None
        if label is None:
            label = self.current_ship_label
        if selected_blueprint_number:
            blueprint_data = self.data.extract_blueprint_data(selected_blueprint_number)
            if blueprint_data and self.is_flyable_blueprint(blueprint_data):
                blueprint_name = self.data.decode_blueprint_name(blueprint_data)
                if label:
                    label.config(text=f"Save {save_number}: #{selected_blueprint_number} - {blueprint_name}")

    def update_blueprint_metrics_ui(self, ui, blueprint_data):
        block_label = ui.get("blueprint_block_count_label") if ui else None
        bounds_label = ui.get("blueprint_bounds_label") if ui else None
        size_label = ui.get("blueprint_size_label") if ui else None
        frame = ui.get("blueprint_metrics_frame") if ui else None
        if not block_label or not bounds_label or not size_label:
            return
        if not blueprint_data:
            block_label.config(text="Block Count: 0")
            bounds_label.config(text="Ship Size: —")
            size_label.config(text="Blueprint Area: —")
            if frame:
                frame.config(text="(No Blueprint Selected)")
            return

        name = self.data.decode_blueprint_name(blueprint_data)
        if not name:
            name = "Unnamed Blueprint"
        if frame:
            frame.config(text=f"{name}:")
        block_count = blueprint_data[0]
        bounds = self.calculate_blueprint_bounds(blueprint_data)
        if bounds:
            width, height, depth = bounds
            bounds_text = f"Ship Size: {width}x{height}x{depth}"
        else:
            bounds_text = "Ship Size: —"

        size_text = "Blueprint Area: —"
        if len(blueprint_data) >= 0x08:
            try:
                size_values = struct.unpack_from("<3H", blueprint_data, 0x02)
                size_text = f"Blueprint Area: {size_values[0]}x{size_values[1]}x{size_values[2]}"
            except struct.error:
                pass

        block_label.config(text=f"Block Count: {block_count}")
        bounds_label.config(text=bounds_text)
        size_label.config(text=size_text)

    def calculate_blueprint_bounds(self, blueprint_data):
        block_count = blueprint_data[0] if blueprint_data else 0
        if block_count == 0:
            return None
        blocks_start = 0x6C
        blocks_end = blocks_start + block_count * 12
        if blocks_end > len(blueprint_data):
            return None

        min_fb = 999
        max_fb = -1
        min_tb = 999
        max_tb = -1
        min_ps = 999
        max_ps = -1

        for i in range(block_count):
            blk = blueprint_data[blocks_start + i * 12:blocks_start + (i + 1) * 12]
            byte0 = blk[0]
            byte1 = blk[1]
            byte2 = blk[2]
            byte3 = blk[3]
            fb = byte1 & 0x0F
            tb = (byte0 >> 4) & 0x0F
            ps = byte0 & 0x0F
            gummi_id = blk[4]
            size_ps, size_tb, size_fb = self.get_oriented_block_size(gummi_id, byte2, byte3)

            min_fb = min(min_fb, fb)
            min_tb = min(min_tb, tb)
            min_ps = min(min_ps, ps)
            max_fb = max(max_fb, fb + size_fb - 1)
            max_tb = max(max_tb, tb + size_tb - 1)
            max_ps = max(max_ps, ps + size_ps - 1)

        width = max_ps - min_ps + 1
        height = max_tb - min_tb + 1
        depth = max_fb - min_fb + 1
        return width, height, depth

    def is_flyable_blueprint(self, blueprint_data):
        if not blueprint_data:
            return False
        required_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)
        has_cockpit = any(required_counts.get(gid, 0) > 0 for gid in Gummi_Block_Info.cockpit_gummis)
        has_engine = any(required_counts.get(gid, 0) > 0 for gid in Gummi_Block_Info.engine_gummis)
        if not has_cockpit or not has_engine:
            return False

        gumi_content = self.data.gumi_content
        if gumi_content is None:
            return False

        def inventory_count(gid):
            offset = Gummi_Block_Operations.calculate_gummi_offset(gid, gumi_content)
            if offset is None or offset < 0 or offset >= len(gumi_content):
                return 0
            return int.from_bytes(gumi_content[offset:offset + 1], byteorder="little")

        cockpit_available = any(
            required_counts.get(gid, 0) > 0 and inventory_count(gid) > 0
            for gid in Gummi_Block_Info.cockpit_gummis
        )

        engine_available = any(
            required_counts.get(gid, 0) > 0 and inventory_count(gid) > 0
            for gid in Gummi_Block_Info.engine_gummis
        )

        return cockpit_available and engine_available

    def get_flyable_issue(self, blueprint_data):
        if not blueprint_data or blueprint_data[0] == 0x00:
            return "Blueprint is empty."
        required_counts = Gummi_Block_Operations.count_gummi_blocks(blueprint_data)
        has_cockpit = any(required_counts.get(gid, 0) > 0 for gid in Gummi_Block_Info.cockpit_gummis)
        has_engine = any(required_counts.get(gid, 0) > 0 for gid in Gummi_Block_Info.engine_gummis)

        if not has_cockpit and not has_engine:
            return "Blueprint does not have a cockpit or engine."
        if not has_cockpit:
            return "Blueprint does not have a cockpit."
        if not has_engine:
            return "Blueprint does not have an engine."

        gumi_content = self.data.gumi_content
        if gumi_content is None:
            return "Gummi inventory data is unavailable."

        def inventory_count(gid):
            offset = Gummi_Block_Operations.calculate_gummi_offset(gid, gumi_content)
            if offset is None or offset < 0 or offset >= len(gumi_content):
                return 0
            return int.from_bytes(gumi_content[offset:offset + 1], byteorder="little")

        cockpit_available = any(
            required_counts.get(gid, 0) > 0 and inventory_count(gid) > 0
            for gid in Gummi_Block_Info.cockpit_gummis
        )
        if not cockpit_available:
            return "Required cockpit gummi is not present in Gummi Inventory."

        engine_available = any(
            required_counts.get(gid, 0) > 0 and inventory_count(gid) > 0
            for gid in Gummi_Block_Info.engine_gummis
        )
        if not engine_available:
            return "Required engine gummi is not present in Gummi Inventory."

        return "Blueprint is not flyable."

    def save_changes(self):
        if self.save_filename:
            if not self.prepare_current_ship_for_save():
                return
            if self.data.save_changes(self.save_filename):
                messagebox.showinfo("Success", "Changes saved successfully.")
            else:
                messagebox.showerror("Save Error", "Failed to save changes.")
        else:
            messagebox.showerror("Invalid File Path", "No save file loaded.")

    def prepare_current_ship_for_save(self):
        current_save = self.data.current_save_number
        if not current_save:
            return True

        manual_popup = bool(self.preferences.get("manual_current_ship_popup", False))
        if manual_popup:
            original_save = current_save
            signatures = {sn: self.get_blueprint_signature(sn) for sn in self.data.gumi_contents.keys()}
            for save_num in self.data.gumi_contents.keys():
                if save_num != original_save and signatures.get(save_num) == self.original_blueprint_signatures.get(save_num):
                    continue

                if not self.set_active_save(save_num):
                    continue

                selection = self.prompt_current_ship_popup(save_num)
                if selection is None:
                    self.set_active_save(original_save)
                    return False
                self.data.set_selected_blueprint(selection)
                if save_num == original_save:
                    ui = self.save_tabs.get(save_num)
                    if ui:
                        self.update_current_ship_label(save_num, ui)

            self.set_active_save(original_save)
            return True

        original_save = current_save
        no_flyable = []
        signatures = {sn: self.get_blueprint_signature(sn) for sn in self.data.gumi_contents.keys()}
        for save_num in self.data.gumi_contents.keys():
            if signatures.get(save_num) == self.original_blueprint_signatures.get(save_num):
                continue
            if not self.set_active_save(save_num):
                continue
            first_flyable = self.find_first_flyable_blueprint()
            if first_flyable is None:
                no_flyable.append(save_num)
                continue
            self.data.set_selected_blueprint(first_flyable)
            if save_num == original_save:
                ui = self.save_tabs.get(save_num)
                if ui:
                    self.update_current_ship_label(save_num, ui)

        self.set_active_save(original_save)
        if no_flyable:
            messagebox.showwarning(
                "No Flyable Ships",
                "No flyable blueprints were found for: " + ", ".join(sorted(no_flyable)) +
                ". Current ship selection was not changed for those saves."
            )
        return True

    def get_blueprint_signature(self, save_number):
        content = self.data.gumi_contents.get(save_number)
        if not content:
            return b""
        signature = bytearray()
        for slot in range(1, 11):
            offset = self.data.blueprint_offsets.get(slot)
            if offset is None:
                signature.extend(b"\x00" * BLUEPRINT_DATA_SIZE)
                continue
            end = offset + BLUEPRINT_DATA_SIZE
            if end <= len(content):
                block = bytearray(content[offset:end])
                name_start = BLUEPRINT_NAME_OFFSET_START
                name_end = BLUEPRINT_NAME_OFFSET_END
                if 0 <= name_start < len(block) and 0 <= name_end <= len(block):
                    for i in range(name_start, name_end):
                        block[i] = 0x00
                signature.extend(block)
            else:
                signature.extend(b"\x00" * BLUEPRINT_DATA_SIZE)
        return bytes(signature)

    def downscale_blueprint_data(self, blueprint_data):
        if not blueprint_data:
            return blueprint_data

        block_count = blueprint_data[0]
        if block_count == 0:
            return blueprint_data

        blocks_start = 0x6C
        blocks_end = blocks_start + block_count * 12
        if blocks_end > len(blueprint_data):
            return blueprint_data

        min_fb = 999
        max_fb = -1
        min_tb = 999
        max_tb = -1
        min_ps = 999
        max_ps = -1
        min_fb_block = None
        max_fb_block = None
        min_tb_block = None
        max_tb_block = None
        min_ps_block = None
        max_ps_block = None
        max_raw_fb = -1
        max_raw_tb = -1
        max_raw_ps = -1

        cockpit_blocks = []
        for i in range(block_count):
            blk = blueprint_data[blocks_start + i * 12:blocks_start + (i + 1) * 12]
            byte0 = blk[0]
            byte1 = blk[1]
            byte2 = blk[2]
            byte3 = blk[3]
            fb = byte1 & 0x0F
            tb = (byte0 >> 4) & 0x0F
            ps = byte0 & 0x0F
            gummi_id = blk[4]
            size = self.get_oriented_block_size(gummi_id, byte2, byte3)
            size_ps, size_tb, size_fb = size

            name = Gummi_Block_Info.gummi_block_names.get(gummi_id, f"GID 0x{gummi_id:02X}")
            if gummi_id in Gummi_Block_Info.cockpit_gummis:
                cockpit_blocks.append((ps, tb, fb, size_ps, size_tb, size_fb))

            if fb < min_fb:
                min_fb = fb
                min_fb_block = (i, name, ps, tb, fb, size)
            if fb > max_raw_fb:
                max_raw_fb = fb
            if fb + size_fb - 1 > max_fb:
                max_fb = fb + size_fb - 1
                max_fb_block = (i, name, ps, tb, fb, size)
            if tb < min_tb:
                min_tb = tb
                min_tb_block = (i, name, ps, tb, fb, size)
            if tb > max_raw_tb:
                max_raw_tb = tb
            if tb + size_tb - 1 > max_tb:
                max_tb = tb + size_tb - 1
                max_tb_block = (i, name, ps, tb, fb, size)
            if ps < min_ps:
                min_ps = ps
                min_ps_block = (i, name, ps, tb, fb, size)
            if ps > max_raw_ps:
                max_raw_ps = ps
            if ps + size_ps - 1 > max_ps:
                max_ps = ps + size_ps - 1
                max_ps_block = (i, name, ps, tb, fb, size)

        width = max_ps - min_ps + 1
        height = max_tb - min_tb + 1
        depth = max_fb - min_fb + 1
        max_span = max(width, height, depth)

        if max_span <= 6:
            target_size = 6
        elif max_span <= 8:
            target_size = 8
        else:
            target_size = 10

        name = self.data.decode_blueprint_name(blueprint_data) if blueprint_data else ""
        if not name:
            name = "Unnamed Blueprint"
        logging.info(
            "Downscaler bounds for %s: %dx%dx%d -> target %dx%dx%d",
            name,
            width, height, depth,
            target_size, target_size, target_size
        )
        def format_block(label, data, expands=False):
            if not data:
                return f"{label}: (none)"
            idx, name, ps, tb, fb, size = data
            suffix = " [EXPANDS EDGE]" if expands else ""
            return (
                f"{label}: Index: {idx}, Gummi Block: {name}, "
                f"Coordinates: {ps},{tb},{fb}, Block Size: {size}{suffix}"
            )

        logging.info(
            "Downscaler edge blocks:\n%s\n%s\n%s\n%s\n%s\n%s",
            format_block("Min Port-Starboard Axis", min_ps_block),
            format_block(
                "Max Port-Starboard Axis",
                max_ps_block,
                max_ps_block is not None
                and max_ps > max_raw_ps
                and max_ps_block[5][0] > 1
            ),
            format_block("Min Top-Bottom Axis", min_tb_block),
            format_block(
                "Max Top-Bottom Axis",
                max_tb_block,
                max_tb_block is not None
                and max_tb > max_raw_tb
                and max_tb_block[5][1] > 1
            ),
            format_block("Min Front-Back Axis", min_fb_block),
            format_block(
                "Max Front-Back Axis",
                max_fb_block,
                max_fb_block is not None
                and max_fb > max_raw_fb
                and max_fb_block[5][2] > 1
            )
        )
        def choose_center(span, min_coord, cockpit_list, axis_index, axis_name):
            leftover = target_size - span
            base = leftover // 2
            if leftover % 2 == 0 or not cockpit_list:
                logging.debug(
                    "Downscaler center %s: span=%d leftover=%d -> %d (no bias)",
                    axis_name,
                    span,
                    leftover,
                    base
                )
                return base
            alt = leftover - base  # base+1
            target_center = (target_size - 1) / 2.0
            best = base
            best_dist = None
            best_idx = None
            best_cockpit = None
            best_dist_alt = None
            alt_dist = None
            for idx, center in enumerate((base, alt)):
                dist = None
                closest = None
                for (ps, tb, fb, sps, stb, sfb) in cockpit_list:
                    coord = (ps, tb, fb)[axis_index]
                    size = (sps, stb, sfb)[axis_index]
                    cockpit_center = coord + (size - 1) / 2.0
                    world_center = (cockpit_center - min_coord) + center
                    d = abs(world_center - target_center)
                    if dist is None or d < dist:
                        dist = d
                        closest = (ps, tb, fb, sps, stb, sfb)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best = center
                    best_idx = idx
                    best_cockpit = closest
                if idx == 1:
                    alt_dist = dist
            if best_idx == 0:
                best_dist_alt = alt_dist
            else:
                best_dist_alt = best_dist
            if best_dist_alt is None:
                best_dist_alt = -1
            logging.debug(
                "Downscaler center %s: span=%d leftover=%d -> %d (alt=%d, best_dist=%.2f, alt_dist=%.2f, cockpit=%s)",
                axis_name,
                span,
                leftover,
                best,
                alt,
                best_dist if best_dist is not None else -1,
                best_dist_alt,
                (
                    f"{best_cockpit[0]},{best_cockpit[1]},{best_cockpit[2]} size={best_cockpit[3]}x{best_cockpit[4]}x{best_cockpit[5]}"
                    if best_cockpit else "none"
                )
            )
            return best

        center_ps = choose_center(width, min_ps, cockpit_blocks, 0, "Port-Starboard")
        center_tb = choose_center(height, min_tb, cockpit_blocks, 1, "Top-Bottom")
        center_fb = choose_center(depth, min_fb, cockpit_blocks, 2, "Front-Back")

        origin_ps = 0
        origin_tb = 0
        origin_fb = 0

        updated = bytearray(blueprint_data)
        for i in range(block_count):
            start = blocks_start + i * 12
            byte0 = updated[start]
            byte1 = updated[start + 1]
            fb = byte1 & 0x0F
            tb = (byte0 >> 4) & 0x0F
            ps = byte0 & 0x0F

            new_ps = (ps - min_ps) + center_ps + origin_ps
            new_tb = (tb - min_tb) + center_tb + origin_tb
            new_fb = (fb - min_fb) + center_fb + origin_fb

            if not (0 <= new_ps <= 0x0F and 0 <= new_tb <= 0x0F and 0 <= new_fb <= 0x0F):
                return blueprint_data

            updated[start] = ((new_tb & 0x0F) << 4) | (new_ps & 0x0F)
            updated[start + 1] = (byte1 & 0xF0) | (new_fb & 0x0F)

        try:
            struct.pack_into("<3H", updated, 0x02, target_size, target_size, target_size)
        except struct.error:
            return blueprint_data

        return updated

    ORIENTATION_DIRECTION_BY_B3 = {
        0x00: "Right",
        0x01: "Left",
        0x02: "Up",
        0x03: "Down",
        0x04: "Forward",
        0x05: "Backward",
    }

    ORIENTATION_MOUNT_BY_B3_B2 = {
        0x04: {0x03: "Left", 0x12: "Right", 0x20: "Bottom", 0x31: "UpsideDown"},
        0x05: {0x02: "Left", 0x13: "Right", 0x21: "Bottom", 0x30: "UpsideDown"},
        0x01: {0x24: "Bottom", 0x35: "UpsideDown", 0x43: "Back", 0x52: "Front"},
        0x00: {0x25: "Bottom", 0x34: "UpsideDown", 0x42: "Back", 0x53: "Front"},
        0x02: {0x04: "Left", 0x15: "Right", 0x41: "Back", 0x50: "Front"},
        0x03: {0x05: "Left", 0x14: "Right", 0x40: "Back", 0x51: "Front"},
    }

    def get_orientation(self, byte2, byte3):
        direction = self.ORIENTATION_DIRECTION_BY_B3.get(byte3)
        mount = self.ORIENTATION_MOUNT_BY_B3_B2.get(byte3, {}).get(byte2)
        if not direction or not mount:
            return None
        return direction, mount

    def get_oriented_block_size(self, gummi_id, byte2, byte3):
        base_size = Gummi_Block_Info.gummi_block_sizes.get(gummi_id, (1, 1, 1))
        if base_size == (1, 1, 1):
            return base_size
        orientation = self.get_orientation(byte2, byte3)
        if not orientation:
            return base_size
        direction, mount = orientation

        # World axes: PS=x, TB=y, FB=z. Signs indicate side, but sizes ignore sign.
        axis = {
            "PS": (1, 0, 0),
            "TB": (0, 1, 0),
            "FB": (0, 0, 1),
        }
        def neg(v):
            return (-v[0], -v[1], -v[2])
        def cross(a, b):
            return (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )

        direction_vec = {
            "Forward": (0, 0, -1),
            "Backward": (0, 0, 1),
            "Left": (-1, 0, 0),
            "Right": (1, 0, 0),
            "Up": (0, 1, 0),
            "Down": (0, -1, 0),
        }
        mount_down_vec = {
            "Left": (-1, 0, 0),
            "Right": (1, 0, 0),
            "Front": (0, 0, -1),
            "Back": (0, 0, 1),
            "Bottom": (0, -1, 0),
            "UpsideDown": (0, 1, 0),
        }

        local_forward = direction_vec[direction]
        local_down = mount_down_vec[mount]
        local_up = neg(local_down)
        local_right = cross(local_forward, local_up)

        def axis_id(v):
            if abs(v[0]) == 1:
                return "PS"
            if abs(v[1]) == 1:
                return "TB"
            return "FB"

        local_to_world = {
            axis_id(local_right): "RIGHT",
            axis_id(local_up): "UP",
            axis_id(local_forward): "FWD",
        }

        size_right, size_up, size_fwd = base_size
        world_ps = size_right if local_to_world.get("PS") == "RIGHT" else (
            size_up if local_to_world.get("PS") == "UP" else size_fwd
        )
        world_tb = size_right if local_to_world.get("TB") == "RIGHT" else (
            size_up if local_to_world.get("TB") == "UP" else size_fwd
        )
        world_fb = size_right if local_to_world.get("FB") == "RIGHT" else (
            size_up if local_to_world.get("FB") == "UP" else size_fwd
        )
        return (world_ps, world_tb, world_fb)

    def find_first_flyable_blueprint(self):
        for blueprint_number in range(1, 11):
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if blueprint_data and self.is_flyable_blueprint(blueprint_data):
                return blueprint_number
        return None

    def prompt_current_ship_popup(self, save_number):
        ui = self.save_tabs.get(save_number)
        if not ui:
            return None
        self.ensure_save_tab_built(save_number, ui)

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select Current Ship (Save {save_number})")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog_frame = tk.Frame(dialog, padx=10, pady=10)
        dialog_frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(dialog_frame, text="Please select the ship to default to in-game:")
        label.pack(anchor="w")

        listbox = tk.Listbox(dialog_frame, width=30, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        blueprint_labels = []
        for blueprint_number in range(1, 11):
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if blueprint_data:
                name = self.data.decode_blueprint_name(blueprint_data)
            else:
                name = "(Empty)"
            label_text = f"Blueprint {blueprint_number} - {name}"
            blueprint_labels.append(label_text)
            listbox.insert(tk.END, label_text)

            flyable = blueprint_data and self.is_flyable_blueprint(blueprint_data)
            if not flyable:
                listbox.itemconfig(
                    blueprint_number - 1,
                    fg="#8b3a3a",
                    bg="#f6caca",
                    selectforeground="#6b2a2a",
                    selectbackground="#e8a8a8"
                )

        selected_default = self.data.get_selected_blueprint()
        if selected_default and 1 <= selected_default <= listbox.size():
            listbox.selection_set(selected_default - 1)
            listbox.activate(selected_default - 1)
            listbox.see(selected_default - 1)

        result = {"selection": None}

        def on_ok():
            selected = listbox.curselection()
            if not selected:
                messagebox.showerror("No Selection", "Please select a blueprint.")
                return
            slot = selected[0] + 1
            blueprint_data = self.data.extract_blueprint_data(slot)
            if not blueprint_data or not self.is_flyable_blueprint(blueprint_data):
                reason = self.get_flyable_issue(blueprint_data)
                messagebox.showerror("Not Flyable", reason)
                return
            result["selection"] = slot
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        button_frame = tk.Frame(dialog_frame)
        button_frame.pack(anchor="e", pady=(8, 0))

        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        dialog.wait_window()
        return result["selection"]

    def refresh_blueprint_list(self, save_number, ui):
        self.set_active_save(save_number)
        ui["blueprint_listbox"].delete(0, tk.END)
        blueprints = self.data.list_available_blueprints()
        for index, blueprint in enumerate(blueprints):
            ui["blueprint_listbox"].insert(tk.END, blueprint)
            blueprint_data = self.data.extract_blueprint_data(index + 1)
            if not blueprint_data:
                ui["blueprint_listbox"].itemconfig(
                    index,
                    fg="#7a7a7a",
                    bg="#e6e6e6",
                    selectforeground="#4a4a4a",
                    selectbackground="#b0b0b0"
                )

    def import_blueprint(self, save_number, ui):
        self.set_active_save(save_number)
        selected_index = ui["blueprint_listbox"].curselection()
        blueprint_number = None
        if selected_index:
            blueprint_number = int(ui["blueprint_listbox"].get(selected_index[0]).split()[1])
        gumi_location = self.data.gumi_offsets.get(save_number)
        logging.info(
            "Import blueprint started (save %s, slot %s).",
            save_number,
            blueprint_number if blueprint_number is not None else "unknown"
        )
        try:
            ui["root"].update_idletasks()
        except Exception:
            pass
        success = Blueprint_Import.import_blueprint(
            self.data.gumi_content,
            ui["blueprint_listbox"],
            self.data.blueprint_offsets,
            self.save_filename,
            gumi_location,
            transform_fn=self.downscale_blueprint_data,
            show_success_message=False,
            parent=ui.get("root")
        )
        if success and blueprint_number is not None:
            blueprint_data = self.data.extract_blueprint_data(blueprint_number)
            if blueprint_data and len(blueprint_data) >= 0x08:
                size_hex = blueprint_data[0x02:0x08].hex().upper()
                logging.info(
                    "Import wrote blueprint size bytes for slot %d: %s",
                    blueprint_number,
                    size_hex
                )

        if success:
            ui["stats_dirty"] = True
            self.refresh_blueprint_list(save_number, ui)
            if blueprint_number is not None:
                ui["blueprint_listbox"].selection_clear(0, tk.END)
                ui["blueprint_listbox"].selection_set(blueprint_number - 1)
                ui["blueprint_listbox"].activate(blueprint_number - 1)
                ui["blueprint_listbox"].see(blueprint_number - 1)
                self.on_blueprint_select(save_number, ui)
            self.update_current_ship_label(save_number, ui)
            self.update_gummi_stats(
                save_number,
                reason=f"import blueprint into slot {blueprint_number}" if blueprint_number else "import blueprint"
            )
            self.update_gummi_treeview(ui, self.data.blueprint_data, self.data.gumi_content)
            self.refresh_inventory_editor(save_number, ui, log_updates=True)
            if blueprint_number is not None:
                messagebox.showinfo(
                    "Blueprint Imported",
                    f"Blueprint imported into slot {blueprint_number} successfully."
                )
        if success:
            logging.info(
                "Import blueprint completed (save %s, slot %s).",
                save_number,
                blueprint_number if blueprint_number is not None else "unknown"
            )

    def export_blueprint(self, save_number, ui):
        self.set_active_save(save_number)
        Blueprint_Export.export_blueprint(
            self.save_filename,
            self.data,
            ui["blueprint_listbox"]
        )

    def setup_inventory_tabs_for_save(self, save_number, parent_notebook, ui):
        logging.debug("Setting up Inventory tabs for Save %s.", save_number)
        gummi_inventory_tab = ttk.Frame(parent_notebook)
        blueprint_collection_tab = ttk.Frame(parent_notebook)
        ship_controls_tab = ttk.Frame(parent_notebook)

        parent_notebook.add(gummi_inventory_tab, text='Gummi Block Inventory')
        parent_notebook.add(blueprint_collection_tab, text='Blueprint Collection')
        parent_notebook.add(ship_controls_tab, text='Ship Controls')

        self.create_inventory_editor(gummi_inventory_tab, show_blueprints=False, ui=ui, save_number=save_number)
        self.create_inventory_editor(blueprint_collection_tab, show_blueprints=True, ui=ui, save_number=save_number)
        self.setup_ship_controls_tab(save_number, ship_controls_tab, ui)
        logging.debug("Inventory tabs setup complete for Save %s.", save_number)

    def setup_ship_controls_tab(self, save_number, parent_tab, ui):
        """Setup the Ship Controls tab for a specific save."""
        self.set_active_save(save_number)

        base_offset = self.get_ship_controls_base_offset(save_number)
        controls = [
            ("Decelerate", base_offset + 0x00),
            ("Accelerate", base_offset + 0x04),
            ("Transform", base_offset + 0x08),
            ("Small Cannon", base_offset + 0x0C),
            ("Mid Cannon", base_offset + 0x10),
            ("Large Cannon", base_offset + 0x14),
            ("Small Laser", base_offset + 0x18),
            ("Mid Laser", base_offset + 0x1C),
            ("Large Laser", base_offset + 0x20),
        ]

        button_map = {
            "L1": bytes([0x00, 0x04, 0x00, 0x00]),
            "Triangle": bytes([0x00, 0x10, 0x00, 0x00]),
            "Circle": bytes([0x00, 0x20, 0x00, 0x00]),
            "Cross": bytes([0x00, 0x40, 0x00, 0x00]),
            "Square": bytes([0x00, 0x80, 0x00, 0x00]),
            "Null": bytes([0x00, 0x00, 0x00, 0x00]),
        }
        view_maps = {
            "PlayStation": {
                "L1": "L1",
                "Triangle": "Triangle",
                "Circle": "Circle",
                "Cross": "Cross",
                "Square": "Square",
                "Null": "Null",
            },
            "Xbox": {
                "LB": "L1",
                "Y": "Triangle",
                "B": "Circle",
                "A": "Cross",
                "X": "Square",
                "Null": "Null",
            },
            "Nintendo": {
                "L": "L1",
                "X": "Triangle",
                "A": "Circle",
                "B": "Cross",
                "Y": "Square",
                "Null": "Null",
            },
        }
        view_colors = {
            "PlayStation": {
                "L1": "#c0c0c0",        # medium gray
                "Triangle": "#b6f0b6",  # light green
                "Circle": "#f7b6b6",    # pale red
                "Cross": "#b7e2ff",     # light blue
                "Square": "#f7c1e8",    # pastel pink
                "Null": self.default_label_bg,
            },
            "Xbox": {
                "LB": "#c0c0c0",        # medium gray
                "Y": "#fff1a8",         # pale yellow
                "B": "#f7b6b6",         # pale red
                "A": "#b6f0b6",         # pale green
                "X": "#b7e2ff",         # pale blue
                "Null": self.default_label_bg,
            },
            "Nintendo": {
                "L": "#d0d0d0",         # light gray
                "X": "#d0d0d0",         # light gray
                "A": "#b6f0b6",         # pale green
                "B": "#f7b6b6",         # pale red
                "Y": "#d0d0d0",         # light gray
                "Null": self.default_label_bg,
            },
        }
        view_display_to_canonical = view_maps
        view_canonical_to_display = {
            view: {canonical: display for display, canonical in mapping.items()}
            for view, mapping in view_maps.items()
        }
        reverse_map = {v: k for k, v in button_map.items()}
        reverse_map_alt = {
            bytes([0x04, 0x00, 0x00, 0x00]): "L1",
            bytes([0x10, 0x00, 0x00, 0x00]): "Triangle",
            bytes([0x20, 0x00, 0x00, 0x00]): "Circle",
            bytes([0x40, 0x00, 0x00, 0x00]): "Cross",
            bytes([0x80, 0x00, 0x00, 0x00]): "Square",
        }

        def decode_control_label(raw_bytes):
            if raw_bytes in reverse_map:
                return reverse_map[raw_bytes]
            if raw_bytes in reverse_map_alt:
                return reverse_map_alt[raw_bytes]
            if (
                len(raw_bytes) == 4
                and raw_bytes[0] in (0x04, 0x10, 0x20, 0x40, 0x80)
                and raw_bytes[1:] == b"\x00\x00\x00"
            ):
                return reverse_map_alt.get(raw_bytes, "Null")
            return "Null"

        container = tk.Frame(parent_tab)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ui.setdefault("ship_controls_vars", {})
        ui.setdefault("ship_controls_widgets", {})
        ui.setdefault("ship_controls_canonical", {})

        view_frame = tk.Frame(container)
        view_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        view_label = tk.Label(view_frame, text="Change Controller View:")
        view_label.pack(side=tk.LEFT, padx=(0, 6))

        view_var = tk.StringVar(value="PlayStation")
        view_menu = tk.OptionMenu(view_frame, view_var, *view_maps.keys())
        view_menu.config(width=12)
        view_menu.pack(side=tk.LEFT)
        self.attach_tooltip(
            view_menu,
            "View the control options in PlayStation, Xbox, or Nintendo button arrangements. "
            "Does not change the underlying button mapping."
        )
        ui["ship_controls_view_var"] = view_var
        ui["ship_controls_view_menu"] = view_menu

        def apply_view(view_name):
            display_to_canonical = view_display_to_canonical.get(view_name, view_maps["PlayStation"])
            canonical_to_display = view_canonical_to_display.get(view_name, view_canonical_to_display["PlayStation"])
            color_map = view_colors.get(view_name, view_colors["PlayStation"])
            values = list(display_to_canonical.keys())

            for control_label, combo in ui["ship_controls_widgets"].items():
                var = ui["ship_controls_vars"].get(control_label)
                canonical = ui["ship_controls_canonical"].get(control_label, "Null")
                display = canonical_to_display.get(canonical, "Null")
                if var:
                    var.set(display)
                menu = combo["menu"]
                menu.delete(0, "end")
                for choice in values:
                    menu.add_command(
                        label=choice,
                        command=lambda ch=choice, v=var, sn=save_number, c=control_label: set_control_value(v, ch, sn, c)
                    )
                combo.configure(background=color_map.get(display, self.default_label_bg))

        for row, (label, offset) in enumerate(controls, start=1):
            label_widget = tk.Label(container, text=label)
            label_widget.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)

            var = tk.StringVar()

            def set_control_value(v, choice, sn, control_label):
                v.set(choice)
                view_name = ui["ship_controls_view_var"].get()
                display_to_canonical = view_display_to_canonical.get(view_name, view_maps["PlayStation"])
                canonical = display_to_canonical.get(choice, "Null")
                ui["ship_controls_canonical"][control_label] = canonical
                self.set_active_save(sn)
                data = button_map.get(canonical, button_map["Null"])
                offset = dict(controls).get(control_label)
                if offset is not None:
                    self.data.gumi_content[offset:offset + 4] = data
                color_map = view_colors.get(view_name, view_colors["PlayStation"])
                widget = ui["ship_controls_widgets"].get(control_label)
                if widget:
                    widget.configure(background=color_map.get(choice, self.default_label_bg))

            combo = tk.OptionMenu(container, var, *view_maps["PlayStation"].keys())
            combo.config(width=12)
            combo.grid(row=row, column=1, sticky="w", pady=2)
            self.attach_tooltip(
                combo,
                "Maps this ship action to a controller button (changes in-game control assignment)."
            )

            # Initialize from gumi_content
            current_bytes = bytes(self.data.gumi_content[offset:offset + 4])
            canonical_label = decode_control_label(current_bytes)
            ui["ship_controls_canonical"][label] = canonical_label
            display_label = view_canonical_to_display["PlayStation"].get(canonical_label, "Null")
            var.set(display_label)
            combo.configure(background=view_colors["PlayStation"].get(display_label, self.default_label_bg))
            set_control_value(var, display_label, save_number, label)

            ui["ship_controls_vars"][label] = var
            ui["ship_controls_widgets"][label] = combo

        view_var.trace_add("write", lambda *_: apply_view(view_var.get()))

    def create_inventory_editor(self, tab, show_blueprints, ui, save_number):
        logging.debug(
            "Creating inventory editor for %s (Save %s)",
            "Blueprint Collection" if show_blueprints else "Gummi Block Inventory",
            save_number
        )
        is_final_mix = self.is_final_mix_save(save_number)

        # Create a canvas and scrollbar for scrolling through the inventory
        canvas = tk.Canvas(tab)
        canvas.pack(side="left", fill="both", expand=True)
        def on_scroll(*args):
            canvas.yview(*args)
            self.schedule_inventory_redraw(ui, canvas)

        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=on_scroll)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        editor_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=editor_frame, anchor="nw")
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.schedule_inventory_redraw(ui, canvas)
            return "break"
        canvas.bind("<MouseWheel>", on_mousewheel)
        editor_frame.bind("<MouseWheel>", on_mousewheel)

        # Variable to keep track of the spinbox count
        spinbox_count = 0
        ui.setdefault("suppress_inventory_trace", False)

        row = 1
        # Loop through the Gummi Block info and create labels and spinboxes
        for gummi_id, gummi_name in Gummi_Block_Info.gummi_block_names.items():
            if not show_blueprints and gummi_id in Gummi_Block_Info.system_gummis:
                continue
            if (not show_blueprints) and (not is_final_mix):
                if gummi_id in Gummi_Block_Info.design_gummis or gummi_id in Gummi_Block_Info.rare_design_gummis:
                    continue
            if show_blueprints and (not is_final_mix):
                if gummi_id in Gummi_Block_Info.final_mix_blueprints:
                    continue
            if (gummi_id in Gummi_Block_Info.gummi_blueprints) == show_blueprints:
                gummi_label = ttk.Label(editor_frame, text=gummi_name)
                gummi_label.grid(row=row, column=0, sticky="w")
            
                var = tk.IntVar(value=0)
                if show_blueprints:
                    gummi_checkbox = tk.Checkbutton(
                        editor_frame,
                        variable=var,
                        onvalue=1,
                        offvalue=0
                    )
                    gummi_checkbox.grid(row=row, column=1, sticky="w")
                    ui.setdefault("inventory_spinbox_widgets", {})[gummi_name] = gummi_checkbox
                else:
                    max_count = Gummi_Block_Info.max_gummi_counts.get(gummi_id, 1)
                    gummi_spinbox = tk.Spinbox(
                        editor_frame,
                        textvariable=var,
                        from_=0,
                        to=max_count
                    )
                    gummi_spinbox.grid(row=row, column=1)
                    ui.setdefault("inventory_spinbox_widgets", {})[gummi_name] = gummi_spinbox
                    self.attach_tooltip(
                        gummi_spinbox,
                        f"Max: {max_count} (values above this will be clamped)"
                    )

                    gummi_spinbox.bind(
                        "<ButtonPress-1>",
                        lambda _e, sn=save_number: self.start_spinbox_hold(sn)
                    )
                    gummi_spinbox.bind(
                        "<ButtonRelease-1>",
                        lambda _e, sn=save_number: self.end_spinbox_hold(sn)
                    )
                    gummi_spinbox.bind(
                        "<KeyPress-Up>",
                        lambda _e, sn=save_number: self.start_spinbox_hold(sn)
                    )
                    gummi_spinbox.bind(
                        "<KeyPress-Down>",
                        lambda _e, sn=save_number: self.start_spinbox_hold(sn)
                    )
                    gummi_spinbox.bind(
                        "<KeyRelease-Up>",
                        lambda _e, sn=save_number: self.end_spinbox_hold(sn)
                    )
                    gummi_spinbox.bind(
                        "<KeyRelease-Down>",
                        lambda _e, sn=save_number: self.end_spinbox_hold(sn)
                    )

                # Store reference to the spinboxes in the inventory dictionary
                ui["inventory_spinboxes"][gummi_name] = var

                # Bind the variable to update gumi_content
                var.trace_add(
                    'write',
                    lambda *args, name=gummi_name, var=var, sn=save_number: self.update_gummi_quantity(sn, name, var)
                )
                spinbox_count += 1
                row += 1

        logging.debug(
            "Created %d spinboxes for %s (Save %s)",
            spinbox_count,
            "Blueprints" if show_blueprints else "Gummi Blocks",
            save_number
        )

        # Update the canvas scrollregion when the content changes
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def schedule_inventory_redraw(self, ui, canvas):
        pending = ui.setdefault("inventory_scroll_pending", {})
        if pending.get(canvas):
            return
        def run():
            pending.pop(canvas, None)
            try:
                canvas.update_idletasks()
            except Exception:
                pass
        pending[canvas] = self.root.after(200, run)

    def update_gummi_quantity(self, save_number, gummi_name, quantity):
        try:
            self.set_active_save(save_number)
            ui = self.save_tabs.get(save_number)
            suppress_trace = bool(ui.get("suppress_inventory_trace")) if ui else False
            is_holding = bool(ui.get("spinbox_holding")) if ui else False

            # Convert quantity to integer; allow empty during user edits.
            if isinstance(quantity, tk.Variable):
                try:
                    quantity = quantity.get()
                except Exception:
                    return
            if quantity in ("", None):
                return
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
                if quantity > max_quantity:
                    quantity = max_quantity
                    if ui and isinstance(ui["inventory_spinboxes"].get(gummi_name), tk.Variable):
                        try:
                            ui["suppress_inventory_trace"] = True
                            ui["inventory_spinboxes"][gummi_name].set(quantity)
                        finally:
                            ui["suppress_inventory_trace"] = False
                quantity = max(0, min(quantity, max_quantity))

                # Calculate the offset in gumi_content
                gummi_offset = Gummi_Block_Operations.calculate_gummi_offset(gummi_id, self.data.gumi_content)
                if gummi_offset is not None:
                    # Update gumi_content with the new quantity
                    previous = self.data.gumi_content[gummi_offset]
                    if previous != quantity:
                        self.data.gumi_content[gummi_offset] = quantity
                        if not suppress_trace:
                            logging.debug(
                                "Spinbox updated (Save %s): %s %d -> %d",
                                save_number,
                                gummi_name,
                                previous,
                                quantity
                            )
                        if ui and not suppress_trace:
                            ui["stats_dirty"] = True
                            if is_holding:
                                self.schedule_gummi_treeview_refresh(save_number)
                            else:
                                # Refresh inventory counts shown in the Blueprint Manager list
                                self.update_gummi_treeview(ui, self.data.blueprint_data, self.data.gumi_content)
                else:
                    logging.warning(f"Invalid Gummi offset for {gummi_name} (ID: {gummi_id}).")
            else:
                logging.warning(f"Gummi name {gummi_name} not found in gummi_block_names.")
        except ValueError:
            # Ignore transient non-numeric edits (e.g., while typing)
            return

    def start_spinbox_hold(self, save_number):
        ui = self.save_tabs.get(save_number)
        if ui is not None:
            ui["spinbox_holding"] = True

    def end_spinbox_hold(self, save_number):
        ui = self.save_tabs.get(save_number)
        if ui is not None:
            ui["spinbox_holding"] = False
            self.schedule_gummi_treeview_refresh(save_number, immediate=True)
            self.schedule_gummi_stats_refresh(
                save_number,
                immediate=True,
                reason="spinbox hold end"
            )

    def schedule_gummi_treeview_refresh(self, save_number, immediate=False):
        ui = self.save_tabs.get(save_number)
        if not ui:
            return
        if immediate:
            pending = ui.get("gummi_treeview_pending")
            if pending:
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
                ui["gummi_treeview_pending"] = None
            self.set_active_save(save_number)
            self.update_gummi_treeview(ui, self.data.blueprint_data, self.data.gumi_content)
            return

        if ui.get("gummi_treeview_pending"):
            return

        def run_refresh(sn=save_number, u=ui):
            u["gummi_treeview_pending"] = None
            self.set_active_save(sn)
            self.update_gummi_treeview(u, self.data.blueprint_data, self.data.gumi_content)

        ui["gummi_treeview_pending"] = self.root.after(200, run_refresh)

    def schedule_gummi_stats_refresh(self, save_number, immediate=False, reason=None):
        ui = self.save_tabs.get(save_number)
        if not ui:
            return
        if immediate:
            pending = ui.get("gummi_stats_pending")
            if pending:
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
                ui["gummi_stats_pending"] = None
            self.update_gummi_stats(save_number, reason=reason)
            return

        if ui.get("gummi_stats_pending"):
            return

        def run_refresh(sn=save_number, u=ui, r=reason):
            u["gummi_stats_pending"] = None
            self.update_gummi_stats(sn, reason=r)

        ui["gummi_stats_pending"] = self.root.after(200, run_refresh)

    def refresh_inventory_editor(self, save_number, ui, log_updates=True):
        """Refresh the inventory editor after data changes by updating only changed values."""
        self.set_active_save(save_number)
        gummi_inventory = Gummi_Inventory_Editor.read_gummi_inventory(self.data.gumi_content)

        ui["suppress_inventory_trace"] = True
        try:
            for gummi_name, var in ui["inventory_spinboxes"].items():
                # Check if the gummi_name exists in the current inventory
                if gummi_name in gummi_inventory:
                    # Get the current inventory value for the gummi_name
                    inventory_value = gummi_inventory[gummi_name]
                
                    # Only update the Spinbox if the value has changed
                    try:
                        current_value = var.get()
                    except Exception:
                        current_value = inventory_value
                    if current_value != inventory_value:
                        var.set(inventory_value)  # Update the Spinbox with the new value
                        if log_updates:
                            logging.debug(f"Updated Spinbox for {gummi_name}: {inventory_value}")
        finally:
            ui["suppress_inventory_trace"] = False

# Main application execution point
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = GummiBlueprintController(root)
        root.mainloop()
    except Exception:
        _log_startup_exception(*sys.exc_info())
        raise
