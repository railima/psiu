"""Atalhos de teclado globais (funcionam com o app minimizado ou em segundo plano).

macOS: Carbon RegisterEventHotKey (não exige permissão de Acessibilidade).
Windows: RegisterHotKey da user32, numa thread com o próprio loop de mensagens.

Os callbacks rodam numa thread separada, então podem demorar sem travar o sistema.
"""

import ctypes
import sys
import threading

# Atalho -> (tecla, rótulo no macOS, rótulo no Windows)
HOTKEYS = {
    "toggle": ("R", "⌃⌥R", "Ctrl+Alt+R"),
    "mark": ("M", "⌃⌥M", "Ctrl+Alt+M"),
}


def labels():
    index = 1 if sys.platform == "darwin" else 2
    return {name: spec[index] for name, spec in HOTKEYS.items()}


def _run_async(callback):
    threading.Thread(target=callback, daemon=True).start()


# ---------- macOS ----------

_MAC_KEYCODES = {"R": 15, "M": 46}  # kVK_ANSI_R, kVK_ANSI_M
_mac_refs = []  # mantém handler e registros vivos (senão o ctypes libera a memória)


def _fourcc(code):
    return int.from_bytes(code.encode(), "big")


def _register_mac(callbacks):
    from ctypes import CFUNCTYPE, POINTER, Structure, byref, c_int32, c_uint32, c_void_p, sizeof

    carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")

    class EventHotKeyID(Structure):
        _fields_ = [("signature", c_uint32), ("id", c_uint32)]

    class EventTypeSpec(Structure):
        _fields_ = [("eventClass", c_uint32), ("eventKind", c_uint32)]

    handler_type = CFUNCTYPE(c_int32, c_void_p, c_void_p, c_void_p)
    carbon.GetApplicationEventTarget.restype = c_void_p
    carbon.InstallEventHandler.argtypes = [c_void_p, handler_type, c_uint32, POINTER(EventTypeSpec), c_void_p, POINTER(c_void_p)]
    carbon.GetEventParameter.argtypes = [c_void_p, c_uint32, c_uint32, c_void_p, c_uint32, c_void_p, c_void_p]
    carbon.RegisterEventHotKey.argtypes = [c_uint32, c_uint32, EventHotKeyID, c_void_p, c_uint32, POINTER(c_void_p)]

    names = list(callbacks)
    signature = _fourcc("PSIU")

    def on_hotkey(_next_handler, event, _user_data):
        hotkey = EventHotKeyID()
        carbon.GetEventParameter(event, _fourcc("----"), _fourcc("hkid"), None, sizeof(hotkey), None, byref(hotkey))
        if hotkey.signature == signature and 1 <= hotkey.id <= len(names):
            _run_async(callbacks[names[hotkey.id - 1]])
        return 0

    handler = handler_type(on_hotkey)
    target = carbon.GetApplicationEventTarget()
    spec = EventTypeSpec(_fourcc("keyb"), 5)  # kEventClassKeyboard, kEventHotKeyPressed
    handler_ref = c_void_p()
    status = carbon.InstallEventHandler(target, handler, 1, byref(spec), None, byref(handler_ref))
    _mac_refs.extend([handler, handler_ref])
    if status != 0:
        return False

    control_option = 4096 | 2048  # controlKey | optionKey
    ok = True
    for i, name in enumerate(names, start=1):
        ref = c_void_p()
        key = _MAC_KEYCODES[HOTKEYS[name][0]]
        status = carbon.RegisterEventHotKey(key, control_option, EventHotKeyID(signature, i), target, 0, byref(ref))
        _mac_refs.append(ref)
        ok = ok and status == 0
    return ok


# ---------- Windows ----------

def _register_windows(callbacks):
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    mod_alt, mod_control, mod_norepeat, wm_hotkey = 0x1, 0x2, 0x4000, 0x0312
    names = list(callbacks)
    result = {}
    ready = threading.Event()

    def loop():
        # O atalho pertence à thread que o registrou, então o loop de mensagens fica aqui.
        result["ok"] = all(
            user32.RegisterHotKey(None, i, mod_control | mod_alt | mod_norepeat, ord(HOTKEYS[name][0]))
            for i, name in enumerate(names, start=1)
        )
        ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == wm_hotkey and 1 <= msg.wParam <= len(names):
                _run_async(callbacks[names[msg.wParam - 1]])

    threading.Thread(target=loop, daemon=True).start()
    ready.wait(2)
    return result.get("ok", False)


def register(callbacks):
    """Registra os atalhos globais. `callbacks` mapeia nomes de HOTKEYS a funções.

    No macOS, chame na thread principal com o app já rodando. Retorna True se todos foram registrados
    (pode falhar se outro programa já usa a mesma combinação).
    """
    if sys.platform == "darwin":
        return _register_mac(callbacks)
    if sys.platform == "win32":
        return _register_windows(callbacks)
    return False
