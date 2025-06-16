I've been working on this code for a long time now, and am finally coming to terms
with the fact that I'm not a coder, and cannot properly implement what I want this
program to do, not even the save file loading/saving functionality.

The following is a detailed design brief written from an end-result point-of-view.
I hope the next person who decides to take this project on has better coding chops than I do.

-----

---Preliminary:
I want this program to be written in Python and built around a Model-View-Controller setup, as that sounds like the most maintainable way to build a program.

I have two pre-existing files containing important information lists for the program to reference: KH1SYS_Text.py, and Gummi_Block_Info.py

KH1SYS_Text.py contains the game's proprietary text format, which is needed to decode the names of the Gummi Blueprints.

Gummi_Block_Info.py contains much information about each Gummi Block, including names, maximum quantities, and classifications.

-----

---Data Structure of gumi_content, etc.:
-These are the constants for GUMI data structure:

GUMI_CONTENT_SIZE = 0x9B70                 # Total size of GUMI content block

The data in gumi_content is as follows:

Currently-Selected Ship: "GUMI" +0x10

Blueprint #1: "GUMI" +0x1C

Blueprint #2: "GUMI" +0xF8C

Blueprint #3: "GUMI" +0x1EFC

Blueprint #4: "GUMI" +0x2E6C

Blueprint #5: "GUMI" +0x3DDC

Blueprint #6: "GUMI" +0x4D4C

Blueprint #7: "GUMI" +0x5CBC

Blueprint #8: "GUMI" +0x6C2C

Blueprint #9: "GUMI" +0x7B9C

Blueprint #10: "GUMI" +0x8B0C

Gummi Inventory: "GUMI" +0x9A78

Gummi Ship Controls: "GUMI" +0x9B40


"Currently-Selected Ship" is a byte that tells the game which of the 10 editable blueprints is currently selected as the default ship the player will fly upon loading the save.

The "Blueprint #1-10" slots are the bytes where each blueprint's data is stored.  Inside the blueprint data, every aspect of a given Gummi Blueprint is stored, including which Gummi Blocks are used, how many of each are used, and (most crucially, in the context of this program) the name of the blueprint.  Each blueprint is 0xF6C in length.

"Gummi Inventory" is a table that keeps track of the player's inventory of Gummi Blocks, as well as their collection of prebuilt blueprints.  GUMI+0x9A78 is Cure-G (Gummi ID 0x01), and every inventory item afterwards matches the gummi_block_names list in Gummi_Block_Info.py.

"Gummi Ship Controls" is a table that keeps track of the player's preferred button assignments for piloting the Gummi Ship.



-These are the constants for Blueprint data structure:

BLUEPRINT_DATA_SIZE = 0xF6C                # Size of the entire blueprint data block

BLUEPRINT_BLOCK_COUNT_OFFSET = 0x00        # Offset for byte that stores the block count in blueprint

BLUEPRINT_SIZE_OFFSET_START = 0x01         # Start of offset for blueprint size

BLUEPRINT_SIZE_OFFSET_END = 0x06           # End of offset for blueprint size

BLUEPRINT_NAME_OFFSET_START = 0x4C         # Start of the encoded blueprint name in blueprint data

BLUEPRINT_NAME_OFFSET_END = 0x58           # End of the encoded blueprint name in blueprint data

BLUEPRINT_GUMMI_BLOCKS_START = 0x6C        # Start of blueprint's Gummi Block Data

-These are the constants for the data structure of a single Gummi Block within each Blueprint:

GUMMI_BLOCK_LENGTH = 0x0C                  # Total size of each Gummi Block entry in blueprint data

GUMMI_ID_OFFSET = 0x04                     # Offset of the ID for each Gummi Block in Gummi Block data.


---Initial Startup:
The Model should initialize the following:

self.file_content (A copy of the data from the entire loaded save file)
self.save_files (A copy of each individual save file from file_content, complete with its save name, extracted from the .png archive, or else just the data from the loaded individual save)
self.gumi_content (The slice of data from the selected entry from save_files that represents the actual Gummi data the tool will work with)
self.blueprint_data (A slice of data representing a single blueprint extracted from gumi_content)
self.gummi_blocks_raw (A copy of each individual 12-byte block of Gummi Block data as found within blueprint_data)
self.gummi_blocks (same as gummi_blocks_raw, but re-sequenced in Gummi ID order)


There are two valid types of save files: PC Port .png save archives, and individual PS2 saves, which are raw blocks of save data.

-----


---Part 1: The GUI: Top Menu and Blueprint Manager
Here I'll describe not only the layout of the GUI, but also the data flow that should take place upon interaction with the GUI.

--The Window:
The title of the program is "KH1 Gummi Manager", and the default window size is 720x450.

--Top Menu Bar, Loading and Saving:
Packed to the top of the program window, there's a menu (herein "Top Menu").  Packed to the left of the Top Menu, there are two buttons "Load Save File" and "Save Changes", which trigger the logic in the Model for loading save files and following the steps to write the modified gumi_content back to the original file.

Upon the loading of a save file as file_content, the Model should first check which type of save file it is.

If bytes 0x00-03 of the save file's header is ASCII "‰PNG", then it's most likely a .png save archive and file_content should be sent to decrypt.py, which will return its results as decrypted_saves, which the model in the main program will use to populate the save entries in save_files.

If it can't find the "‰PNG", then check if 0x2400-2403 of the loaded file is ASCII "GUMI", in which case it's an individual PS2 save and should be loaded directly into the first entry in save_files, with its save name being taken directly from the filename.

Else, just throw an error for invalid save file.

---

Decrypt.py should be a separate Python module that extracts Kingdom Hearts 1 Final Mix PC port save data from a .png save archive. The .png save archive contains:

A table of contents (TOC) starting at offset 0x70, consisting of 200 entries, each 0x158 bytes long.

The first 0xE0 bytes of each entry are encrypted using a 16-byte XOR key located at offset +0xE0.

After decryption, each entry contains:

A 0x40-byte ASCII name at offset 0x00.

A 4-byte little-endian integer at offset 0x50 indicating the size of the associated save data.

The actual save data begins at offset 0x10D30, with each save slot occupying 0x16C40 bytes.

The i-th save slot starts at 0x10D30 + i * 0x16C40.

Only TOC entries whose names match the pattern BISLPS-25198-## represent valid saves.

The module must:

Decrypt and parse the TOC entries.

Identify valid saves by matching their names.

For each valid save, extract the full 0x16C40 bytes from the correct offset.

Return a list of tuples containing the save name, save number, and raw save data as decrypted_saves.

Use struct for binary parsing and logging for debug output. The code should take file_content as input, not rely on direct file access.

---

Back to the Model of the main program: whether the loaded file is a .png save archive or a single save data block, the extracted save data should populate save_files.  By default, the program will load the first valid entry in save_files.

Once save_files has been populated with at least one valid save, the Model will go to 0x2400 of the save file (which should be the "GUMI" header) and extract the next 0x9B70 bytes as gumi_content.

When the "Save Changes" button is pressed, the Model will basically do these steps in reverse: write the gumi_content back to the entry in save_files it was pulled from, then write each entry in save_files back into the addresses in file_content they were pulled from, then file_content is written over the original file that the program opened.  After all of this happens, a pop-up informing the user that changes were saved successfully appears, with an "OK" button to dismiss it.



--Top Menu Bar, Save File Selector:

A drop-down menu, packed to the top-middle of the GUI, allows the user to select which save file from the save_files list to load gumi_content from.  Empty entries in the list are not displayed; only the ones populated with valid save data.

-----


---Part 2: Blueprint Manager Tab
This will be the biggest, most robust portion of the program.

The Blueprint Manager is the first tab from the left, and the program's default tab.

Packed to the left of the Blueprint Manager tab is a small ten-entry-tall listbox (called blueprint_listbox internally) labeled "Blueprints in save file:".  Below it are two buttons labeled "Import Blueprint" and "Export Blueprint".

Packed to the right of the Blueprint Manager tab is a large treeview (called gummi_treeview internally) with four columns: "Gummi Block" (the widest of the columns), "Type", "Required", and "Inventory".

Packed below the gummi_treeview is a button labeled "Add Required Gummi Blocks", with three checkboxes next to it in vertical orientation: "Add for all Blueprints" (checked by default), "Include Chest Gummis" (unchecked by default), and "Include Design Gummis" (unchecked by default).

When the Model loads gumi_content, the blueprint_listbox is populated with whatever blueprints are found in gumi_content.

The naming convention for each entry in blueprint_listbox is "Blueprint [blueprint_number] - [blueprint_name]", with blueprint_number taken from the blueprint slot the blueprint was taken from (valid values are 1-10).  The blueprint_name is either taken from BLUEPRINT_NAME_OFFSET_START through BLUEPRINT_NAME_OFFSET_END (decoded using the hex values in the KH1SYS_Text list in KH1SYS_Text.py, with 0x00 treated as an end-of-line), or else defaults to "(Empty)" in dark gray text with light gray highlight if there's no blueprint data there.

Clicking on a blueprint in blueprint_listbox will cause the Model to load that blueprint as blueprint_data.  From there, the Model checks the byte at 0x00 of the blueprint_data to determine how many Gummi Blocks are used in the blueprint.  Then the Model goes to 0x6C of blueprint_data and stores each 12-byte block of Gummi Block data (ONLY as many as are indicated by the byte at 0x00 of blueprint_data; E.G. if the byte reads 0x0B, store the first 11 blocks of Gummi Block data.) as gummi_blocks_raw.  The Model then reads the 4th byte of every Gummi Block as its Gummi ID, and sorts the entire list by Gummi ID and stores the re-ordered list as gummi_blocks.

Once that's complete, the GUI reads gummi_blocks, counts the number of times each Gummi ID appears in the list, and then, in the gummi_treeview, displays the information for each Gummi ID that's found in gummi_blocks, including its name in the "Gummi Block" column (discerned using the gummi_block_names list in Gummi_Block_Info.py), the Type in the "Type" column ("Chest" or "Design", else "Common"), the quantity used in the blueprint in the "Required" column, and the quantity available in the Gummi Inventory in the "Inventory" column (found at 0x9BA8 + Gummi ID -1; Gummi ID 0x00 is Null and should be ignored by the program).

The "Export Blueprint" button should cause the Model to export blueprint_data as a .kh1blueprint file.

The "Import Blueprint" button should cause the Model to import a .kh1blueprint file into one of the blueprint slots in gumi_content.

The "Add Required Gummi Blocks" button should cause the model to check the inventory addresses for every Gummi ID that's present in gummi_blocks; if a given Gummi Block's quantity in the inventory address is lower than the number of that Gummi Block the blueprint calls for, set the inventory quantity to match the blueprint's required count.

The "Add for all Blueprints" checkbox causes the program to automatically repeat "Add Required Gummi Blocks" for every blueprint in gumi_content when checked; otherwise it only adds the required Gummi Blocks for the currently selected Blueprint.

The "Include Chest Gummis" and "Include Design Gummis" checkboxes, when checked, allows Gummi Blocks designated as "Chest" or "Design" gummis (determined using the chest_gummis, design_gummis, and chest_design_gummis lists in Gummi_Block_Info.py) to be included in the "Add Required Gummi Blocks" operation.  The entries in chest_design_gummis shouldn't be included unless BOTH checkboxes are checked.  By default, these checkboxes are left unchecked, as messing with the quantities of these Gummis outside of the game itself could lead to certain chests being unable to be opened.



--Top Menu Bar, Information Box:
Packed to the right of the top menu bar, opposite of the "Load Save File" and "Save Changes" buttons, there should be a display that lists the save name of the currently-loaded save file, the currently-selected ship in gumi_content (at hex address 0x10), the highest SYS. UP in the inventory in gumi_content (0x9ABA for "SYS UP: 1" and 0x9ABB for "SYS UP: 2", else "SYS UP: 0"), and the highest COM LVL in the inventory in gumi_content (0x9ABC, 0x9ABD, 0x9ABE for "COM LVL: 1", "COM LVL: 2", and "COM LVL: 3" respectively, else "COM LVL: 0").

The program should automatically raise SYS UP 2 to 0x01 and display "SYS UP: 2" in a pale blue highlight if at least one blueprint in gumi_content has a blueprint size of "0x00 0x0A 0x00 0x0A 0x00 0x0A", otherwise, it should automatically raise SYS UP 1 to a value of 0x01 and display "SYS UP: 1" in a pale green highlight if at least one blueprint in gumi_content has a blueprint size of "0x00 0x08 0x00 0x08 0x00 0x08".  Otherwise, it displays "SYS UP: 0" with no highlight.

The program should automatically raise COM LVL 3 to a value of 0x01 and display "COM LVL: 3" in a pale blue highlight if:

-There are 5 or more blueprints in gumi_content
OR
-At least one blueprint in gumi_content has any of the following:
--more than 150 blocks
--more than 4 Engine Gummis
--more than 6 Weapon Gummis

The program should automatically raise COM LVL 2 to a value of 0x01 and display "COM LVL: 2" in a pale green highlight if:

-There are 2 or more blueprints in gumi_content
OR
-At least one blueprint in gumi_content has any of the following:
--more than 100 blocks
--more than 2 Engine Gummis
--more than 4 Weapon Gummis

Otherwise it should set COM LVL 1 to a value of 0x01 and display "COM LVL:1" with no highlight.

The SYS UP and COM LVL parameter checks should be performed every time the model class makes a change to the data in gumi_content.  While the checks are being performed, the display should replace the SYS UP and COM LVL text with "checking SYS UP and COM LVL parameters..." for the duration of both checks.

-----




---Part 3: Extra Features, Gummi Inventory Editor, and Ship Controls
--Extra Top Menu Features:
Upon the user clicking the "Save Changes" button, a pop-up window should appear, consisting of the text "Please select the ship to default to in-game:", along with a duplicate of Blueprint Manager's blueprint_listbox.  After the user selects the desired blueprint to use as the default ship (which the data reads as a value of 1-10) and clicks "OK", the pop-up disappears, the Model writes the selected value to the 0x10 offset in gumi_content, and the logic for saving changes commences.


--Extra Blueprint Manager Features:
Right-clicking on an entry in blueprint_listbox will both select that entry (loading it as blueprint_data) and display a right-click menu with three options: "Migrate", "Rename", and "Delete".

"Migrate" is a function intended to migrate a blueprint from the currently-loaded gumi_content to a blueprint slot in a different save file in save_files.  First, it displays a pop-up window where the user can select which save file to migrate the blueprint to; the "gumi_content"-equivalent data slice from this save file's GUMI header up to GUMI+0x9B70 is extracted as "gumi_content_migrate".  Next, the View generates a pop-up window with a copy of blueprint_listbox (sans right-click menu), which is populated with the ten blueprint slots from gumi_content_migrate; the user clicks which slot to migrate the blueprint to; if the chosen slot would overwrite an existing blueprint, a warning box appears asking if the user is okay with overwriting the blueprint.  If "Yes", then the selected blueprint overwrites the blueprint in the chosen slot in gumi_content_migrate, then gumi_content_migrate is written back into the save slot in save_files that it was taken from and the pop-up closes, if "No", then the warning box closes and the user must pick another blueprint slot from gumi_content_migrate.

"Rename" displays a pop-up window where the user can type a 12-character ASCII string, which the Model will then convert to KH1SYS_Text and overwrite the name in blueprint_data at BLUEPRINT_NAME_OFFSET_START.

"Delete" is very simple; it replaces the entire BLUEPRINT_DATA_SIZE of that blueprint with "0x00", erasing the content of that blueprint from the gumi_content.


--Inventory Editor/Blueprint Collection Tabs:
The Gummi Block Inventory tab is the second tab from the left (after the Blueprint Manager tab), and the Blueprint Collection tab is the one after that.

This program will have one tab for the Gummi Block Inventory, and another for the Blueprint Collection.  Both tabs use the same underlying code structure (herein "Inventory Editor").

The interface for the Inventory Editor should consist entirely of a list of spinboxes; one spinbox for every Gummi ID in gummi_block_names in Gummi_Block_Info.py, and the name of the associated Gummi Block right next to that spinbox.

There should be two ways to scroll through the list: one by using the mouse's scroll wheel while the cursor is anywhere inside the Inventory Editor tab, and the other by clicking and dragging the scroll bar that's packed to the right of the Inventory Editor tab.

The program reads the inventory from gumi_content at 0x9A78 as the "0x01" entry in gummi_block_names from Gummi_Block_Info.py (Gummi ID 0x01/Cure-G), and continues the sequence of gummi_block_names from there, with the value at each inventory address being loaded into the spinbox in the Inventory Editor.

From there, every time the user changes the quantity of the spinbox for a given Gummi Block, the Model will write the new value to that Gummi Block's inventory address in gumi_content.

The Inventory items start with Gummi ID 0x01 (Cure-G), and follows the sequencing of gummi_block_names (from Gummi_Block_Info.py) from there.  Gummi_Block_Info.py also contains max_gummi_counts, which tells the program what the upper limit is for each Gummi Block in the Inventory; if no upper limit is defined, the program should assume the upper limit is "1".

Checks should be added to ensure that SYS UP 1, SYS UP 2, COM LVL 1, COM LVL 2, and COM LVL 3 never go lower than the SYS UP and COM LVL parameter checks allow for each level of SYS UP or COM LVL, which is determined by the state of the blueprints in each blueprint slot in gumi_content.

The only difference between the Gummi Block Inventory and the Blueprint Collection is that Blueprint Collection sets "ShowBlueprints=True", which has the effect of showing the Blueprints (as listed in gummi_blueprints in Gummi_Block_Info.py) and hiding the other inventory items.  The Gummi Block Inventory sets "ShowBlueprints=False", which hides the Blueprints, and shows the other inventory items.


--Ship Controls Tab:
Ship Controls is the fourth tab from the left, after Blueprint Manager, Inventory Editor, and Blueprint Collection.

There are 9 drop-down boxes representing in-game controls, each labeled as follows: Decelerate, Accelerate, Transform, Small Cannon, Mid Cannon, Large Cannon, Small Laser, Mid Laser, and Large Laser.

The contents of the drop-down boxes represent the buttons on a PS2 controller, each labeled as follows: L1 (highlighted medium gray), Triangle (highlighted light green), Circle (highlighted pastel orange), Cross (highlighted light blue), Square (highlighted pastel pink), and Null (no highlight).

Hex Strings mapped to Buttons:
0x00 0x04 0x00 0x00 = L1
0x00 0x10 0x00 0x00 = Triangle
0x00 0x20 0x00 0x00 = Circle
0x00 0x40 0x00 0x00 = Cross
0x00 0x80 0x00 0x00 = Square
0x00 0x00 0x00 0x00 = Null

When the contents of each of the 9 drop-down boxes are changed, the hex string associated with the chosen button is written to the appropriate Control Offset:

Control Offsets:
GUMI +0x9B40 = Decelerate
GUMI +0x9B44 = Accelerate
GUMI +0x9B48 = Transform
GUMI +0x9B4C = Small Cannon
GUMI +0x9B50 = Mid Cannon
GUMI +0x9B54 = Large Cannon
GUMI +0x9B58 = Small Laser
GUMI +0x9B5C = Mid Laser
GUMI +0x9B60 = Large Laser

An extra "Change Controller View" dropdown optionally replaces the GUI text for the PS2 button arrangements with Xbox and Nintendo button arrangements instead.  The internal logic is unchanged.

PlayStation = Xbox                       = Nintendo
L1          = LB (Medium Gray Highlight) = L (Light Gray Highlight)
Triangle    = Y (Pale Yellow Highlight)  = X (Light Gray Highlight)
Circle      = B (Pale Red Highlight)     = A (Pale Green Highlight) 
Cross       = A (Pale Green Highlight)   = B (Pale Red Highlight)
Square      = X (Pale Blue Highlight)    = Y (Light Gray Highlight)
Null







                  Here's the original readme:
  ---Intro:

Just made a super-awesome KH1 Gummi Ship?  Wanna share it with others?  Wanna use it in a new save?

With this tool, you can export blueprints you made from that old endgame save, and import them into new save files!  Start your Gummi Journey in style!

(Currently compatible ONLY with foldered PCSX2 saves.  PC Port Save compatibility is being worked on, but is buggy at the moment.)

  ---Tool Functionality:

-Upon opening, there's a "Load Save File" button at the top, with a "Save Changes" button right next to it.  A message box, also at the top, displays the loaded save file, the currently-selected ship, and the current SYS UP and COM LVL.

-Just below the buttons at the top, there are three tabs: "Blueprint Manager", "Gummi Block Inventory", and "Blueprint Collection".

In "Blueprint Manager", you can manage the ten editable blueprints the game gives you.  This is the default tab.

In "Gummi Block Inventory", you can freely edit the quantity of any Gummi item in the inventory.

In "Blueprint Collection", you can view and edit your collection of pre-built Gummi Ship blueprints obtained from enemy ships and other rewards.

So you can go crazy and max out your inventory if you like, but if all you want is to import a mid-to-lategame blueprint into an early-game save file, and only add to the inventory the neccessary parts to build the ship and make it work, you can do that without ever leaving the Blueprint Manager.

-In the Blueprint Manager, you can Export and Import Blueprints by clicking on the appropriate button beneath the Blueprint Listbox.

-You can also Rename or Delete Blueprints by right-clicking on the desired Blueprint and clicking "Rename" or "Delete" in the Right Click Menu.

-You can even change the save file's currently selected ship just by clicking on the Blueprint Listbox!

-You can also add Gummi Blocks to your Inventory based on the requirements of the blueprints currently imported.  Gummi Blocks are catagorized into three types: Common, Chest, and Design.

Common Gummis are Gummi Blocks that can be sold at Cid's shop or are otherwise fairly easy to obtain.

Chest Gummis are Gummi Blocks that, in Final Mix, are obtained from treasure chests and cannot be bought or sold.

Design Gummis are the Gummi Blocks introduced in Final Mix, which means they aren't available and may cause unexpected bugs in pre-Final Mix versions of the game.

By default, Chest and Design Gummis don't get added to the inventory, and while it is recommended to leave their checkboxes unchecked so that you aren't locked out of chests containing late-game Gummi Blocks, the user always has the option to add them to the inventory anyway.

  ---To-do list:

-CRITICAL: Fix loading PC Port save files.

-Fix a bug where clicking on an empty blueprint does not clear the gummi_treeview. (Did I resolve this already?)

-Add support for editing Gummi Ship controls; extend the gumi_content slice to accommodate that section of the data.

-Simplify the SYS UP and COM LVL code; set all five of them to 1 upon importing a blueprint.  This will prevent blueprints from unexpectedly having blocks disappear because the SYS UP/COM LVL weren't set correctly.

-Compile the program as an .exe with external .py components.

-Fix visual errors that affect tool functionality.
