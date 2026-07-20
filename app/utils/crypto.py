import sys
import os
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger("CucumberStudioImporter")

# DPAPI Structures (for Windows-native encryption using OS login session)
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ('cbData', wintypes.DWORD),
            ('pbData', ctypes.POINTER(ctypes.c_char))
        ]

def _encrypt_dpapi(data: bytes) -> bytes:
    """Encrypts data using Windows DPAPI."""
    if sys.platform != 'win32':
        raise OSError("DPAPI is only available on Windows.")
    
    in_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
    out_blob = DATA_BLOB()
    
    # CRYPTPROTECT_UI_FORBIDDEN = 0x01
    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        b"CucumberStudioCredentials",
        None,
        None,
        None,
        0x01,
        ctypes.byref(out_blob)
    )
    if not result:
        raise ctypes.WinError()
    
    encrypted_data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    ctypes.windll.kernel32.LocalFree(out_blob.pbData)
    return encrypted_data

def _decrypt_dpapi(data: bytes) -> bytes:
    """Decrypts data using Windows DPAPI."""
    if sys.platform != 'win32':
        raise OSError("DPAPI is only available on Windows.")
    
    in_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data))
    out_blob = DATA_BLOB()
    
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0x01,
        ctypes.byref(out_blob)
    )
    if not result:
        raise ctypes.WinError()
    
    decrypted_data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    ctypes.windll.kernel32.LocalFree(out_blob.pbData)
    return decrypted_data


# Fernet Fallback (for non-Windows or if DPAPI fails)
def _get_fernet():
    from cryptography.fernet import Fernet
    key_file = settings.ENCRYPTION_KEY_FILE
    if key_file.exists():
        key = key_file.read_bytes()
    else:
        key = Fernet.generate_key()
        key_file.write_bytes(key)
    return Fernet(key)

def _encrypt_fernet(data: bytes) -> bytes:
    f = _get_fernet()
    return f.encrypt(data)

def _decrypt_fernet(data: bytes) -> bytes:
    f = _get_fernet()
    return f.decrypt(data)


# Public API
def encrypt_string(plain_text: str) -> bytes:
    """Encrypts a string and returns the encrypted bytes."""
    if not plain_text:
        return b""
    data_bytes = plain_text.encode('utf-8')
    try:
        if sys.platform == 'win32':
            return _encrypt_dpapi(data_bytes)
    except Exception as e:
        logger.warning(f"Windows DPAPI encryption failed, falling back to Fernet: {e}")
    
    return _encrypt_fernet(data_bytes)

def decrypt_string(encrypted_bytes: bytes) -> str:
    """Decrypts bytes and returns the plain text string."""
    if not encrypted_bytes:
        return ""
    try:
        if sys.platform == 'win32':
            # Check if it was encrypted with DPAPI (Fernet output is base64 text/bytes, starting with gAAAA...)
            # We try DPAPI first; if it fails, we fall back to Fernet.
            try:
                return _decrypt_dpapi(encrypted_bytes).decode('utf-8')
            except Exception:
                pass
    except Exception:
        pass
        
    try:
        return _decrypt_fernet(encrypted_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ""

def save_credentials(email: str, password: str):
    """Saves email and password to encrypted file."""
    if not email or not password:
        return
    
    enc_email = encrypt_string(email)
    enc_password = encrypt_string(password)
    
    # Store length of email and data in a binary format:
    # [4 bytes email len][encrypted email bytes][4 bytes pwd len][encrypted pwd bytes]
    import struct
    data = struct.pack(">I", len(enc_email)) + enc_email + struct.pack(">I", len(enc_password)) + enc_password
    settings.ENCRYPTED_CREDS_FILE.write_bytes(data)

def load_credentials() -> tuple[str, str]:
    """Loads email and password from encrypted file. Returns (email, password) or ('', '')."""
    if not settings.ENCRYPTED_CREDS_FILE.exists():
        return "", ""
    
    try:
        data = settings.ENCRYPTED_CREDS_FILE.read_bytes()
        if len(data) < 8:
            return "", ""
        
        import struct
        email_len = struct.unpack(">I", data[:4])[0]
        offset = 4
        enc_email = data[offset:offset+email_len]
        offset += email_len
        
        password_len = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        enc_password = data[offset:offset+password_len]
        
        email = decrypt_string(enc_email)
        password = decrypt_string(enc_password)
        return email, password
    except Exception as e:
        logger.error(f"Failed to load encrypted credentials: {e}")
        return "", ""

def clear_credentials():
    """Removes stored encrypted credentials."""
    if settings.ENCRYPTED_CREDS_FILE.exists():
        try:
            settings.ENCRYPTED_CREDS_FILE.unlink()
        except Exception as e:
            logger.error(f"Failed to delete credentials file: {e}")
