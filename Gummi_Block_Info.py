gummi_block_names = {
    0x01: "Cure-G",
    0x02: "Curaga-G",
    0x03: "Life-G",
    0x04: "Full-Life-G",
    0x05: "Fire-G",
    0x06: "Fira-G",
    0x07: "Firaga-G",
    0x08: "Flare-G",
    0x09: "Holy-G",
    0x0A: "Protect-G (Cube)",
    0x0B: "Protect-G (Ramp)",
    0x0C: "Protect-G (Pyramid)",
    0x0D: "Protect-G (Cylinder)",
    0x0E: "Protect-G (Round)",
    0x0F: "Protect-G (Spherical)",
    0x10: "Protect-G (Cone)",
    0x11: "Protect-G (Half Ball)",
    0x12: "Shell-G (Cube)",
    0x13: "Shell-G (Ramp)",
    0x14: "Shell-G (Pyramid)",
    0x15: "Shell-G (Cylinder)",
    0x16: "Shell-G (Round)",
    0x17: "Shell-G (Spherical)",
    0x18: "Shell-G (Cone)",
    0x19: "Shell-G (Half Ball)",
    0x1A: "Dispel-G (Cube)",
    0x1B: "Dispel-G (Ramp)",
    0x1C: "Dispel-G (Pyramid)",
    0x1D: "Dispel-G (Cylinder)",
    0x1E: "Dispel-G (Round)",
    0x1F: "Dispel-G (Spherical)",
    0x20: "Dispel-G (Cone)",
    0x21: "Dispel-G (Half Ball)",
    0x22: "Aerora-G >",
    0x23: "Aerora-G <",
    0x24: "Aeroga-G >",
    0x25: "Aeroga-G <",
    0x26: "Tornado-G >",
    0x27: "Tornado-G <",
    0x28: "Float-G >",
    0x29: "Float-G <",
    0x2A: "Aero-G >",
    0x2B: "Aero-G <",
    0x2C: "Aero-G (Square)",
    0x2D: "Drain-G >",
    0x2E: "Drain-G <",
    0x2F: "Osmose-G >",
    0x30: "Osmose-G <",
    0x31: "Transform-G",
    0x32: "Warp-G",
    0x33: "Scan-G (Front)",
    0x34: "Scan-G (All)",
    0x35: "Haste-G",
    0x36: "Haste2-G",
    0x37: "Shield-G",
    0x38: "Shield2-G",
    0x39: "Esuna-G (Circle)",
    0x3A: "Esuna-G (Square)",
    0x3B: "Thunder-G",
    0x3C: "Thundara-G",
    0x3D: "Thundaga-G",
    0x3E: "Comet-G",
    0x3F: "Meteor-G",
    0x40: "Ultima-G",
    0x41: "Spray",
    0x42: "Palette",
    0x43: "SYS. UP1",
    0x44: "SYS. UP2",
    0x45: "COM. LVL1",
    0x46: "COM. LVL2",
    0x47: "COM. LVL3",
    0x48: "Kingdom Model",
    0x49: "Hyperion Model",
    0x4A: "Geppetto Model",
    0x4B: "Cid Model",
    0x4C: "Leon Model",
    0x4D: "Yuffie Model",
    0x4E: "Aerith Model",
    0x4F: "Cactuar Model",
    0x50: "Chocobo Model",
    0x51: "Cindy Model",
    0x52: "Shiva Model",
    0x53: "Lamia Model",
    0x54: "Sandy Model",
    0x55: "Sylph Model",
    0x56: "Carbuncle Model",
    0x57: "Mindy Model",
    0x58: "Goblin Model",
    0x59: "Bomb Model",
    0x5A: "Remora Model",
    0x5B: "Ahriman Model",
    0x5C: "Imp Model",
    0x5D: "Siren Model",
    0x5E: "Stingray Model",
    0x5F: "Catoblepas Model",
    0x60: "Adamant Model",
    0x61: "Serpent Model",
    0x62: "Ifrit Model",
    0x63: "Odin Model",
    0x64: "Atomos Model",
    0x65: "Golem Model",
    0x66: "Diablos Model",
    0x67: "Deathguise Model",
    0x68: "Typhoon Model",
    0x69: "Alexander Model",
    0x6A: "Leviathan Model",
    0x6B: "Ramuh Model",
    0x6C: "Omega Model",
    0x6D: "Moogle Model",
    0x6E: "Valefor Model",
    0x6F: "PuPu Model",
    0x70: "Cerberus Model",
    0x71: "Tonberry Model",
    0x72: "Pandaemonium Model",
    0x73: "Ixion Model",
    0x74: "Gilgamesh Model",
    0x75: "Phoenix Model",
    0x76: "Eden Model",
    0x77: "Bahamut Model",
    0x81: "Wheel-G",
    0x82: "Fang-G",
    0x83: "Horn-G",
    0x84: "Angel-G",
    0x85: "Dark-G",
    0x86: "Shoes-G",
    0x87: "Rock-G >",
    0x88: "Rock-G <",
    0x89: "Scissors-G >",
    0x8A: "Scissors-G <",
    0x8B: "Paper-G >",
    0x8C: "Paper-G <",
    0x8D: "Crown-G",
    0x8E: "Drill-G",
    0x8F: "Caterpillar-G >",
    0x90: "Caterpillar-G [Square]",
}

# Define the maximum count for each Gummi block based on the provided in-game quantities
max_gummi_counts = {
    0x01: 1,    # Cure-G
    0x02: 1,    # Curaga-G
    0x03: 1,    # Life-G
    0x04: 1,    # Full-Life-G
    0x05: 6,    # Fire-G
    0x06: 6,    # Fira-G
    0x07: 4,    # Firaga-G
    0x08: 4,    # Flare-G
    0x09: 2,    # Holy-G
    0x0A: 99,   # Protect-G (Cube)
    0x0B: 99,   # Protect-G (Ramp)
    0x0C: 99,   # Protect-G (Pyramid)
    0x0D: 30,   # Protect-G (Cylinder)
    0x0E: 30,   # Protect-G (Round)
    0x0F: 10,   # Protect-G (Spherical)
    0x10: 10,   # Protect-G (Cone)
    0x11: 10,   # Protect-G (Half Ball)
    0x12: 99,   # Shell-G (Cube)
    0x13: 99,   # Shell-G (Ramp)
    0x14: 99,   # Shell-G (Pyramid)
    0x15: 20,   # Shell-G (Cylinder)
    0x16: 20,   # Shell-G (Round)
    0x17: 8,    # Shell-G (Spherical)
    0x18: 8,    # Shell-G (Cone)
    0x19: 8,    # Shell-G (Half Ball)
    0x1A: 99,   # Dispel-G (Cube)
    0x1B: 99,   # Dispel-G (Ramp)
    0x1C: 99,   # Dispel-G (Pyramid)
    0x1D: 10,   # Dispel-G (Cylinder)
    0x1E: 10,   # Dispel-G (Round)
    0x1F: 6,    # Dispel-G (Spherical)
    0x20: 6,    # Dispel-G (Cone)
    0x21: 6,    # Dispel-G (Half Ball)
    0x22: 30,   # Aerora-G >
    0x23: 30,   # Aerora-G <
    0x24: 20,   # Aeroga-G >
    0x25: 20,   # Aeroga-G <
    0x26: 10,   # Tornado-G >
    0x27: 10,   # Tornado-G <
    0x28: 10,   # Float-G >
    0x29: 10,   # Float-G <
    0x2A: 99,   # Aero-G >
    0x2B: 99,   # Aero-G <
    0x2C: 99,   # Aero-G (Square)
    0x2D: 4,    # Drain-G >
    0x2E: 4,    # Drain-G <
    0x2F: 2,    # Osmose-G >
    0x30: 2,    # Osmose-G <
    0x31: 1,    # Transform-G
    0x32: 1,    # Warp-G
    0x33: 2,    # Scan-G (Front)
    0x34: 2,    # Scan-G (All)
    0x35: 2,    # Haste-G
    0x36: 2,    # Haste2-G
    0x37: 1,    # Shield-G
    0x38: 1,    # Shield2-G
    0x39: 6,    # Esuna-G (Circle)
    0x3A: 10,   # Esuna-G (Square)
    0x3B: 10,   # Thunder-G
    0x3C: 8,    # Thundara-G
    0x3D: 6,    # Thundaga-G
    0x3E: 8,    # Comet-G
    0x3F: 6,    # Meteor-G
    0x40: 4,    # Ultima-G
    0x81: 6,    # Wheel-G
    0x82: 4,    # Fang-G
    0x83: 2,    # Horn-G
    0x84: 2,    # Angel-G
    0x85: 2,    # Dark-G
    0x86: 2,    # Shoes-G
    0x87: 1,    # Rock-G >
    0x88: 1,    # Rock-G <
    0x89: 1,    # Scissors-G >
    0x8A: 1,    # Scissors-G <
    0x8B: 1,    # Paper-G >
    0x8C: 1,    # Paper-G <
    0x8D: 1,    # Crown-G
    0x8E: 2,    # Drill-G
    0x8F: 4,    # Caterpillar-G >
    0x90: 6,    # Caterpillar-G [Square]
}

    # Rare Gummis are Gummi Blocks that, in Final Mix, are obtained from treasure chests and cannot be
    # bought or sold.  This distinction is made for the sake of an option in the blueprint tab that toggles
    # whether to import these Gummis, giving the user the option to freely import required Gummi Blocks
    # without accidentally locking them out of obtainable Gummi chests later.
rare_gummis = {
    0x03,   # Life-G
    0x04,   # Full-Life-G
    0x08,   # Flare-G
    0x09,   # Holy-G
    0x2F,   # Osmose-G >
    0x30,   # Osmose-G <
    0x34,   # Scan-G (All)
    0x36,   # Haste2-G
    0x38,   # Shield2-G
    0x3C,   # Thundara-G
    0x3D,   # Thundaga-G
    0x3F,   # Meteor-G
    0x40,   # Ultima-G
}

    # Design Gummis exclusive to Final Mix.  The ones in this list are obtained through Gummi Missions.
design_gummis = {
    0x81,   # Wheel-G
    0x82,   # Fang-G
    0x83,   # Horn-G
    0x84,   # Angel-G
    0x85,   # Dark-G
    0x86,   # Shoes-G
    0x87,   # Rock-G >
    0x88,   # Rock-G <
    0x8D,   # Crown-G
    0x8F,   # Caterpillar-G >
    0x90,   # Caterpillar-G [Square]
}

    # # Design Gummis exclusive to Final Mix.  The ones in this list are obtained through Treasure Chests.
    # # These can only be imported if both boxes are checked.
rare_design_gummis = {
    0x89,   # Scissors-G >
    0x8A,   # Scissors-G <
    0x8B,   # Paper-G >
    0x8C,   # Paper-G <
    0x8E,   # Drill-G
}

cockpit_gummis = {
    0x01,   # Cure-G
    0x02,   # Curaga-G
    0x03,   # Life-G
    0x04,   # Full-Life-G
}

engine_gummis = {
    0x05,   # Fire-G
    0x06,   # Fira-G
    0x07,   # Firaga-G
    0x08,   # Flare-G
    0x09,   # Holy-G
}

weapon_gummis = {
    0x3B,   # Thunder-G
    0x3C,   # Thundara-G
    0x3D,   # Thundaga-G
    0x3E,   # Comet-G
    0x3F,   # Meteor-G
    0x40,   # Ultima-G
}

cannon_gummis = {
    0x3B,   # Thunder-G
    0x3C,   # Thundara-G
    0x3D,   # Thundaga-G
}

laser_gummis = {
    0x3E,   # Comet-G
    0x3F,   # Meteor-G
    0x40,   # Ultima-G
}

special_gummis = {
    0x2D,    # Drain-G >
    0x2E,    # Drain-G <
    0x2F,    # Osmose-G >
    0x30,    # Osmose-G <
    0x31,    # Transform-G
    0x32,    # Warp-G
    0x33,    # Scan-G (Front)
    0x34,    # Scan-G (All)
    0x35,    # Haste-G
    0x36,    # Haste2-G
    0x37,    # Shield-G
    0x38,    # Shield2-G
    0x39,    # Esuna-G (Circle)
    0x3A,    # Esuna-G (Square)
}

gummi_tiers = {
    0x01: 1,    # Cure-G
    0x02: 2,    # Curaga-G
    0x03: 4,    # Life-G
    0x04: 5,    # Full-Life-G
    0x05: 1,    # Fire-G
    0x06: 2,    # Fira-G
    0x07: 3,    # Firaga-G
    0x08: 4,    # Flare-G
    0x09: 5,    # Holy-G
    0x3B: 1,    # Thunder-G
    0x3C: 2,    # Thundara-G
    0x3D: 5,    # Thundaga-G
    0x3E: 1,    # Comet-G
    0x3F: 3,    # Meteor-G
    0x40: 5,    # Ultima-G
   
}

tier_weights = {
    1: 1,    # Tier 1
    2: 20,    # Tier 2
    3: 360,    # Tier 3
    4: 6480,    # Tier 4
    5: 116640,    # Tier 5
}

gummi_colors = {
    0x41,   # Spray
    0x42,   # Palette
}

    # The program automatically updates these items based on the blueprints loaded in the save file.
system_gummis = {
    0x43,   # SYS. UP1
    0x44,   # SYS. UP2
    0x45,   # COM. LVL1
    0x46,   # COM. LVL2
    0x47,   # COM. LVL3
}

gummi_blueprints = {
    0x48,   # Kingdom Model
    0x49,   # Hyperion Model
    0x4A,   # Geppetto Model
    0x4B,   # Cid Model
    0x4C,   # Leon Model
    0x4D,   # Yuffie Model
    0x4E,   # Aerith Model
    0x4F,   # Cactuar Model
    0x50,   # Chocobo Model
    0x51,   # Cindy Model
    0x52,   # Shiva Model
    0x53,   # Lamia Model
    0x54,   # Sandy Model
    0x55,   # Sylph Model
    0x56,   # Carbuncle Model
    0x57,   # Mindy Model
    0x58,   # Goblin Model
    0x59,   # Bomb Model
    0x5A,   # Remora Model
    0x5B,   # Ahriman Model
    0x5C,   # Imp Model
    0x5D,   # Siren Model
    0x5E,   # Stingray Model
    0x5F,   # Catoblepas Model
    0x60,   # Adamant Model
    0x61,   # Serpent Model
    0x62,   # Ifrit Model
    0x63,   # Odin Model
    0x64,   # Atomos Model
    0x65,   # Golem Model
    0x66,   # Diablos Model
    0x67,   # Deathguise Model
    0x68,   # Typhoon Model
    0x69,   # Alexander Model
    0x6A,   # Leviathan Model
    0x6B,   # Ramuh Model
    0x6C,   # Omega Model
    0x6D,   # Moogle Model
    0x6E,   # Valefor Model
    0x6F,   # PuPu Model
    0x70,   # Cerberus Model
    0x71,   # Tonberry Model
    0x72,   # Pandaemonium Model
    0x73,   # Ixion Model
    0x74,   # Gilgamesh Model
    0x75,   # Phoenix Model
    0x76,   # Eden Model
    0x77,   # Bahamut Model
}

# Final Mix-only blueprints (not present in pre-Final Mix saves)
final_mix_blueprints = {
    0x6D,  # Moogle Model
    0x6E,  # Valefor Model
    0x6F,  # PuPu Model
    0x70,  # Cerberus Model
    0x71,  # Tonberry Model
    0x72,  # Pandaemonium Model
    0x73,  # Ixion Model
    0x74,  # Gilgamesh Model
    0x75,  # Phoenix Model
    0x76,  # Eden Model
    0x77,  # Bahamut Model
}

# Non-1x1x1 block sizes.
# Axis order: (Port/Starboard, Top/Bottom, Front/Back).
# Locator is assumed to be at (0, 0, 0) for all blocks in this list.
gummi_block_sizes = {
    0x01: (2, 2, 2),  # Cure-G
    0x02: (2, 2, 2),  # Curaga-G
    0x03: (2, 2, 2),  # Life-G
    0x04: (2, 2, 2),  # Full-Life-G
    0x06: (1, 1, 2),  # Fira-G
    0x07: (2, 2, 2),  # Firaga-G
    0x08: (1, 1, 3),  # Flare-G
    0x09: (2, 2, 2),  # Holy-G
    0x22: (1, 1, 2),  # Aerora-G >
    0x23: (1, 1, 2),  # Aerora-G <
    0x24: (1, 1, 3),  # Aeroga-G >
    0x25: (1, 1, 3),  # Aeroga-G <
    0x26: (2, 1, 2),  # Tornado-G >
    0x27: (2, 1, 2),  # Tornado-G <
    0x28: (1, 1, 3),  # Float-G >
    0x29: (1, 1, 3),  # Float-G <
    0x2D: (4, 1, 1),  # Drain-G >
    0x2E: (4, 1, 1),  # Drain-G <
    0x2F: (4, 1, 1),  # Osmose-G >
    0x30: (4, 1, 1),  # Osmose-G <
    0x33: (1, 2, 1),  # Scan-G (Front)
    0x34: (1, 2, 1),  # Scan-G (All)
    0x35: (1, 1, 2),  # Haste-G
    0x36: (1, 1, 2),  # Haste2-G
    0x37: (1, 1, 2),  # Shield-G
    0x38: (1, 1, 2),  # Shield2-G
    0x3B: (1, 1, 2),  # Thunder-G
    0x3C: (1, 1, 2),  # Thundara-G
    0x3D: (1, 1, 3),  # Thundaga-G
    0x3E: (1, 1, 2),  # Comet-G
    0x3F: (1, 1, 2),  # Meteor-G
    0x40: (1, 1, 3),  # Ultima-G
    0x81: (1, 2, 2),  # Wheel-G
    0x83: (2, 2, 2),  # Horn-G
    0x84: (3, 1, 2),  # Angel-G
    0x85: (3, 1, 2),  # Dark-G
    0x86: (2, 1, 3),  # Shoes-G
    0x87: (2, 2, 2),  # Rock-G >
    0x88: (2, 2, 2),  # Rock-G <
    0x89: (2, 2, 2),  # Scissors-G >
    0x8A: (2, 2, 2),  # Scissors-G <
    0x8B: (2, 2, 2),  # Paper-G >
    0x8C: (2, 2, 2),  # Paper-G <
    0x8D: (2, 2, 2),  # Crown-G
    0x8E: (2, 2, 3),  # Drill-G
    0x8F: (1, 2, 2),  # Caterpillar-G >
    0x90: (1, 2, 2),  # Caterpillar-G [Square]
}
