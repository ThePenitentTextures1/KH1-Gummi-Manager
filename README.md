                  Here's the original readme:
  ---Intro:

Just made a super-awesome KH1 Gummi Ship?  Wanna share it with others?  Wanna use it in a new save?

With this tool, you can export blueprints you made from that old endgame save, and import them into new save files!  Start your Gummi Journey in style!

Compatible Saves:

-PC Port .png save files

-PS2 Foldered Saves:

"BISLPS-25198-XX" - Kingdom Hearts Final Mix (Japan)

"BISLPS-25105-XX" - Kingdom Hearts (Japan)

"BASLUS-20370-XX" - Kingdom Hearts (USA)

"BESCES-50967-XX" - Kingdom Hearts (UK/Australia)

"BESCES-50968-XX" - Kingdom Hearts (French)

"BESCES-50969-XX" - Kingdom Hearts (German)

"BESCES-50970-XX" - Kingdom Hearts (Italian)

"BESCES-50971-XX" - Kingdom Hearts (Spanish)

(I had to infer most of these, the BESCES filenames haven't been tested yet; please let me know if one of these is wrong or if you get an error trying to import them.)

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
