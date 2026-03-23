import struct
import logging
import re

pngHeaderLength = 0x70
numEntries = 200
entryLength = 0x158
encryptedLength = 0xE0

entryNameOffset = 0x00
entryNameLength = 0x40
entryDataLengthOffset = 0x50

def getDecryptedEntries(file_content):

    decrypted_entries = []
    
    for i in range(numEntries):
        entryOffset = pngHeaderLength + i * entryLength
        entry = file_content[entryOffset:entryOffset + encryptedLength]
        encrypted_content = [int(c) for c in entry]
        encryption_key = [int(c) for c in file_content[entryOffset + encryptedLength:entryOffset + encryptedLength + 0x10]]
        decrypted_content = encrypted_content.copy()
        
        for i, c in enumerate(encrypted_content):
            decrypted_content[i] ^= encryption_key[i % 16]
        decrypted_content += [0] * 0x78

        content_format = "{}B".format(len(decrypted_content))
        decrypted_content = struct.pack(content_format, *decrypted_content)
        
        decrypted_entry = {
            "name": struct.unpack("{}s".format(entryNameLength), decrypted_content[entryNameOffset:entryNameOffset + entryNameLength])[0].strip(b"\x00").decode('ascii'), 
            "size": struct.unpack("<I", decrypted_content[entryDataLengthOffset:entryDataLengthOffset + 4])[0], 
            "content": decrypted_content
        }
            
        decrypted_entries.append(decrypted_entry)
        
    return decrypted_entries


def getValidSaveEntries(file_content):
    """
    Return only valid KHFM save entries, preserving the original index.
    Each entry includes an 'index' field pointing to its TOC slot.
    """
    decrypted_entries = getDecryptedEntries(file_content)
    valid_entries = []
    pattern = re.compile(r"^BISLPS-25198-\d{2}$")

    for i, entry in enumerate(decrypted_entries):
        name = entry.get("name", "")
        if pattern.match(name):
            entry_copy = dict(entry)
            entry_copy["index"] = i
            valid_entries.append(entry_copy)

    return valid_entries
