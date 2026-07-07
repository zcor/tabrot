#!/usr/bin/env python3
"""Synthetic-fixture test for src/snss_tabs.py.

Builds a minimal, valid SNSS session file in memory (no real browser data
involved), runs it through the parser, and asserts the expected URLs,
titles, and window grouping come out the other end.

Plain asserts, no pytest. Run with: python3 tests/test_parser.py
"""
import os
import struct
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.dirname(TESTS_DIR), 'src')
sys.path.insert(0, SRC_DIR)

import snss_tabs  # noqa: E402

# Command ids, mirrored from snss_tabs.py
CMD_SET_TAB_WINDOW = 0
CMD_SET_TAB_INDEX = 2
CMD_UPDATE_TAB_NAVIGATION = 6
CMD_SET_SELECTED_NAV_INDEX = 7
CMD_TAB_CLOSED = 16
CMD_WINDOW_CLOSED = 17


def _pad4(n):
    return (n + 3) & ~3


def build_string(s):
    """Mirror read_string: uint32 length + utf-8 bytes + zero-pad to 4."""
    raw = s.encode('utf-8')
    out = struct.pack('<I', len(raw)) + raw
    padded_len = _pad4(len(out))
    out += b'\x00' * (padded_len - len(out))
    return out


def build_string16(s):
    """Mirror read_string16: uint32 char-count + utf-16-le bytes + zero-pad to 4."""
    raw = s.encode('utf-16-le')
    out = struct.pack('<I', len(s)) + raw
    padded_len = _pad4(len(out))
    out += b'\x00' * (padded_len - len(out))
    return out


def build_command(cmd_id, payload):
    """A command record: uint16 size (1 byte cmd id + payload), then cmd id
    byte, then payload. Mirrors the read loop in parse_snss()."""
    size = 1 + len(payload)
    return struct.pack('<H', size) + bytes([cmd_id]) + payload


def build_update_tab_navigation(tab_id, nav_idx, url, title):
    # payload: uint32 pickle_size (unused by reader, just skipped via offset
    # arithmetic — reader starts reading the tab_id/index at off=4), then
    # int32 tab_id, int32 nav_idx, string url, string16 title.
    body = struct.pack('<ii', tab_id, nav_idx) + build_string(url) + build_string16(title)
    pickle_size = len(body)
    payload = struct.pack('<I', pickle_size) + body
    return build_command(CMD_UPDATE_TAB_NAVIGATION, payload)


def build_set_tab_window(window_id, tab_id):
    payload = struct.pack('<II', window_id, tab_id)
    return build_command(CMD_SET_TAB_WINDOW, payload)


def build_set_tab_index(tab_id, index):
    payload = struct.pack('<II', tab_id, index)
    return build_command(CMD_SET_TAB_INDEX, payload)


def build_set_selected_nav_index(tab_id, index):
    payload = struct.pack('<Ii', tab_id, index)
    return build_command(CMD_SET_SELECTED_NAV_INDEX, payload)


def build_tab_closed(tab_id):
    payload = struct.pack('<I', tab_id)
    return build_command(CMD_TAB_CLOSED, payload)


def build_window_closed(window_id):
    payload = struct.pack('<I', window_id)
    return build_command(CMD_WINDOW_CLOSED, payload)


def build_snss_file(commands):
    header = b'SNSS' + struct.pack('<i', 1)
    return header + b''.join(commands)


def run_tests():
    failures = []

    def check(name, cond):
        if cond:
            print(f"  ok - {name}")
        else:
            print(f"  FAIL - {name}")
            failures.append(name)

    # --- Scenario ---------------------------------------------------------
    # Window 0: two tabs.
    #   tab 1 -> single nav entry (its only/current entry): example.org
    #   tab 2 -> two nav entries, selected nav index points at the 2nd
    # Window 1: one tab, but the tab itself is closed -> should not appear.
    # Window 2: one tab; the *window* is closed -> should not appear.
    commands = []

    # Window 0 / tab 1: index 0 in window, one nav entry (index 0)
    commands.append(build_set_tab_window(0, 1))
    commands.append(build_set_tab_index(1, 0))
    commands.append(build_update_tab_navigation(1, 0, "https://example.org/", "Example Domain"))

    # Window 0 / tab 2: index 1 in window, two nav entries; selected = 1
    commands.append(build_set_tab_window(0, 2))
    commands.append(build_set_tab_index(2, 1))
    commands.append(build_update_tab_navigation(2, 0, "https://old.example.com/", "Old Page"))
    commands.append(build_update_tab_navigation(2, 1, "https://new.example.com/", "New Page — Unicode ✓"))
    commands.append(build_set_selected_nav_index(2, 1))

    # Window 1 / tab 3: closed tab, should be excluded entirely
    commands.append(build_set_tab_window(1, 3))
    commands.append(build_set_tab_index(3, 0))
    commands.append(build_update_tab_navigation(3, 0, "https://ghost.example.com/", "Ghost Tab"))
    commands.append(build_tab_closed(3))

    # Window 2 / tab 4: window closed, tab should be excluded
    commands.append(build_set_tab_window(2, 4))
    commands.append(build_set_tab_index(4, 0))
    commands.append(build_update_tab_navigation(4, 0, "https://closedwindow.example.com/", "In A Closed Window"))
    commands.append(build_window_closed(2))

    data = build_snss_file(commands)

    print("SNSS magic + parse:")
    check("magic bytes present", data[:4] == b'SNSS')

    windows = snss_tabs.parse_snss(data)

    check("exactly one surviving window", len(windows) == 1)
    check("window 0 is the surviving window", 0 in windows)
    check("window 1 excluded (tab closed)", 1 not in windows)
    check("window 2 excluded (window closed)", 2 not in windows)

    tabs = sorted(windows.get(0, []))
    check("window 0 has exactly 2 tabs", len(tabs) == 2)

    if len(tabs) == 2:
        (idx0, tabid0, url0, title0), (idx1, tabid1, url1, title1) = tabs
        check("tab order: index 0 first", idx0 == 0)
        check("tab order: index 1 second", idx1 == 1)
        check("tab 1 url correct", url0 == "https://example.org/")
        check("tab 1 title correct", title0 == "Example Domain")
        check("tab 2 uses selected nav (not first entry)", url1 == "https://new.example.com/")
        check("tab 2 title uses selected nav entry", title1 == "New Page — Unicode ✓")

    # --- JSON round trip ----------------------------------------------------
    doc = snss_tabs.to_json_doc(windows)
    check("json doc has one window", len(doc["windows"]) == 1)
    if doc["windows"]:
        w0 = doc["windows"][0]
        check("json window id correct", w0["window"] == 0)
        check("json has 2 tabs", len(w0["tabs"]) == 2)
        urls = [t["url"] for t in w0["tabs"]]
        check("json urls match", urls == ["https://example.org/", "https://new.example.com/"])

    # --- Fallback: no selected-nav-index recorded -> use max nav index ------
    fallback_commands = [
        build_set_tab_window(5, 10),
        build_set_tab_index(10, 0),
        build_update_tab_navigation(10, 0, "https://first.example.com/", "First"),
        build_update_tab_navigation(10, 3, "https://latest.example.com/", "Latest"),
    ]
    fallback_data = build_snss_file(fallback_commands)
    fallback_windows = snss_tabs.parse_snss(fallback_data)
    check("fallback: window present", 5 in fallback_windows)
    if 5 in fallback_windows:
        _, _, furl, ftitle = fallback_windows[5][0]
        check("fallback picks max nav index when no selection recorded", furl == "https://latest.example.com/")

    # --- Malformed command is skipped without crashing the whole parse ------
    malformed = build_command(CMD_UPDATE_TAB_NAVIGATION, b'\x01\x02')  # too short, will raise internally
    good = build_update_tab_navigation(20, 0, "https://survives.example.com/", "Survivor")
    resilience_data = build_snss_file([
        build_set_tab_window(9, 20),
        build_set_tab_index(20, 0),
        malformed,
        good,
    ])
    resilience_windows = snss_tabs.parse_snss(resilience_data)
    check("parser survives a malformed command", 9 in resilience_windows)
    if 9 in resilience_windows:
        check("surviving tab parsed correctly after malformed command",
              resilience_windows[9][0][2] == "https://survives.example.com/")

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED: {failures}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == '__main__':
    sys.exit(run_tests())
