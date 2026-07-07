#!/usr/bin/env python3
"""Parse a Chromium-family SNSS Session file and print current tab per window.

Works against Brave, Chrome, Chromium, Edge, Arc, and any other
Chromium-derived browser — they all share the same Session Service file
format ("SNSS").

Best-effort: parses UpdateTabNavigation (6), SetTabWindow (0),
SetSelectedNavigationIndex (7), SetTabIndexInWindow (2).
Falls back gracefully on malformed commands.

Usage:
    snss_tabs.py [PATH] [--json] [--session-file PATH]

If no path is given (positionally or via --session-file), the newest
Session_* file is auto-detected across the common Chromium-family profile
locations on macOS and Linux, scanning the "Default" profile plus any
"Profile *" profiles, and picking whichever Session file was modified most
recently. The browser/profile chosen is reported on stderr.

Output is a plain per-window tab listing by default, or a JSON document
(windows -> tabs, each with url/title) when --json is passed.

Stdlib only. Python 3.9+.
"""
import argparse
import collections
import glob
import json
import os
import struct
import sys

# ---------------------------------------------------------------------------
# Binary parsing — do not "improve" this, it works. Tested against a real
# 144-tab, 12-window Brave session on macOS.
# ---------------------------------------------------------------------------

# command ids (session service)
CMD_SET_TAB_WINDOW = 0
CMD_SET_TAB_INDEX = 2
CMD_TAB_NAV_PATH_PRUNED_FROM_BACK = 5
CMD_UPDATE_TAB_NAVIGATION = 6
CMD_SET_SELECTED_NAV_INDEX = 7
CMD_SET_SELECTED_TAB_IN_INDEX = 8
CMD_TAB_CLOSED = 16
CMD_WINDOW_CLOSED = 17


def read_string(buf, off):
    (n,) = struct.unpack_from('<I', buf, off)
    off += 4
    s = buf[off:off+n].decode('utf-8', 'replace')
    off += n
    off = (off + 3) & ~3  # pad to 4
    return s, off


def read_string16(buf, off):
    (n,) = struct.unpack_from('<I', buf, off)
    off += 4
    nbytes = n * 2
    s = buf[off:off+nbytes].decode('utf-16-le', 'replace')
    off += nbytes
    off = (off + 3) & ~3
    return s, off


def parse_snss(data):
    """Parse raw SNSS bytes. Returns dict: window_id -> list of (index, tab_id, url, title)."""
    assert data[:4] == b'SNSS', 'not an SNSS file'
    struct.unpack('<i', data[4:8])[0]  # version, unused
    pos = 8

    tab_window = {}
    tab_index = {}
    tab_selected_nav = {}
    navs = collections.defaultdict(dict)  # tab_id -> {nav_index: (url, title)}
    closed_tabs = set()
    closed_windows = set()

    while pos + 3 <= len(data):
        (size,) = struct.unpack_from('<H', data, pos)
        pos += 2
        if size == 0 or pos + size > len(data):
            break
        cmd = data[pos]
        payload = data[pos+1:pos+size]
        pos += size
        try:
            if cmd == CMD_UPDATE_TAB_NAVIGATION:
                # payload: uint32 pickle_size, then pickle: int tab_id, int index, string url, string16 title, ...
                buf = payload
                off = 4
                (tab_id, nav_idx) = struct.unpack_from('<ii', buf, off)
                off += 8
                url, off = read_string(buf, off)
                title, off = read_string16(buf, off)
                navs[tab_id][nav_idx] = (url, title)
            elif cmd == CMD_SET_TAB_WINDOW:
                w, t = struct.unpack_from('<II', payload, 0)
                tab_window[t] = w
            elif cmd == CMD_SET_TAB_INDEX:
                t, i = struct.unpack_from('<II', payload, 0)
                tab_index[t] = i
            elif cmd == CMD_SET_SELECTED_NAV_INDEX:
                t, i = struct.unpack_from('<Ii', payload, 0)
                tab_selected_nav[t] = i
            elif cmd == CMD_TAB_CLOSED:
                (t,) = struct.unpack_from('<I', payload, 0)
                closed_tabs.add(t)
            elif cmd == CMD_WINDOW_CLOSED:
                (w,) = struct.unpack_from('<I', payload, 0)
                closed_windows.add(w)
        except Exception:
            continue

    windows = collections.defaultdict(list)
    for tab_id, entries in navs.items():
        if tab_id in closed_tabs:
            continue
        w = tab_window.get(tab_id, -1)
        if w in closed_windows:
            continue
        sel = tab_selected_nav.get(tab_id)
        if sel is not None and sel in entries:
            url, title = entries[sel]
        else:
            url, title = entries[max(entries)]
        windows[w].append((tab_index.get(tab_id, 10**9), tab_id, url, title))

    return windows


# ---------------------------------------------------------------------------
# Auto-detection of Session files across Chromium-family browsers
# ---------------------------------------------------------------------------

def _mac_profile_roots():
    home = os.path.expanduser('~')
    base = os.path.join(home, 'Library', 'Application Support')
    return [
        ('Brave', os.path.join(base, 'BraveSoftware', 'Brave-Browser')),
        ('Chrome', os.path.join(base, 'Google', 'Chrome')),
        ('Chromium', os.path.join(base, 'Chromium')),
        ('Edge', os.path.join(base, 'Microsoft Edge')),
        ('Arc', os.path.join(base, 'Arc', 'User Data')),
    ]


def _linux_profile_roots():
    home = os.path.expanduser('~')
    config = os.path.join(home, '.config')
    return [
        ('Brave', os.path.join(config, 'BraveSoftware', 'Brave-Browser')),
        ('Chrome', os.path.join(config, 'google-chrome')),
        ('Chromium', os.path.join(config, 'chromium')),
        ('Edge', os.path.join(config, 'microsoft-edge')),
    ]


def profile_roots():
    """Return list of (browser_name, root_dir) to search, per platform."""
    if sys.platform == 'darwin':
        return _mac_profile_roots()
    elif sys.platform.startswith('linux'):
        return _linux_profile_roots()
    else:
        # Best-effort: try both sets of paths anyway.
        return _mac_profile_roots() + _linux_profile_roots()


def find_session_files():
    """Scan all known browser roots for Default + Profile * dirs, return
    list of (browser_name, profile_name, session_file_path, mtime)."""
    found = []
    for browser_name, root in profile_roots():
        if not os.path.isdir(root):
            continue
        profile_dirs = []
        default_dir = os.path.join(root, 'Default')
        if os.path.isdir(default_dir):
            profile_dirs.append(('Default', default_dir))
        for entry in sorted(glob.glob(os.path.join(root, 'Profile *'))):
            if os.path.isdir(entry):
                profile_dirs.append((os.path.basename(entry), entry))

        for profile_name, profile_dir in profile_dirs:
            sessions_dir = os.path.join(profile_dir, 'Sessions')
            if not os.path.isdir(sessions_dir):
                continue
            for session_file in glob.glob(os.path.join(sessions_dir, 'Session_*')):
                try:
                    mtime = os.path.getmtime(session_file)
                except OSError:
                    continue
                found.append((browser_name, profile_name, session_file, mtime))
    return found


def auto_detect_session_file():
    """Pick the most-recently-modified Session file across all known
    browsers/profiles. Returns (browser_name, profile_name, path) or raises
    FileNotFoundError."""
    found = find_session_files()
    if not found:
        raise FileNotFoundError(
            "No Chromium-family Session files found. Checked Brave, Chrome, "
            "Chromium, Edge, and Arc profile directories (Default + Profile *)."
        )
    found.sort(key=lambda t: t[3], reverse=True)
    browser_name, profile_name, path, _mtime = found[0]
    return browser_name, profile_name, path


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_text(windows):
    for w in sorted(windows):
        tabs = sorted(windows[w])
        print(f"=== WINDOW {w} ({len(tabs)} tabs) ===")
        for idx, (i, t, url, title) in enumerate(tabs, 1):
            title = (title or '').strip()[:100]
            print(f"{idx}. {url}  ||| {title}")
        print()


def to_json_doc(windows):
    doc = {"windows": []}
    for w in sorted(windows):
        tabs = sorted(windows[w])
        window_doc = {"window": w, "tabs": []}
        for idx, (i, t, url, title) in enumerate(tabs, 1):
            window_doc["tabs"].append({
                "position": idx,
                "url": url,
                "title": (title or '').strip(),
            })
        doc["windows"].append(window_doc)
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('path', nargs='?', default=None,
                         help='Path to an SNSS Session file (optional; auto-detected if omitted)')
    parser.add_argument('--session-file', dest='session_file', default=None,
                         help='Explicit path to an SNSS Session file (overrides auto-detection)')
    parser.add_argument('--json', action='store_true',
                         help='Emit JSON instead of the plain text listing')
    args = parser.parse_args()

    path = args.session_file or args.path

    if path is None:
        try:
            browser_name, profile_name, path = auto_detect_session_file()
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Using {browser_name} ({profile_name}): {path}", file=sys.stderr)

    try:
        with open(path, 'rb') as f:
            data = f.read()
    except OSError as e:
        print(f"error: could not read session file {path!r}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        windows = parse_snss(data)
    except AssertionError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(to_json_doc(windows), indent=2))
    else:
        print_text(windows)


if __name__ == '__main__':
    main()
